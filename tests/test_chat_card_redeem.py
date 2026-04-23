import unittest
from pathlib import Path
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

import chat_card


class _FakeCard:
    def __init__(self, card_key):
        self.card_key = card_key


class _FakeQuery:
    def __init__(self, existing_cards):
        self.existing_cards = existing_cards
        self.current_candidate = None

    def filter(self, expression):
        self.current_candidate = expression.right.value
        return self

    def first(self):
        if self.current_candidate in self.existing_cards:
            return _FakeCard(self.current_candidate)
        return None


class _FakeSession:
    def __init__(self, existing_cards):
        self.existing_cards = existing_cards

    def query(self, _model):
        return _FakeQuery(self.existing_cards)


class _FakeSessionContext:
    def __init__(self, existing_cards):
        self.session = _FakeSession(existing_cards)

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        return False


class ChatCardRedeemTests(unittest.TestCase):
    def test_extract_card_candidates_supports_spaced_card_text(self):
        candidates = chat_card.extract_card_candidates("充值卡密 abcd efgh 2345 6789")

        self.assertIn("ABCDEFGH23456789", candidates)

    def test_find_matching_card_key_returns_existing_candidate(self):
        with patch("chat_card.get_db_session", return_value=_FakeSessionContext({"ABCD2345EFGH6789"})):
            matched = chat_card.find_matching_card_key("这是我的卡密 abcd 2345 efgh 6789")

        self.assertEqual("ABCD2345EFGH6789", matched)

    def test_chat_route_short_circuits_to_direct_card_redeem(self):
        main_py = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")

        self.assertIn('direct_card_key = find_matching_card_key(message)', main_py)
        self.assertIn('result = skills.use_card(user_key, direct_card_key)', main_py)
        self.assertIn('save_chat_message(user_key, "assistant", reply)', main_py)
        self.assertIn('function_result=result', main_py)


if __name__ == "__main__":
    unittest.main()
