import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

import scheduler as scheduler_module


class _FakeFilter:
    def __init__(self, result):
        self._result = result

    def first(self):
        return self._result


class _FakeDb:
    def __init__(self, user):
        self._user = user

    def query(self, model):
        return self

    def filter(self, *args, **kwargs):
        return _FakeFilter(self._user)


class _FakeUser:
    def __init__(self, vip_expire_at):
        self.vip_expire_at = vip_expire_at


class _FakeTask:
    def __init__(self):
        self.user_key = "user-1"
        self.target_steps = 50000
        self.start_hour = 8
        self.end_hour = 21
        self.status = "active"
        self.current_steps = 2000
        self.current_step_index = 3
        self.last_run_at = None
        self.last_run_date = "2026-04-12"
        self.last_attempt_at = None
        self.last_success_at = None
        self.last_error = "old error"
        self.last_error_type = "old_type"
        self.consecutive_failures = 2


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.scheduler = scheduler_module.StepScheduler()
        self.fixed_now = datetime(2026, 4, 13, 10, 0, 0)

    def test_process_task_resets_progress_on_new_day_and_clears_failure_state_on_success(self):
        task = _FakeTask()
        user = _FakeUser(vip_expire_at=datetime(2026, 4, 14, 0, 0, 0))
        db = _FakeDb(user)

        with patch("scheduler.get_beijing_time", return_value=self.fixed_now), patch.object(
            self.scheduler,
            "_execute_brush_step",
            return_value={"success": True, "message": "ok"},
        ):
            self.scheduler._process_task(task, current_hour=10, current_date="2026-04-13", db=db)

        self.assertEqual("2026-04-13", task.last_run_date)
        self.assertEqual(0, task.consecutive_failures)
        self.assertEqual("", task.last_error)
        self.assertEqual("", task.last_error_type)
        self.assertEqual(self.fixed_now, task.last_attempt_at)
        self.assertEqual(self.fixed_now, task.last_success_at)
        self.assertEqual(self.fixed_now, task.last_run_at)
        self.assertGreater(task.current_steps, 0)

    def test_process_task_records_failure_reason_without_losing_task(self):
        task = _FakeTask()
        user = _FakeUser(vip_expire_at=datetime(2026, 4, 14, 0, 0, 0))
        db = _FakeDb(user)

        with patch("scheduler.get_beijing_time", return_value=self.fixed_now), patch.object(
            self.scheduler,
            "_execute_brush_step",
            return_value={
                "success": False,
                "message": "bind status invalid",
                "error_type": "bind_status",
            },
        ):
            self.scheduler._process_task(task, current_hour=10, current_date="2026-04-13", db=db)

        self.assertEqual(self.fixed_now, task.last_attempt_at)
        self.assertIsNone(task.last_success_at)
        self.assertEqual("bind status invalid", task.last_error)
        self.assertEqual("bind_status", task.last_error_type)
        self.assertEqual(1, task.consecutive_failures)
        self.assertEqual(2, task.current_step_index)
        self.assertEqual(0, task.current_steps)


if __name__ == "__main__":
    unittest.main()
