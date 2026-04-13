import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import sys

from sqlalchemy.exc import OperationalError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

import skills as skills_module


class _FakeQuery:
    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return _FakeDbUser()


class _FakeDbUser:
    login_token = None
    app_token = None
    token_updated_at = None


class _FakeDb:
    def query(self, *args, **kwargs):
        return _FakeQuery()


class _FakeAPI:
    def __init__(self, *args, **kwargs):
        self.login_token = None
        self.app_token = None
        self.userid = None

    def get_qrcode_ticket(self, userid):
        return {"success": True, "ticket": "ticket-123"}


class StepSkillsBindQrTests(unittest.TestCase):
    def test_get_bindqr_succeeds_even_if_token_cache_update_times_out(self):
        user = {
            "user_key": "user-1",
            "zepp_email": "pool@example.com",
            "zepp_password": "secret",
            "zepp_userid": None,
            "login_token": None,
            "app_token": None,
        }

        @contextmanager
        def fake_db_session():
            yield _FakeDb()
            raise OperationalError(
                "UPDATE users SET login_token=:login_token",
                {},
                Exception("Lock wait timeout exceeded"),
            )

        with patch("skills.ZeppAPI", _FakeAPI), patch(
            "skills._login_with_proxy",
            return_value={
                "success": True,
                "userid": "zepp-user-1",
                "login_token": "login-token",
                "app_token": "app-token",
            },
        ), patch("skills.get_db_session", fake_db_session), patch(
            "skills.generate_qrcode",
            return_value="qr-base64",
        ), patch("skills.QRCODE_AVAILABLE", True):
            result = skills_module.skills._get_bindqr_for_user_dict(user)

        self.assertTrue(result["success"])
        self.assertEqual("qr-base64", result["qrcode_image"])
        self.assertIn("请使用微信扫描下方二维码绑定微信", result["message"])


if __name__ == "__main__":
    unittest.main()
