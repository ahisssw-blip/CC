"""Composable, explainable post filters for the Arabic Studio."""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Set

from src.content_quality import extract_urls, HASHTAG_RE


def filter_posts(posts: Iterable[Dict[str, Any]], spec: Optional[Dict[str, Any]] = None, issue_map: Optional[Dict[str, Set[int]]] = None) -> List[Dict[str, Any]]:
    spec = dict(spec or {})
    issue_map = issue_map or {}
    result = []
    for post in posts:
        text = post.get("raw_text") or post.get("text") or ""
        if spec.get("channel_id") and str(post.get("channel_id")) != str(spec["channel_id"]):
            continue
        if spec.get("text") and str(spec["text"]).casefold() not in text.casefold():
            continue
        if spec.get("date_from") and (post.get("date") or "") < spec["date_from"]:
            continue
        if spec.get("date_to") and (post.get("date") or "") > spec["date_to"]:
            continue
        if spec.get("media_type") and post.get("media_type") != spec["media_type"]:
            continue
        if spec.get("has_media") is not None and bool(post.get("has_media")) != bool(spec["has_media"]):
            continue
        if spec.get("has_url") is not None and bool(extract_urls(text)) != bool(spec["has_url"]):
            continue
        if spec.get("has_hashtag") is not None and bool(HASHTAG_RE.search(text)) != bool(spec["has_hashtag"]):
            continue
        views = int(post.get("views") or 0)
        if spec.get("min_views") is not None and views < int(spec["min_views"]):
            continue
        if spec.get("max_views") is not None and views > int(spec["max_views"]):
            continue
        if spec.get("modified") is True and not post.get("edit_date"):
            continue
        if spec.get("modified") is False and post.get("edit_date"):
            continue
        issue_codes = spec.get("issue_codes") or []
        if issue_codes and not any(int(post.get("message_id", post.get("id", 0))) in issue_map.get(code, set()) for code in issue_codes):
            continue
        if spec.get("low_performance_below") is not None and views >= int(spec["low_performance_below"]):
            continue
        result.append(post)
    return result
