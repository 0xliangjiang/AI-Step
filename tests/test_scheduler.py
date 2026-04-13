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

    def test_seconds_until_next_scan_waits_until_next_hour_boundary(self):
        wait_seconds = self.scheduler._seconds_until_next_scan(
            datetime(2026, 4, 13, 10, 15, 30)
        )
        self.assertEqual(2670, wait_seconds)

        exact_hour_wait = self.scheduler._seconds_until_next_scan(
            datetime(2026, 4, 13, 10, 0, 0)
        )
        self.assertEqual(3600, exact_hour_wait)

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
        self.assertEqual(0, task.current_step_index)
        self.assertEqual(0, task.current_steps)

    def test_process_task_catches_up_oldest_missed_hour_once_per_scan(self):
        task = _FakeTask()
        task.target_steps = 1200
        task.start_hour = 8
        task.end_hour = 11
        task.current_steps = 400
        task.current_step_index = 1
        task.last_run_date = "2026-04-13"
        user = _FakeUser(vip_expire_at=datetime(2026, 4, 14, 0, 0, 0))
        db = _FakeDb(user)

        with patch("scheduler.get_beijing_time", return_value=self.fixed_now), patch.object(
            self.scheduler,
            "_execute_brush_step",
            return_value={"success": True, "message": "ok"},
        ) as mock_execute:
            self.scheduler._process_task(task, current_hour=10, current_date="2026-04-13", db=db)

        mock_execute.assert_called_once_with(task.user_key, 800)
        self.assertEqual(800, task.current_steps)
        self.assertEqual(2, task.current_step_index)
        self.assertEqual(self.fixed_now, task.last_run_at)

    def test_process_task_logs_catch_up_and_normal_slot_modes(self):
        user = _FakeUser(vip_expire_at=datetime(2026, 4, 14, 0, 0, 0))
        db = _FakeDb(user)

        catch_up_task = _FakeTask()
        catch_up_task.target_steps = 1200
        catch_up_task.start_hour = 8
        catch_up_task.end_hour = 11
        catch_up_task.current_steps = 400
        catch_up_task.current_step_index = 1
        catch_up_task.last_run_date = "2026-04-13"

        normal_task = _FakeTask()
        normal_task.target_steps = 1200
        normal_task.start_hour = 8
        normal_task.end_hour = 11
        normal_task.current_steps = 800
        normal_task.current_step_index = 2
        normal_task.last_run_date = "2026-04-13"

        with patch("scheduler.get_beijing_time", return_value=self.fixed_now), patch.object(
            self.scheduler,
            "_execute_brush_step",
            return_value={"success": True, "message": "ok"},
        ), patch.object(self.scheduler, "log") as mock_log:
            self.scheduler._process_task(catch_up_task, current_hour=10, current_date="2026-04-13", db=db)
            self.scheduler._process_task(normal_task, current_hour=10, current_date="2026-04-13", db=db)

        messages = [args[0] for args, _ in mock_log.call_args_list]
        self.assertTrue(any("补执行" in message for message in messages))
        self.assertTrue(any("正常执行" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
