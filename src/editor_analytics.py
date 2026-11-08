"""Explainable editorial analytics from locally indexed message metrics."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, Iterable


def editorial_report(posts: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(posts)
    if not rows:
        return {"total": 0, "summary": {}, "by_channel": [], "high_views_low_reactions": [], "low_views_high_reactions": []}
    views = [int(row.get("views", 0) or 0) for row in rows]
    reactions = [int(row.get("reaction_count", row.get("reactions_count", 0)) or 0) for row in rows]
    median_views = sorted(views)[len(views) // 2]
    median_reactions = sorted(reactions)[len(reactions) // 2]
    hours = Counter()
    media = Counter()
    channels = defaultdict(lambda: {"posts": 0, "views": 0, "reactions": 0})
    for row, reaction_count in zip(rows, reactions):
        date = str(row.get("date") or "")
        hour = date[11:13] if len(date) >= 13 and date[10] in " T" else "غير معروف"
        hours[hour] += 1
        media[str(row.get("media_type") or "نص")] += 1
        channel = str(row.get("channel_title") or row.get("channel_id") or "غير معروف")
        channels[channel]["posts"] += 1
        channels[channel]["views"] += int(row.get("views", 0) or 0)
        channels[channel]["reactions"] += reaction_count
    high_low = [row for row, reaction_count in zip(rows, reactions) if int(row.get("views", 0) or 0) >= median_views and reaction_count <= median_reactions]
    low_high = [row for row, reaction_count in zip(rows, reactions) if int(row.get("views", 0) or 0) <= median_views and reaction_count >= median_reactions]
    return {
        "total": len(rows),
        "summary": {"median_views": median_views, "median_reactions": median_reactions, "top_hour": hours.most_common(1)[0][0] if hours else None, "top_media_type": media.most_common(1)[0][0] if media else None},
        "hours": [{"hour": key, "posts": value} for key, value in hours.most_common()],
        "media_types": [{"type": key, "posts": value} for key, value in media.most_common()],
        "by_channel": [{"channel": key, **value} for key, value in channels.items()],
        "high_views_low_reactions": [{"message_id": row.get("message_id", row.get("id")), "views": row.get("views", 0), "reactions": reaction_count} for row, reaction_count in zip(high_low, [int(item.get("reaction_count", item.get("reactions_count", 0)) or 0) for item in high_low])],
        "low_views_high_reactions": [{"message_id": row.get("message_id", row.get("id")), "views": row.get("views", 0), "reactions": int(row.get("reaction_count", row.get("reactions_count", 0)) or 0)} for row in low_high],
        "causality_note": "هذه مقارنة وصفية للبيانات المحلية وليست إثباتًا لسببية أو تأثير حملة.",
    }
