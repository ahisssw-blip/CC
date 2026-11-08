import pytest

from src.message_model import EditablePost, InlineButton, MediaItem, build_edit_plan


def test_buttons_and_albums_are_validated():
    button = InlineButton("المصدر", "https://example.com")
    original = EditablePost("1", 10, "قبل", buttons=[button])
    updated = EditablePost("1", 10, "بعد", buttons=[button])
    plan = build_edit_plan(original, updated)
    assert plan["changed"]["text"] is True
    assert plan["requires_review"] is True
    with pytest.raises(ValueError):
        InlineButton("رابط", "not-a-url").validate()
    with pytest.raises(ValueError):
        EditablePost("1", 10, media=[MediaItem("photo", "a"), MediaItem("photo", "b")]).validate()


def test_media_change_is_marked_for_reupload():
    original = EditablePost("1", 10, "نص", media=[MediaItem("photo", "old.jpg")])
    updated = EditablePost("1", 10, "نص", media=[MediaItem("photo", "new.jpg")])
    plan = build_edit_plan(original, updated)
    assert plan["requires_media_reupload"] is True
    assert plan["changed"]["text"] is False
