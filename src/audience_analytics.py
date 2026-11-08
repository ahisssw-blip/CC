"""Privacy-safe audience analytics based only on observable Telegram data."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations
from typing import Any, Dict, Iterable, List, Set


WEIGHTS = {"comments": 5, "replies": 4, "polls": 3, "known_reactions": 2, "shares": 1, "discussion_presence": 1}


def activity_score(member: Dict[str, Any]) -> int:
    return sum(int(member.get(key, 0) or 0) * weight for key, weight in WEIGHTS.items())


def segment_member(member: Dict[str, Any], *, active_days: int = 0) -> str:
    channels = int(member.get("channels_count", 1) or 1)
    score = activity_score(member)
    if score == 0:
        return "متابع صامت"
    if channels > 1:
        return "متابع متعدد القنوات"
    if active_days <= 30 and score >= 10:
        return "عضو جديد واعد"
    if score >= 25:
        return "متفاعل نشط"
    if member.get("specialty"):
        return "متفاعل متخصص"
    return "عضو نشط قابل للرصد"


def enrich_members(members: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result = []
    for member in members:
        row = dict(member)
        row["activity_score"] = activity_score(row)
        row["segment"] = segment_member(row, active_days=int(row.get("active_days", 0) or 0))
        row["views_attributed"] = False
        row["privacy_note"] = "المشاهدات مجهولة ولا تُنسب إلى هذا العضو"
        result.append(row)
    return sorted(result, key=lambda item: item["activity_score"], reverse=True)


def audience_overlap(memberships: Dict[str, Iterable[str]]) -> Dict[str, Any]:
    sets = {str(channel): set(map(str, users)) for channel, users in memberships.items()}
    pairwise = []
    for (left_name, left), (right_name, right) in combinations(sets.items(), 2):
        pairwise.append({"channels": [left_name, right_name], "shared": len(left & right)})
    all_shared = len(set.intersection(*sets.values())) if sets else 0
    return {"channels": {name: len(users) for name, users in sets.items()}, "pairwise": pairwise, "all_channels": all_shared}


def snapshot_delta(previous: Dict[str, int], current: Dict[str, int]) -> Dict[str, Any]:
    channels = set(previous) | set(current)
    return {channel: {"before": int(previous.get(channel, 0)), "after": int(current.get(channel, 0)), "delta": int(current.get(channel, 0)) - int(previous.get(channel, 0))} for channel in sorted(channels)}


def campaign_signals(post_metrics: Iterable[Dict[str, Any]], snapshots: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Correlate available timestamps; never claim causal certainty."""
    posts = list(post_metrics)
    result = []
    for snapshot in snapshots:
        before = snapshot.get("subscribers_before")
        after = snapshot.get("subscribers_after")
        if before is None or after is None:
            continue
        change = int(after) - int(before)
        candidates = [post for post in posts if post.get("channel_id") == snapshot.get("channel_id")]
        result.append({"channel_id": snapshot.get("channel_id"), "period": snapshot.get("period"), "subscriber_delta": change,
                       "candidate_posts": [post.get("message_id") for post in candidates],
                       "interpretation": "ارتباط زمني محتمل وليس إثباتًا سببيًا"})
    return result
