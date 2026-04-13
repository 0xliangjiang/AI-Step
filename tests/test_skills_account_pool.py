import unittest
from pathlib import Path
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

import skills as skills_module


class StepSkillsAccountPoolTests(unittest.TestCase):
    def test_register_uses_account_pool_snapshot_without_detached_instance(self):
        account_snapshot = {
            "id": 123,
            "user_key": None,
            "zepp_email": "pool@example.com",
            "zepp_password": "secret",
            "zepp_userid": "zepp-user-1",
            "bind_status": 0,
            "bind_button_triggered": 0,
            "vip_expire_at": None,
            "login_token": None,
            "app_token": None,
            "token_updated_at": None,
        }

        captured = {}

        def fake_assign(user_key, account):
            captured["user_key"] = user_key
            captured["account"] = account
            return {"success": True, "message": "assigned"}

        with patch.object(
            skills_module.skills,
            "_get_available_account",
            return_value=account_snapshot,
        ), patch.object(
            skills_module.skills,
            "_assign_account_to_user",
            side_effect=fake_assign,
        ):
            result = skills_module.skills.register_zepp_account("user-1")

        self.assertTrue(result["success"])
        self.assertEqual("assigned", result["message"])
        self.assertEqual("user-1", captured["user_key"])
        self.assertEqual("pool@example.com", captured["account"]["zepp_email"])
        self.assertEqual(123, captured["account"]["id"])


if __name__ == "__main__":
    unittest.main()
