from datetime import datetime, timezone

from src.telegram_gateway import TelegramGateway


class FakeMessage:
    id = 7
    date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    edit_date = None
    text = "نص"
    raw_text = "نص"
    text_html = "نص"
    entities = []
    media = None
    reactions = None
    views = 12
    forwards = 2
    pinned = True
    reply_to = None


def test_gateway_requires_credentials():
    try:
        TelegramGateway(0, "", "/tmp/session")
    except ValueError as exc:
        assert "API_ID" in str(exc)
    else:
        raise AssertionError("expected credential validation")


def test_message_serialization_is_ui_safe():
    result = TelegramGateway.serialize_message(FakeMessage())
    assert result["id"] == 7
    assert result["date"].startswith("2026-01-01")
    assert result["views"] == 12
    assert result["has_media"] is False
