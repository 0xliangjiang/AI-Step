# -*- coding: utf-8 -*-
"""
定时刷步调度器
"""
import time
import threading
import math
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.exc import OperationalError

from models import ScheduledTask, User, SessionLocal, get_db_session
from config import APP_DEBUG, USE_PROXY, USE_PROXY_MODE

# 导入 step_brush
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from step_brush import ZeppAPI
from step_brush import bindband

# 配置日志
logger = logging.getLogger(__name__)
if APP_DEBUG:
    logging.basicConfig(level=logging.DEBUG)


def get_beijing_time() -> datetime:
    """获取北京时间（UTC+8）"""
    return datetime.utcnow() + timedelta(hours=8)


class StepScheduler:
    """定时刷步调度器"""

    def __init__(self):
        self.running = False
        self.thread = None
        self.interval = 60  # 检查间隔（秒）

    def log(self, msg: str):
        if APP_DEBUG:
            logger.debug(f"[Scheduler] {msg}")
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
        now = get_beijing_time()
        current_hour = now.hour
        current_date = now.strftime("%Y-%m-%d")
        max_retries = 2

        for attempt in range(max_retries):
            try:
                with get_db_session() as db:
                    # 查找所有活跃的定时任务
                    tasks = db.query(ScheduledTask).filter(
                        ScheduledTask.status == "active"
                    ).all()

                    for task in tasks:
                        self._process_task(task, current_hour, current_date, db)
                    return
            except OperationalError as e:
                self.log(f"数据库连接异常，第 {attempt + 1}/{max_retries} 次重试: {e}")
                time.sleep(1)
            except Exception as e:
                self.log(f"调度执行异常: {e}")
                return

        self.log("数据库连接异常，已跳过本轮调度")

    def _process_task(self, task: ScheduledTask, current_hour: int, current_date: str, db):
        """处理单个任务"""
        # 检查用户会员状态
        now = get_beijing_time()
        user = db.query(User).filter(User.user_key == task.user_key).first()
        if not user or not user.vip_expire_at or user.vip_expire_at < now:
            self.log(f"任务 {task.user_key} 用户会员已过期，跳过执行")
            return

        # 检查是否是新的一天，重置进度
        if task.last_run_date != current_date:
            task.current_steps = 0
            task.current_step_index = 0
            task.last_run_date = current_date
            self.log(f"任务 {task.user_key} 新的一天，重置进度")

        # 检查是否在执行时间范围内
        if not (task.start_hour <= current_hour < task.end_hour):
            return

        total_hours = task.end_hour - task.start_hour

        # 计算当前应该执行到哪个时段
        expected_index = current_hour - task.start_hour

        # 如果已经执行过当前时段，跳过
        if task.current_step_index > expected_index:
            return

        # 计算基础步数（按总时段平均分配）
        base_steps_per_hour = math.ceil(task.target_steps / total_hours)

        # 确定本次要执行的时段：执行下一个未执行的时段
        slot_to_execute = task.current_step_index

        # 如果当前时段已经超过要执行的时段，只执行当前应该执行的时段
        # 而不是一次性补齐所有错过的时段
        if slot_to_execute < expected_index:
            # 错过了多个时段，只执行下一个时段，让后续调度继续补
            self.log(f"任务 {task.user_key}: 检测到错过时段，当前时段 {expected_index + 1}，将执行时段 {slot_to_execute + 1}")

        # 计算本次应该达到的累计步数
        # 最后一个时段补齐剩余步数，其他时段按平均值
        if slot_to_execute == total_hours - 1:
            target_current_steps = task.target_steps
        else:
            # 使用固定平均值，确保稳定递增
            target_current_steps = (slot_to_execute + 1) * base_steps_per_hour
            # 不超过目标
            target_current_steps = min(target_current_steps, task.target_steps)

        # 如果当前已经达到或超过本次目标，跳过
        if task.current_steps >= target_current_steps:
            task.current_step_index = slot_to_execute + 1
            return

        steps_to_add = target_current_steps - task.current_steps
        self.log(f"任务 {task.user_key}: 时段 {slot_to_execute + 1}/{total_hours}, "
                f"当前 {task.current_steps} → 目标 {target_current_steps}")

        # 执行刷步（传入累计目标值，不是增量）
        success = self._execute_brush_step(task.user_key, target_current_steps)

        if success:
            task.current_steps = target_current_steps
            task.current_step_index = slot_to_execute + 1
            task.last_run_at = get_beijing_time()
            self.log(f"任务 {task.user_key} 刷步成功: 已刷到 {target_current_steps} 步")
        else:
            self.log(f"任务 {task.user_key} 刷步失败")

    def _execute_brush_step(self, user_key: str, target_steps: int) -> bool:
        """执行刷步（设置目标步数，非增量）"""
        try:
            with get_db_session() as db:
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
                    result = api.update_step(target_steps)
                else:
                    result = bindband(
                        user.zepp_email,
                        user.zepp_password,
                        step=target_steps,
                        verbose=APP_DEBUG,
                        use_proxy=False
                    )

                return result.get("success", False)
        except Exception as e:
            self.log(f"刷步异常: {e}")
            return False

    # ==================== 任务管理方法 ====================

    def create_task(self, user_key: str, target_steps: int,
                   start_hour: int = 8, end_hour: int = 21) -> dict:
        """创建定时任务"""
        with get_db_session() as db:
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
            db.flush()  # 获取ID

            return {
                "success": True,
                "message": f"已创建定时任务：每天 {start_hour}:00-{end_hour}:00 完成 {target_steps} 步",
                "task": task.to_dict()
            }

    def get_task(self, user_key: str) -> Optional[Dict[str, Any]]:
        """获取用户的定时任务"""
        with get_db_session() as db:
            task = db.query(ScheduledTask).filter(
                ScheduledTask.user_key == user_key,
                ScheduledTask.status.in_(["active", "paused"])
            ).first()

            return task.to_dict() if task else None

    def get_task_detail(self, user_key: str) -> dict:
        """获取定时任务详情，包含每小时刷步计划"""
        with get_db_session() as db:
            task = db.query(ScheduledTask).filter(
                ScheduledTask.user_key == user_key,
                ScheduledTask.status.in_(["active", "paused"])
            ).first()

            if not task:
                return {"success": False, "message": "您还没有设置定时任务"}

            # 计算每小时步数分配
            target_steps = task.target_steps
            start_hour = task.start_hour
            end_hour = task.end_hour
            total_hours = end_hour - start_hour

            # 生成每小时计划
            hourly_plan = []
            remaining_steps = target_steps
            for hour in range(start_hour, end_hour):
                remaining_slots = end_hour - hour
                if remaining_slots == 1:
                    steps_this_hour = remaining_steps
                else:
                    steps_this_hour = math.ceil(remaining_steps / remaining_slots)

                cumulative = target_steps - remaining_steps + steps_this_hour
                hourly_plan.append({
                    "hour": hour,
                    "time": f"{hour}:00",
                    "steps_this_hour": steps_this_hour,
                    "cumulative_steps": cumulative
                })
                remaining_steps -= steps_this_hour

            status_text = {"active": "执行中", "paused": "已暂停"}.get(task.status, task.status)

            return {
                "success": True,
                "task": task.to_dict(),
                "hourly_plan": hourly_plan,
                "summary": {
                    "target_steps": target_steps,
                    "time_range": f"{start_hour}:00-{end_hour}:00",
                    "total_hours": total_hours,
                    "avg_steps_per_hour": math.ceil(target_steps / total_hours) if total_hours > 0 else 0,
                    "status": status_text,
                    "current_steps": task.current_steps,
                    "current_progress": f"{task.current_steps}/{target_steps}",
                    "note": "每小时设置累计目标步数（非增量）"
                },
                "message": f"定时任务详情：每天 {start_hour}:00-{end_hour}:00 刷到 {target_steps} 步，共 {total_hours} 个时段，每小时递增至目标"
            }

    def update_task(self, user_key: str, target_steps: int = None,
                   start_hour: int = None, end_hour: int = None) -> dict:
        """更新定时任务"""
        with get_db_session() as db:
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

            return {
                "success": True,
                "message": f"定时任务已更新：每天 {task.start_hour}:00-{task.end_hour}:00 完成 {task.target_steps} 步",
                "task": task.to_dict()
            }

    def pause_task(self, user_key: str) -> dict:
        """暂停定时任务"""
        with get_db_session() as db:
            task = db.query(ScheduledTask).filter(
                ScheduledTask.user_key == user_key,
                ScheduledTask.status == "active"
            ).first()

            if not task:
                return {"success": False, "message": "没有找到活跃的定时任务"}

            task.status = "paused"

            return {"success": True, "message": "定时任务已暂停"}

    def resume_task(self, user_key: str) -> dict:
        """恢复定时任务"""
        with get_db_session() as db:
            task = db.query(ScheduledTask).filter(
                ScheduledTask.user_key == user_key,
                ScheduledTask.status == "paused"
            ).first()

            if not task:
                return {"success": False, "message": "没有找到暂停的定时任务"}

            task.status = "active"

            return {"success": True, "message": "定时任务已恢复"}

    def cancel_task(self, user_key: str) -> dict:
        """取消定时任务"""
        with get_db_session() as db:
            task = db.query(ScheduledTask).filter(
                ScheduledTask.user_key == user_key,
                ScheduledTask.status.in_(["active", "paused"])
            ).first()

            if not task:
                return {"success": False, "message": "没有找到定时任务"}

            task.status = "cancelled"

            return {"success": True, "message": "定时任务已取消"}

    def get_all_active_tasks(self) -> list:
        """获取所有活跃任务（后台管理用）"""
        with get_db_session() as db:
            tasks = db.query(ScheduledTask).filter(
                ScheduledTask.status.in_(["active", "paused"])
            ).all()
            return [t.to_dict() for t in tasks]


# 全局调度器实例
scheduler = StepScheduler()
