import sys
import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

import skills as skills_module


class _FakeDbUser:
    def __init__(self):
        self.login_token = "cached-login"
        self.app_token = "cached-app"
        self.token_updated_at = datetime.now() - timedelta(minutes=20)
        self.bind_status = 1


class _FakeQuery:
    def __init__(self, db_user):
        self.db_user = db_user

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.db_user


class _FakeDb:
    def __init__(self, db_user):
        self.db_user = db_user
        self.records = []

    def query(self, *args, **kwargs):
        return _FakeQuery(self.db_user)

    def add(self, record):
        self.records.append(record)


class StepSkillsDirectBrushTests(unittest.TestCase):
    def setUp(self):
        self.db_user = _FakeDbUser()
        self.db = _FakeDb(self.db_user)
        self.user = {
            "user_key": "user-1",
            "zepp_email": "pool@example.com",
            "zepp_password": "secret",
            "zepp_userid": "zepp-user-1",
            "bind_status": 1,
            "vip_expire_at": datetime.now() + timedelta(days=3),
            "login_token": "cached-login",
            "app_token": "cached-app",
            "token_updated_at": datetime.now() - timedelta(minutes=20),
        }

    @contextmanager
    def fake_db_session(self):
        yield self.db

    def test_brush_step_uses_direct_bindband_even_when_proxy_mode_is_on(self):
        with patch.object(skills_module.skills, "get_user", return_value=self.user), patch(
            "skills._bindband_with_retry",
            return_value={"success": True, "message": "ok"},
        ) as bindband_mock, patch("skills._login_with_proxy") as login_mock, patch(
            "skills.ZeppAPI"
        ) as zepp_mock, patch(
            "skills.get_db_session",
            self.fake_db_session,
        ), patch(
            "skills.USE_PROXY_MODE",
            True,
        ):
            result = skills_module.skills.brush_step("user-1", 8888)

        self.assertTrue(result["success"])
        bindband_mock.assert_called_once_with(
            "pool@example.com",
            "secret",
            step=8888,
            verbose=skills_module.APP_DEBUG,
            use_proxy=False,
        )
        login_mock.assert_not_called()
        zepp_mock.assert_not_called()

    def test_brush_step_still_requires_bind_status_before_direct_brush(self):
        self.user["bind_status"] = 0

        with patch.object(skills_module.skills, "get_user", return_value=self.user), patch(
            "skills._bindband_with_retry"
        ) as bindband_mock, patch(
            "skills.USE_PROXY_MODE",
            True,
        ):
            result = skills_module.skills.brush_step("user-1", 8888)

        self.assertFalse(result["success"])
        self.assertIn("您还没有绑定设备", result["message"])
        bindband_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
