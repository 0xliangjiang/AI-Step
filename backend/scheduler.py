# -*- coding: utf-8 -*-
"""
定时刷步调度器
"""
import time
import threading
import math
import logging
import json
import random
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.exc import OperationalError

from models import ScheduledTask, User, SessionLocal, get_db_session, StepRecord, ensure_runtime_schema
from config import APP_DEBUG, USE_PROXY, USE_PROXY_MODE

# 导入 step_brush
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from step_brush import ZeppAPI
from step_brush import bindband
from time_utils import get_china_now

# 重试装饰器
def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    重试装饰器，用于网络请求失败时自动重试
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = None
            current_delay = delay
            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    if result.get('success'):
                        return result
                    error_msg = result.get('message', '')
                    if any(keyword in error_msg for keyword in ['未配置', '不存在', '无效', '格式错误', '参数']):
                        return result
                    last_error = error_msg
                    if attempt < max_retries - 1:
                        print(f"[Retry] {func.__name__} 第 {attempt + 1} 次失败: {error_msg}，{current_delay}秒后重试")
                        import time as time_module
                        time_module.sleep(current_delay)
                        current_delay *= backoff
                except Exception as e:
                    last_error = str(e)
                    if attempt < max_retries - 1:
                        print(f"[Retry] {func.__name__} 第 {attempt + 1} 次异常: {e}，{current_delay}秒后重试")
                        import time as time_module
                        time_module.sleep(current_delay)
                        current_delay *= backoff
            return {'success': False, 'message': f'请求失败（已重试{max_retries}次）: {last_error}'}
        return wrapper
    return decorator


@retry_on_failure(max_retries=3, delay=1.0, backoff=2.0)
def _bindband_with_retry_scheduler(email: str, password: str, step: int, verbose: bool, use_proxy: bool) -> dict:
    """带重试机制的绑定手环/刷步接口"""
    return bindband(email, password, step=step, verbose=verbose, use_proxy=use_proxy)

# 配置日志
logger = logging.getLogger(__name__)
if APP_DEBUG:
    logging.basicConfig(level=logging.DEBUG)

SYNC_LOG_PREFIX = "scheduled_sync"


def get_beijing_time() -> datetime:
    """获取北京时间（UTC+8）"""
    return get_china_now()


