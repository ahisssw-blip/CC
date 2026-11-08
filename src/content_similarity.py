"""Lightweight, explainable duplicate and near-duplicate detection."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Set

TOKEN_RE = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)


@dataclass(frozen=True)
class SimilarityMatch:
    left_channel: str
    left_message_id: int
    right_channel: str
    right_message_id: int
    score: float
    reason: str

    def as_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def tokens(text: str) -> Set[str]:
    return {token.casefold() for token in TOKEN_RE.findall(text or "") if len(token) > 1}


def jaccard(left: Set[str], right: Set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def find_similar_posts(posts: Iterable[Dict[str, Any]], threshold: float = 0.82) -> List[SimilarityMatch]:
    prepared = []
    for post in posts:
        text = post.get("raw_text") or post.get("text") or ""
        prepared.append((post, tokens(text)))
    matches: List[SimilarityMatch] = []
    for index, (left, left_tokens) in enumerate(prepared):
        for right, right_tokens in prepared[index + 1:]:
            if str(left.get("channel_id")) == str(right.get("channel_id")) and left.get("message_id", left.get("id")) == right.get("message_id", right.get("id")):
                continue
            score = jaccard(left_tokens, right_tokens)
            if score >= threshold:
                matches.append(SimilarityMatch(
                    str(left.get("channel_id")), int(left.get("message_id", left.get("id", 0))),
                    str(right.get("channel_id")), int(right.get("message_id", right.get("id", 0))),
                    round(score, 4), "تشابه نصي مرتفع؛ راجع العنوان والروابط والوسائط",
                ))
    return sorted(matches, key=lambda item: item.score, reverse=True)
