# -*- coding: utf-8 -*-
"""
定时刷步调度器
"""
import time
import threading
from datetime import datetime, date
from typing import Optional

from models import ScheduledTask, User, SessionLocal
from config import APP_DEBUG, USE_PROXY, USE_PROXY_MODE

# 导入 step_brush
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from step_brush import ZeppAPI
from step_brush import bindband


class StepScheduler:
    """定时刷步调度器"""

    def __init__(self):
        self.running = False
        self.thread = None
        self.interval = 60  # 检查间隔（秒）

    def log(self, msg: str):
        if APP_DEBUG:
            print(f"[Scheduler] {msg}")

    def start(self):
        """启动调度器"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.log("调度器已启动")

    def stop(self):
        """停止调度器"""
        self.running = False
        self.log("调度器已停止")

    def _run_loop(self):
        """主循环"""
        while self.running:
            try:
                self._check_and_execute()
            except Exception as e:
                self.log(f"执行异常: {e}")

            time.sleep(self.interval)

    def _check_and_execute(self):
        """检查并执行定时任务"""
        now = datetime.now()
        current_hour = now.hour
        current_date = now.strftime("%Y-%m-%d")

        db = SessionLocal()
        try:
            # 查找所有活跃的定时任务
            tasks = db.query(ScheduledTask).filter(
                ScheduledTask.status == "active"
            ).all()

            for task in tasks:
                self._process_task(task, current_hour, current_date, db)
        finally:
            db.close()

    def _process_task(self, task: ScheduledTask, current_hour: int, current_date: str, db):
        """处理单个任务"""
        # 检查用户会员状态
        user = db.query(User).filter(User.user_key == task.user_key).first()
        if not user or not user.vip_expire_at or user.vip_expire_at < datetime.now():
            self.log(f"任务 {task.user_key} 用户会员已过期，跳过执行")
            return

        # 检查是否是新的一天，重置进度
        if task.last_run_date != current_date:
            task.current_steps = 0
            task.current_step_index = 0
            task.last_run_date = current_date
            db.commit()
            self.log(f"任务 {task.user_key} 新的一天，重置进度")

        # 检查是否在执行时间范围内
        if not (task.start_hour <= current_hour < task.end_hour):
            return

        # 检查当前小时是否已经执行过
        expected_index = current_hour - task.start_hour
        if task.current_step_index > expected_index:
            return  # 已经执行过当前时间段

        # 计算应该达到的步数
        total_hours = task.end_hour - task.start_hour
        steps_per_hour = task.target_steps // total_hours
        target_current_steps = (expected_index + 1) * steps_per_hour

        # 确保最后一段时间达到目标
        if expected_index == total_hours - 1:
            target_current_steps = task.target_steps

        # 计算本次需要刷的步数
        steps_to_add = target_current_steps - task.current_steps
        if steps_to_add <= 0:
            return  # 不需要刷步

        self.log(f"任务 {task.user_key}: 时间段 {expected_index + 1}/{total_hours}, "
                f"目标 {target_current_steps}, 当前 {task.current_steps}, 本次刷 {steps_to_add}")

        # 执行刷步
        success = self._execute_brush_step(task.user_key, steps_to_add)

        if success:
            task.current_steps = target_current_steps
            task.current_step_index = expected_index + 1
            task.last_run_at = datetime.now()
            self.log(f"任务 {task.user_key} 刷步成功: +{steps_to_add}步, 累计 {task.current_steps}")
        else:
            self.log(f"任务 {task.user_key} 刷步失败")

        db.commit()

    def _execute_brush_step(self, user_key: str, steps: int) -> bool:
        """执行刷步"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_key == user_key).first()
            if not user or not user.zepp_email:
                return False
            if USE_PROXY_MODE and user.bind_status != 1:
                return False

            if USE_PROXY_MODE:
                api = ZeppAPI(
                    user.zepp_email,
                    user.zepp_password,
                    verbose=APP_DEBUG,
                    use_proxy=USE_PROXY
                )
                api.userid = user.zepp_userid
                result = api.update_step(steps)
            else:
                result = bindband(
                    user.zepp_email,
                    user.zepp_password,
                    step=steps,
                    verbose=APP_DEBUG,
                    use_proxy=False
                )

            return result.get("success", False)
        except Exception as e:
            self.log(f"刷步异常: {e}")
            return False
        finally:
            db.close()

    # ==================== 任务管理方法 ====================

    def create_task(self, user_key: str, target_steps: int,
                   start_hour: int = 8, end_hour: int = 21) -> dict:
        """创建定时任务"""
        db = SessionLocal()
        try:
            # 检查用户是否可执行刷步
            user = db.query(User).filter(User.user_key == user_key).first()
            if not user or not user.zepp_email:
                return {"success": False, "message": "请先完成设备注册"}
            if USE_PROXY_MODE and user.bind_status != 1:
                return {"success": False, "message": "请先完成设备绑定"}

            # 检查是否已有任务
            existing = db.query(ScheduledTask).filter(
                ScheduledTask.user_key == user_key,
                ScheduledTask.status.in_(["active", "paused"])
            ).first()

            if existing:
                # 更新现有任务
                existing.target_steps = target_steps
                existing.start_hour = start_hour
                existing.end_hour = end_hour
                existing.status = "active"
                existing.current_steps = 0
                existing.current_step_index = 0
                existing.last_run_date = None
                db.commit()
                return {
                    "success": True,
                    "message": f"已更新定时任务：每天 {start_hour}:00-{end_hour}:00 完成 {target_steps} 步",
                    "task": existing.to_dict()
                }

            # 创建新任务
            task = ScheduledTask(
                user_key=user_key,
                target_steps=target_steps,
                start_hour=start_hour,
                end_hour=end_hour,
                status="active"
            )
            db.add(task)
            db.commit()

            return {
                "success": True,
                "message": f"已创建定时任务：每天 {start_hour}:00-{end_hour}:00 完成 {target_steps} 步",
                "task": task.to_dict()
            }
        finally:
            db.close()

    def get_task(self, user_key: str) -> Optional[dict]:
        """获取用户的定时任务"""
        db = SessionLocal()
        try:
            task = db.query(ScheduledTask).filter(
                ScheduledTask.user_key == user_key,
                ScheduledTask.status.in_(["active", "paused"])
            ).first()

            return task.to_dict() if task else None
        finally:
            db.close()

    def update_task(self, user_key: str, target_steps: int = None,
                   start_hour: int = None, end_hour: int = None) -> dict:
        """更新定时任务"""
        db = SessionLocal()
        try:
            task = db.query(ScheduledTask).filter(
                ScheduledTask.user_key == user_key,
                ScheduledTask.status.in_(["active", "paused"])
            ).first()

            if not task:
                return {"success": False, "message": "没有找到定时任务"}

            if target_steps is not None:
                task.target_steps = target_steps
            if start_hour is not None:
                task.start_hour = start_hour
            if end_hour is not None:
                task.end_hour = end_hour

            db.commit()

            return {
                "success": True,
                "message": f"定时任务已更新：每天 {task.start_hour}:00-{task.end_hour}:00 完成 {task.target_steps} 步",
                "task": task.to_dict()
            }
        finally:
            db.close()

    def pause_task(self, user_key: str) -> dict:
        """暂停定时任务"""
        db = SessionLocal()
        try:
            task = db.query(ScheduledTask).filter(
                ScheduledTask.user_key == user_key,
                ScheduledTask.status == "active"
            ).first()

            if not task:
                return {"success": False, "message": "没有找到活跃的定时任务"}

            task.status = "paused"
            db.commit()

            return {"success": True, "message": "定时任务已暂停"}
        finally:
            db.close()

    def resume_task(self, user_key: str) -> dict:
        """恢复定时任务"""
        db = SessionLocal()
        try:
            task = db.query(ScheduledTask).filter(
                ScheduledTask.user_key == user_key,
                ScheduledTask.status == "paused"
            ).first()

            if not task:
                return {"success": False, "message": "没有找到暂停的定时任务"}

            task.status = "active"
            db.commit()

            return {"success": True, "message": "定时任务已恢复"}
        finally:
            db.close()

    def cancel_task(self, user_key: str) -> dict:
        """取消定时任务"""
        db = SessionLocal()
        try:
            task = db.query(ScheduledTask).filter(
                ScheduledTask.user_key == user_key,
                ScheduledTask.status.in_(["active", "paused"])
            ).first()

            if not task:
                return {"success": False, "message": "没有找到定时任务"}

            task.status = "cancelled"
            db.commit()

            return {"success": True, "message": "定时任务已取消"}
        finally:
            db.close()

    def get_all_active_tasks(self) -> list:
        """获取所有活跃任务（后台管理用）"""
        db = SessionLocal()
        try:
            tasks = db.query(ScheduledTask).filter(
                ScheduledTask.status.in_(["active", "paused"])
            ).all()
            return [t.to_dict() for t in tasks]
        finally:
            db.close()


# 全局调度器实例
scheduler = StepScheduler()
