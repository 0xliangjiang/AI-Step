import re
from typing import List, Optional

from models import Card, get_db_session


CARD_CANDIDATE_PATTERN = re.compile(r"[A-Z0-9]{4,32}")


def extract_card_candidates(message: str) -> List[str]:
    """从消息中提取可能的卡密候选值。"""
    normalized = (message or "").upper()
    candidates: List[str] = []
    seen = set()

    for token in CARD_CANDIDATE_PATTERN.findall(normalized):
        if len(token) < 8:
            continue
        if token not in seen:
            seen.add(token)
            candidates.append(token)

    compact = re.sub(r"[^A-Z0-9]", "", normalized)
    if 8 <= len(compact) <= 32 and compact not in seen:
        candidates.append(compact)

    return candidates


def find_matching_card_key(message: str) -> Optional[str]:
    """查找消息中包含的有效卡密。"""
    candidates = extract_card_candidates(message)
    if not candidates:
        return None

    with get_db_session() as db:
        for candidate in candidates:
            card = db.query(Card).filter(Card.card_key == candidate).first()
            if card:
                return card.card_key

    return None
