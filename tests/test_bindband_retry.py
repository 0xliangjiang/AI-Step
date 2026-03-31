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


if __name__ == "__main__":
    unittest.main()