class StepScheduler:
    """定时刷步调度器"""

    def __init__(self):
        self.running = False
        self.thread = None

    def log(self, msg: str):
        if APP_DEBUG:
            logger.debug(f"[Scheduler] {msg}")
            print(f"[Scheduler] {msg}")

    def _ensure_scheduled_tasks_schema(self):
        """在查询定时任务前先修复旧库结构，避免老表缺列直接炸掉。"""
        ensure_runtime_schema()

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

            now = get_beijing_time()
            next_scan_at = self._next_scan_time(now)
            wait_seconds = self._seconds_until_next_scan(now)
            self.log(f"下次扫描时间：{next_scan_at.strftime('%Y-%m-%d %H:%M:%S')}")
            sleep_until = time.time() + wait_seconds
            while self.running and time.time() < sleep_until:
                time.sleep(min(1, max(0, sleep_until - time.time())))

    def _seconds_until_next_scan(self, now: Optional[datetime] = None) -> int:
        """计算距离下一个整点扫描还有多少秒。"""
        now = now or get_beijing_time()
        next_scan_at = self._next_scan_time(now)
        wait_seconds = int((next_scan_at - now).total_seconds())
        return max(wait_seconds, 1)

    def _next_scan_time(self, now: Optional[datetime] = None) -> datetime:
        """获取下一次整点扫描的北京时间。"""
        now = now or get_beijing_time()
        return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    def _check_and_execute(self):
        """检查并执行定时任务"""
        now = get_beijing_time()
        current_hour = now.hour
        current_date = now.strftime("%Y-%m-%d")
        max_retries = 2

        for attempt in range(max_retries):
            try:
                self._ensure_scheduled_tasks_schema()
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
            self._reset_task_for_new_day(task, current_date)

        # 检查是否在执行时间范围内
        if not (task.start_hour <= current_hour < task.end_hour):
            return

        total_hours = task.end_hour - task.start_hour
        daily_plan = self._load_daily_plan(task, total_hours)

        # 计算当前应该执行到哪个时段
        expected_index = current_hour - task.start_hour

        # 如果已经执行过当前时段，跳过
        if task.current_step_index > expected_index:
            return

        # 每小时扫描一次时，只执行一个时段。
        # 如果前一个应执行时段错过了，优先补最早漏掉的那个。
        slot_to_execute = task.current_step_index

        execution_mode = "正常执行"
        if slot_to_execute < expected_index:
            execution_mode = "补执行"
            self.log(
                f"任务 {task.user_key}: 检测到漏执行时段，"
                f"本轮补执行时段 {slot_to_execute + 1}，当前已到时段 {expected_index + 1}"
            )

        target_current_steps = daily_plan[slot_to_execute]

        # 如果当前已经达到或超过本次目标，跳过
        if task.current_steps >= target_current_steps:
            task.current_step_index = slot_to_execute + 1
            return

        steps_to_add = target_current_steps - task.current_steps
        self.log(
            f"任务 {task.user_key}: {execution_mode}，时段 {slot_to_execute + 1}/{total_hours}, "
            f"当前 {task.current_steps} → 目标 {target_current_steps}"
        )

        # 执行刷步（传入累计目标值，不是增量）
        task.last_attempt_at = now
        result = self._execute_brush_step(task.user_key, target_current_steps)

        if result.get("success"):
            task.current_steps = target_current_steps
            task.current_step_index = slot_to_execute + 1
            task.last_run_at = now
            task.last_success_at = now
            task.last_error = ""
            task.last_error_type = ""
            task.consecutive_failures = 0
            self._append_sync_record(
                db=db,
                task=task,
                steps=target_current_steps,
                status="success",
                execution_mode=execution_mode,
                detail=f"本次状态已更新至 {target_current_steps} 步"
            )
            self.log(f"任务 {task.user_key} 刷步成功: 已刷到 {target_current_steps} 步")
        else:
            task.last_error = result.get("message", "未知错误")
            task.last_error_type = result.get("error_type", "brush_step_failed")
            task.consecutive_failures = (task.consecutive_failures or 0) + 1
            self._append_sync_record(
                db=db,
                task=task,
                steps=target_current_steps,
                status="failed",
                execution_mode=execution_mode,
                detail=task.last_error
            )
            self.log(f"任务 {task.user_key} 刷步失败: {task.last_error}")

    def _append_sync_record(self, db, task: ScheduledTask, steps: int, status: str, execution_mode: str, detail: str):
        db.add(StepRecord(
            user_key=task.user_key,
            steps=steps,
            status=status,
            message=f"{SYNC_LOG_PREFIX}|{status}|{execution_mode}|{detail}"
        ))

    def _generate_daily_plan(self, target_steps: int, total_hours: int):
        if total_hours <= 0:
            return [target_steps]

        weights = []
        for index in range(total_hours):
            progress = (index + 1) / total_hours
            base_weight = math.pow(progress, 1.8) * 100
            jitter = random.uniform(0.65, 1.35)
            weights.append(max(base_weight * jitter, 1.0))

        total_weight = sum(weights) or 1.0
        increments = []
        allocated = 0
        for index, weight in enumerate(weights):
            if index == total_hours - 1:
                increment = target_steps - allocated
            else:
                raw_value = target_steps * weight / total_weight
                increment = max(1, int(round(raw_value)))
                remaining_slots = total_hours - index - 1
                max_allowed = target_steps - allocated - remaining_slots
                increment = min(increment, max_allowed)
            allocated += increment
            increments.append(increment)

        cumulative = []
        running = 0
        for increment in increments:
            running += increment
            cumulative.append(running)

        cumulative[-1] = target_steps
        return cumulative

    def _load_daily_plan(self, task: ScheduledTask, total_hours: int):
        if task.daily_plan:
            try:
                plan = json.loads(task.daily_plan)
                if len(plan) == total_hours and plan[-1] == task.target_steps:
                    return plan
            except Exception:
                pass

        plan = self._generate_daily_plan(task.target_steps, total_hours)
        task.daily_plan = json.dumps(plan, ensure_ascii=False)
        self.log(f"任务 {task.user_key} 今日随机计划已生成: {plan}")
        return plan

    @staticmethod
    def _is_retryable_brush_message(message: str) -> bool:
        text = (message or "").lower()
        retryable_keywords = [
            "timeout",
            "timed out",
            "connection reset",
            "reset by peer",
            "awaiting headers",
            "proxy",
            "tlsclient",
            "tls client",
            "connection aborted",
            "temporary failure",
            "temporarily unavailable",
            "network",
            "eof",
        ]
        return any(keyword in text for keyword in retryable_keywords)

    def _safe_update_step(self, api: ZeppAPI, target_steps: int) -> dict:
        try:
            return api.update_step(target_steps)
        except Exception as e:
            self.log(f"刷步异常: {e}")
            return {"success": False, "message": str(e), "error_type": "exception"}

    def _reset_task_for_new_day(self, task: ScheduledTask, current_date: str):
        """新的一天重置任务进度与失败状态，避免前一天状态干扰当天执行。"""
        total_hours = max(task.end_hour - task.start_hour, 1)
        task.current_steps = 0
        task.current_step_index = 0
        task.daily_plan = json.dumps(
            self._generate_daily_plan(task.target_steps, total_hours),
            ensure_ascii=False
        )
        task.last_run_date = current_date
        task.last_error = ""
        task.last_error_type = ""
        task.consecutive_failures = 0
        self.log(f"任务 {task.user_key} 新的一天，重置进度")

    def _execute_brush_step(self, user_key: str, target_steps: int) -> Dict[str, Any]:
        """执行刷步（设置目标步数，非增量）"""
        try:
            with get_db_session() as db:
                user = db.query(User).filter(User.user_key == user_key).first()
                if not user or not user.zepp_email:
                    return {"success": False, "message": "用户未注册设备", "error_type": "user_missing"}
                if user.bind_status != 1:
                    return {"success": False, "message": "用户未完成绑定", "error_type": "bind_status"}

                result = _bindband_with_retry_scheduler(
                    user.zepp_email,
                    user.zepp_password,
                    step=target_steps,
                    verbose=APP_DEBUG,
                    use_proxy=False
                )

                if result.get("success", False):
                    return {"success": True, "message": result.get("message", "ok")}
                return {
                    "success": False,
                    "message": result.get("message", "刷步失败"),
                    "error_type": result.get("error_type", "api_error")
                }
        except Exception as e:
            self.log(f"刷步异常: {e}")
            return {"success": False, "message": str(e), "error_type": "exception"}

    # ==================== 任务管理方法 ====================

    def create_task(self, user_key: str, target_steps: int,
                   start_hour: int = 8, end_hour: int = 21) -> dict:
        """创建定时任务"""
        self._ensure_scheduled_tasks_schema()
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
                existing.daily_plan = None
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
        self._ensure_scheduled_tasks_schema()
        with get_db_session() as db:
            task = db.query(ScheduledTask).filter(
                ScheduledTask.user_key == user_key,
                ScheduledTask.status.in_(["active", "paused"])
            ).first()

            return task.to_dict() if task else None

    def get_task_detail(self, user_key: str) -> dict:
        """获取定时任务详情，包含每小时刷步计划"""
        self._ensure_scheduled_tasks_schema()
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
            daily_plan = self._load_daily_plan(task, total_hours)

            # 生成每小时计划（展示每个时段增量及累计目标）
            hourly_plan = []
            previous_cumulative = 0
            for index, hour in enumerate(range(start_hour, end_hour)):
                cumulative = daily_plan[index]
                steps_this_hour = cumulative - previous_cumulative
                hourly_plan.append({
                    "hour": hour,
                    "time": f"{hour}:00",
                    "steps_this_hour": steps_this_hour,
                    "cumulative_steps": cumulative
                })
                previous_cumulative = cumulative

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
                    "note": "每天生成前少后多的随机累计目标计划"
                },
                "message": f"定时任务详情：每天 {start_hour}:00-{end_hour}:00 刷到 {target_steps} 步，共 {total_hours} 个时段，按随机递增计划完成目标"
            }

    def update_task(self, user_key: str, target_steps: int = None,
                   start_hour: int = None, end_hour: int = None) -> dict:
        """更新定时任务"""
        self._ensure_scheduled_tasks_schema()
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
        self._ensure_scheduled_tasks_schema()
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
        self._ensure_scheduled_tasks_schema()
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
        self._ensure_scheduled_tasks_schema()
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
        self._ensure_scheduled_tasks_schema()
        with get_db_session() as db:
            tasks = db.query(ScheduledTask).filter(
                ScheduledTask.status.in_(["active", "paused"])
            ).all()
            return [t.to_dict() for t in tasks]


# 全局调度器实例
scheduler = StepScheduler()
