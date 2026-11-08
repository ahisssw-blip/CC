from src.bulk_editor import preview_bulk


def test_bulk_preview_returns_independent_results():
    posts = [
        {"channel_id": "a", "message_id": 1, "raw_text": "خبر عاجل"},
        {"channel_id": "b", "message_id": 2, "raw_text": "خبر عادي"},
    ]
    results = preview_bulk(posts, "replace", {"search": "عاجل", "replace": "مهم"})
    assert results[0].changed is True
    assert results[1].changed is False
    assert results[0].after == "خبر مهم"


def test_bulk_operations_cover_requested_transforms():
    post = [{"channel_id": "a", "message_id": 1, "raw_text": "خبر!! https://bit.ly/demo 2026-01-02 😀"}]
    assert "#خبر" in preview_bulk(post, "append_hashtag", {"hashtags": ["خبر"]})[0].after
    assert "bit.ly" not in preview_bulk(post, "remove_short_links")[0].after
    assert "!" in preview_bulk(post, "normalize_punctuation")[0].after
    assert "😀" not in preview_bulk(post, "remove_emoji")[0].after
    assert "02/01/2026" in preview_bulk(post, "date_format")[0].after
