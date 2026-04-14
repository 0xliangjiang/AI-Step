import unittest
import json
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
        self.records = []

    def query(self, model):
        return self

    def filter(self, *args, **kwargs):
        return _FakeFilter(self._user)

    def add(self, record):
        self.records.append(record)


class _FakeUser:
    def __init__(self, vip_expire_at):
        self.vip_expire_at = vip_expire_at
        self.zepp_email = "pool@example.com"
        self.zepp_password = "secret"
        self.zepp_userid = "zepp-user-1"
        self.bind_status = 1


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
        self.daily_plan = None

    def to_dict(self):
        return {
            "user_key": self.user_key,
            "target_steps": self.target_steps,
            "start_hour": self.start_hour,
            "end_hour": self.end_hour,
            "status": self.status,
            "current_steps": self.current_steps,
            "current_step_index": self.current_step_index,
            "daily_plan": self.daily_plan,
        }


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

    def test_next_scan_time_is_reported_in_beijing_time(self):
        next_scan_at = self.scheduler._next_scan_time(
            datetime(2026, 4, 13, 10, 15, 30)
        )
        self.assertEqual("2026-04-13 11:00:00", next_scan_at.strftime("%Y-%m-%d %H:%M:%S"))

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
        task.daily_plan = json.dumps([300, 800, 1200], ensure_ascii=False)
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
        catch_up_task.daily_plan = json.dumps([300, 800, 1200], ensure_ascii=False)

        normal_task = _FakeTask()
        normal_task.target_steps = 1200
        normal_task.start_hour = 8
        normal_task.end_hour = 11
        normal_task.current_steps = 800
        normal_task.current_step_index = 2
        normal_task.last_run_date = "2026-04-13"
        normal_task.daily_plan = json.dumps([300, 800, 1200], ensure_ascii=False)

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

    def test_generate_daily_plan_is_front_light_and_back_heavy(self):
        plan = self.scheduler._generate_daily_plan(target_steps=13000, total_hours=6)

        self.assertEqual(6, len(plan))
        self.assertEqual(13000, plan[-1])
        increments = [plan[0]] + [plan[i] - plan[i - 1] for i in range(1, len(plan))]
        self.assertTrue(all(value > 0 for value in increments))
        self.assertGreater(sum(increments[3:]), sum(increments[:3]))

    def test_reset_task_for_new_day_generates_fresh_daily_plan(self):
        task = _FakeTask()
        task.target_steps = 12000
        task.start_hour = 8
        task.end_hour = 14

        with patch("scheduler.random.uniform", side_effect=[0.2, 0.4, 0.6, 0.8, 1.0, 1.2]):
            self.scheduler._reset_task_for_new_day(task, "2026-04-13")

        self.assertEqual("2026-04-13", task.last_run_date)
        self.assertIsNotNone(task.daily_plan)
        plan = json.loads(task.daily_plan)
        self.assertEqual(6, len(plan))
        self.assertEqual(12000, plan[-1])

    def test_get_task_detail_uses_saved_daily_plan_for_hourly_breakdown(self):
        task = _FakeTask()
        task.target_steps = 1200
        task.start_hour = 8
        task.end_hour = 11
        task.current_steps = 800
        task.daily_plan = json.dumps([200, 500, 1200], ensure_ascii=False)
        db = _FakeDb(task)

        with patch("scheduler.get_db_session") as session_mock:
            session_mock.return_value.__enter__.return_value = db
            result = self.scheduler.get_task_detail(task.user_key)

        self.assertTrue(result["success"])
        self.assertEqual(
            [
                {"hour": 8, "time": "8:00", "steps_this_hour": 200, "cumulative_steps": 200},
                {"hour": 9, "time": "9:00", "steps_this_hour": 300, "cumulative_steps": 500},
                {"hour": 10, "time": "10:00", "steps_this_hour": 700, "cumulative_steps": 1200},
            ],
            result["hourly_plan"],
        )
        self.assertEqual("800/1200", result["summary"]["current_progress"])

    def test_execute_brush_step_retries_retryable_network_failures_up_to_three_times(self):
        user = _FakeUser(vip_expire_at=datetime(2026, 4, 14, 0, 0, 0))
        db = _FakeDb(user)

        with patch("scheduler.get_db_session"), patch(
            "scheduler._bindband_with_retry_scheduler",
            return_value={"success": True, "message": "ok"},
        ) as bindband_mock, patch(
            "scheduler.USE_PROXY_MODE",
            True,
        ), patch(
            "scheduler.USE_PROXY",
            True,
        ), patch("scheduler.ZeppAPI") as zepp_mock:
            scheduler_module.get_db_session.return_value.__enter__.return_value = db
            result = self.scheduler._execute_brush_step("user-1", 12000)

        self.assertTrue(result["success"])
        bindband_mock.assert_called_once_with(
            "pool@example.com",
            "secret",
            step=12000,
            verbose=scheduler_module.APP_DEBUG,
            use_proxy=False,
        )
        zepp_mock.assert_not_called()

    def test_execute_brush_step_does_not_retry_non_retryable_business_failure(self):
        user = _FakeUser(vip_expire_at=datetime(2026, 4, 14, 0, 0, 0))
        db = _FakeDb(user)

        with patch("scheduler.get_db_session"), patch(
            "scheduler._bindband_with_retry_scheduler",
            return_value={"success": False, "message": "参数无效"},
        ) as bindband_mock, patch(
            "scheduler.USE_PROXY_MODE",
            True,
        ), patch(
            "scheduler.USE_PROXY",
            True,
        ):
            scheduler_module.get_db_session.return_value.__enter__.return_value = db
            result = self.scheduler._execute_brush_step("user-1", 12000)

        self.assertFalse(result["success"])
        bindband_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
