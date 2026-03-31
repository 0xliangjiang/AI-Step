import unittest
from unittest.mock import patch
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

import skills


class BindBandRetryTests(unittest.TestCase):
    def test_bind_device_retry_uses_direct_connection(self):
        calls = []

        def fake_bindband(email, password, step, verbose, use_proxy):
            calls.append(
                {
                    "email": email,
                    "password": password,
                    "step": step,
                    "verbose": verbose,
                    "use_proxy": use_proxy,
                }
            )
            if len(calls) < 3:
                return {"success": False, "message": "连接超时"}
            return {"success": True, "message": "ok"}

        with patch("skills.bindband", side_effect=fake_bindband), patch(
            "skills.time.sleep"
        ):
            result = skills._bind_device_with_retry(
                "user@example.com",
                "secret",
                verbose=False,
            )

        self.assertTrue(result["success"])
        self.assertEqual(3, len(calls))
        self.assertTrue(all(call["step"] == 1 for call in calls))
        self.assertTrue(all(call["use_proxy"] is False for call in calls))

    def test_login_with_proxy_forces_proxy_enabled(self):
        api_init_calls = []

        class FakeAPI:
            def __init__(self, user, password, verbose, use_tls=False, use_proxy=False, **kwargs):
                api_init_calls.append(
                    {
                        "user": user,
                        "password": password,
                        "verbose": verbose,
                        "use_tls": use_tls,
                        "use_proxy": use_proxy,
                    }
                )
                self.userid = "user-1"
                self.login_token = "login-token"
                self.app_token = "app-token"

            def login(self):
                return {"success": True, "userid": self.userid, "message": "ok"}

        with patch("skills.ZeppAPI", FakeAPI):
            result = skills._login_with_proxy(
                "user@example.com",
                "secret",
                verbose=False,
            )

        self.assertTrue(result["success"])
        self.assertEqual(1, len(api_init_calls))
        self.assertTrue(api_init_calls[0]["use_proxy"])
        self.assertEqual("login-token", result["login_token"])
        self.assertEqual("app-token", result["app_token"])


if __name__ == "__main__":
    unittest.main()
