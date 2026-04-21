import unittest
from pathlib import Path
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

import ai_client as ai_client_module


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class AIClientResponseGuardTests(unittest.TestCase):
    def setUp(self):
        self.client = ai_client_module.AIClient(provider="minimax")

    def test_minimax_uses_openai_compatible_endpoint_and_payload(self):
        with patch("ai_client.requests.post", return_value=FakeResponse({
            "choices": [
                {
                    "message": {
                        "content": "ok"
                    }
                }
            ]
        })) as mock_post:
            result = self.client._chat_minimax(
                "system prompt",
                [{"role": "user", "content": "注册"}],
                "user-1",
                stealth=False,
            )

        self.assertTrue(result["success"])
        self.assertEqual("ok", result["reply"])

        self.assertEqual(1, mock_post.call_count)
        call_args = mock_post.call_args
        self.assertEqual(
            "https://api.minimaxi.com/v1/chat/completions",
            call_args.args[0],
        )
        payload = call_args.kwargs["json"]
        self.assertEqual("MiniMax-M2.5", payload["model"])
        self.assertFalse(payload["reasoning_split"])
        self.assertEqual("auto", payload["tool_choice"])
        self.assertIn("tools", payload)
        self.assertEqual("system", payload["messages"][0]["role"])
        self.assertEqual("system prompt", payload["messages"][0]["content"])
        self.assertEqual("user", payload["messages"][1]["role"])
        self.assertEqual("注册", payload["messages"][1]["content"])
        self.assertEqual(120, call_args.kwargs["timeout"])

    def test_minimax_handles_none_choices_without_crashing(self):
        with patch("ai_client.requests.post", return_value=FakeResponse({
            "choices": None,
            "base_resp": {
                "status_code": 1000,
                "status_msg": "upstream error"
            }
        })):
            result = self.client._chat_minimax(
                "system prompt",
                [{"role": "user", "content": "注册"}],
                "user-1",
                stealth=False,
            )

        self.assertFalse(result["success"])
        self.assertEqual(ai_client_module.ERROR_MESSAGE, result["reply"])
        self.assertIn("upstream error", result["function_result"]["message"])

    def test_minimax_handles_empty_choices_without_crashing(self):
        with patch("ai_client.requests.post", return_value=FakeResponse({
            "choices": [],
            "base_resp": {
                "status_code": 1001,
                "status_msg": "no choices returned"
            }
        })):
            result = self.client._chat_minimax(
                "system prompt",
                [{"role": "user", "content": "注册"}],
                "user-1",
                stealth=False,
            )

        self.assertFalse(result["success"])
        self.assertEqual(ai_client_module.ERROR_MESSAGE, result["reply"])
        self.assertIn("no choices returned", result["function_result"]["message"])

    def test_minimax_strips_think_blocks_from_reply(self):
        with patch("ai_client.requests.post", return_value=FakeResponse({
            "choices": [
                {
                    "message": {
                        "content": "<think>internal reasoning</think>这是给用户的回复"
                    }
                }
            ]
        })):
            result = self.client._chat_minimax(
                "system prompt",
                [{"role": "user", "content": "注册"}],
                "user-1",
                stealth=False,
            )

        self.assertTrue(result["success"])
        self.assertEqual("这是给用户的回复", result["reply"])

    def test_minimax_strips_malformed_think_tags_from_reply(self):
        with patch("ai_client.requests.post", return_value=FakeResponse({
            "choices": [
                {
                    "message": {
                        "content": "<think>这是隐藏内容\n这是给用户的回复</think>"
                    }
                }
            ]
        })):
            result = self.client._chat_minimax(
                "system prompt",
                [{"role": "user", "content": "注册"}],
                "user-1",
                stealth=False,
            )

        self.assertTrue(result["success"])
        self.assertEqual("", result["reply"])

        cleaned = self.client._sanitize_reply_text("<think>\n这是给用户的回复")
        self.assertEqual("这是给用户的回复", cleaned)


if __name__ == "__main__":
    unittest.main()
