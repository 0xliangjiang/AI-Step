import unittest
from pathlib import Path
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import step_brush


class _FakeResponse:
    status_code = 200
    text = '{"code":1,"message":"ok"}'

    @staticmethod
    def json():
        return {"code": 1, "message": "ok"}


class StepBrushTimezoneTests(unittest.TestCase):
    def test_core_network_calls_use_two_minute_timeout_budget(self):
        source = (ROOT / "step_brush.py").read_text(encoding="utf-8")

        self.assertIn("NETWORK_TIMEOUT_SECONDS = 120", source)
        self.assertIn('timeout=NETWORK_TIMEOUT_SECONDS', source)

    def test_update_step_uses_china_date_instead_of_process_local_date(self):
        api = step_brush.ZeppAPI(verbose=False, use_tls=False)
        api.userid = "user-1"
        api.login_token = "login-token"
        api.app_token = "app-token"

        with patch("step_brush.time.strftime", return_value="2026-04-14"), patch(
            "step_brush.get_china_today_str",
            return_value="2026-04-15",
            create=True,
        ), patch.object(
            api,
            "_build_data_json",
            return_value="encoded",
        ) as build_mock, patch.object(
            api,
            "_request",
            return_value=_FakeResponse(),
        ):
            result = api.update_step(12345)

        self.assertTrue(result["success"])
        build_mock.assert_called_once_with(12345, "2026-04-15")


if __name__ == "__main__":
    unittest.main()
