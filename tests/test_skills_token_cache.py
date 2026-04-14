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
        self.login_token = None
        self.app_token = None
        self.token_updated_at = None


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


class _FakeAPI:
    update_calls = []
    update_results = []

    def __init__(self, *args, **kwargs):
        self.login_token = None
        self.app_token = None
        self.userid = None

    def update_step(self, steps):
        _FakeAPI.update_calls.append(
            {
                "steps": steps,
                "login_token": self.login_token,
                "app_token": self.app_token,
                "userid": self.userid,
            }
        )
        if _FakeAPI.update_results:
            return _FakeAPI.update_results.pop(0)
        return {"success": True, "message": "ok"}


class StepSkillsTokenCacheTests(unittest.TestCase):
    def setUp(self):
        _FakeAPI.update_calls = []
        _FakeAPI.update_results = []
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
        }

    @contextmanager
    def fake_db_session(self):
        yield self.db

    def test_brush_step_relogs_before_using_token_older_than_one_hour(self):
        self.user["token_updated_at"] = datetime.now() - timedelta(hours=2)
        _FakeAPI.update_results = [{"success": True, "message": "ok"}]

        with patch.object(skills_module.skills, "get_user", return_value=self.user), patch(
            "skills.ZeppAPI",
            _FakeAPI,
        ), patch(
            "skills._login_with_proxy",
            return_value={
                "success": True,
                "userid": "fresh-user",
                "login_token": "fresh-login",
                "app_token": "fresh-app",
            },
        ) as login_mock, patch("skills.get_db_session", self.fake_db_session), patch(
            "skills.USE_PROXY_MODE",
            True,
        ), patch(
            "skills.USE_PROXY",
            True,
        ):
            result = skills_module.skills.brush_step("user-1", 8888)

        self.assertTrue(result["success"])
        self.assertEqual(1, login_mock.call_count)
        self.assertEqual(1, len(_FakeAPI.update_calls))
        self.assertEqual("fresh-login", _FakeAPI.update_calls[0]["login_token"])
        self.assertEqual("fresh-app", _FakeAPI.update_calls[0]["app_token"])

    def test_brush_step_reuses_cached_token_within_one_hour(self):
        self.user["token_updated_at"] = datetime.now() - timedelta(minutes=30)
        _FakeAPI.update_results = [{"success": True, "message": "ok"}]

        with patch.object(skills_module.skills, "get_user", return_value=self.user), patch(
            "skills.ZeppAPI",
            _FakeAPI,
        ), patch(
            "skills._login_with_proxy",
            return_value={
                "success": True,
                "userid": "fresh-user",
                "login_token": "fresh-login",
                "app_token": "fresh-app",
            },
        ) as login_mock, patch("skills.get_db_session", self.fake_db_session), patch(
            "skills.USE_PROXY_MODE",
            True,
        ), patch(
            "skills.USE_PROXY",
            True,
        ):
            result = skills_module.skills.brush_step("user-1", 8888)

        self.assertTrue(result["success"])
        self.assertEqual(0, login_mock.call_count)
        self.assertEqual(1, len(_FakeAPI.update_calls))
        self.assertEqual("cached-login", _FakeAPI.update_calls[0]["login_token"])
        self.assertEqual("cached-app", _FakeAPI.update_calls[0]["app_token"])

    def test_brush_step_retries_with_relogin_when_fresh_cached_token_fails(self):
        self.user["token_updated_at"] = datetime.now() - timedelta(minutes=20)
        _FakeAPI.update_results = [
            {"success": False, "message": "expired"},
            {"success": True, "message": "ok"},
        ]

        with patch.object(skills_module.skills, "get_user", return_value=self.user), patch(
            "skills.ZeppAPI",
            _FakeAPI,
        ), patch(
            "skills._login_with_proxy",
            return_value={
                "success": True,
                "userid": "fresh-user",
                "login_token": "fresh-login",
                "app_token": "fresh-app",
            },
        ) as login_mock, patch("skills.get_db_session", self.fake_db_session), patch(
            "skills.USE_PROXY_MODE",
            True,
        ), patch(
            "skills.USE_PROXY",
            True,
        ):
            result = skills_module.skills.brush_step("user-1", 8888)

        self.assertTrue(result["success"])
        self.assertEqual(1, login_mock.call_count)
        self.assertEqual(2, len(_FakeAPI.update_calls))
        self.assertEqual("cached-login", _FakeAPI.update_calls[0]["login_token"])
        self.assertEqual("fresh-login", _FakeAPI.update_calls[1]["login_token"])


if __name__ == "__main__":
    unittest.main()
