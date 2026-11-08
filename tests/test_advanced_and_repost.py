import pytest

from src.advanced_filters import filter_posts
from src.repost_queue import RepostItem, build_repost_plan


def test_advanced_filters():
    posts = [
        {"channel_id": "a", "message_id": 1, "date": "2026-01-01", "raw_text": "خبر #أخبار https://example.com", "views": 10, "has_media": False},
        {"channel_id": "a", "message_id": 2, "date": "2026-02-01", "raw_text": "نص", "views": 100, "has_media": True},
    ]
    result = filter_posts(posts, {"has_url": True, "has_hashtag": True, "max_views": 50})
    assert [item["message_id"] for item in result] == [1]


def test_repost_plan_is_safe_and_reviewable():
    plan = build_repost_plan([RepostItem("a", 1, "b", "copy", "2026-12-01T10:00:00+00:00")])
    assert plan["status"] == "pending_review"
    assert plan["requires_confirmation"] is True
    with pytest.raises(ValueError):
        RepostItem("a", 1, "a").validate()
    with pytest.raises(ValueError):
        RepostItem("a", 1, "b", "move", "2026-12-01T10:00:00+00:00").validate()
