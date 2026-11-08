import asyncio
import pytest

from src.change_manager import ChangeManager
from src.studio_store import StudioStore


def make_manager(tmp_path):
    store = StudioStore(tmp_path / "studio.sqlite3")
    store.upsert_channel({"id": "1", "title": "أخبار"})
    store.upsert_message("1", {"id": 10, "date": "2026-01-01", "raw_text": "قبل"})
    store.upsert_message("1", {"id": 11, "date": "2026-01-02", "raw_text": "قبل 2"})
    return store, ChangeManager(store)


def test_batch_review_execute_and_rollback(tmp_path):
    store, manager = make_manager(tmp_path)
    batch_id = manager.create_batch("توحيد التوقيع", "اختبار", [
        {"channel_id": "1", "message_id": 10, "before": "قبل", "after": "بعد"},
        {"channel_id": "1", "message_id": 11, "before": "قبل 2", "after": "بعد 2"},
    ])
    assert manager.get_batch(batch_id)["status"] == "pending_review"
    with pytest.raises(ValueError):
        manager.execute_local(batch_id)
    manager.approve_batch(batch_id)
    result = manager.execute_local(batch_id, batch_size=1)
    assert result["applied"] == 1 and result["remaining"] == 1
    result = manager.execute_local(batch_id, batch_size=10)
    assert result["status"] == "completed"
    assert manager.rollback(batch_id) == {"restored": 2}
    assert store.search_messages(text="قبل")[0]["message_id"] == 11


def test_cancel_one_item(tmp_path):
    _, manager = make_manager(tmp_path)
    batch_id = manager.create_batch("اختبار", "", [{"channel_id": "1", "message_id": 10, "before": "قبل", "after": "بعد"}])
    item_id = manager.get_batch(batch_id)["items"][0]["id"]
    manager.cancel_item(item_id)
    assert manager.get_batch(batch_id)["items"][0]["status"] == "cancelled"


def test_run_due_batches(tmp_path):
    _, manager = make_manager(tmp_path)
    batch_id = manager.create_batch(
        "مجدولة", "", [{"channel_id": "1", "message_id": 10, "before": "قبل", "after": "بعد"}],
        scheduled_at="2026-01-02T00:00:00+00:00",
    )
    manager.approve_batch(batch_id)
    result = manager.run_due_batches(now="2026-01-03T00:00:00+00:00")
    assert result[0]["status"] == "completed"


def test_execute_telegram_updates_batch_state(tmp_path):
    store, manager = make_manager(tmp_path)
    batch_id = manager.create_batch("حي", "", [{"channel_id": "1", "message_id": 10, "before": "قبل", "after": "بعد"}])
    manager.approve_batch(batch_id)

    class Permission:
        can_edit_messages = True

    class Gateway:
        async def permissions(self, channel):
            return Permission()
        async def edit_message(self, channel, message_id, text, entities):
            assert (channel, message_id, text) == ("1", 10, "بعد")

    result = asyncio.run(manager.execute_telegram(batch_id, Gateway(), lambda channel: channel))
    assert result["status"] == "completed"
    assert manager.get_batch(batch_id)["items"][0]["status"] == "applied"


def test_local_execute_rejects_stale_before_text(tmp_path):
    store, manager = make_manager(tmp_path)
    batch_id = manager.create_batch("تغيير قديم", "", [
        {"channel_id": "1", "message_id": 10, "before": "قبل", "after": "بعد"}
    ])
    manager.approve_batch(batch_id)
    store.upsert_message("1", {"id": 10, "date": "2026-01-01", "raw_text": "تحديث أحدث"})

    result = manager.execute_local(batch_id)
    assert result["failed"] == 1
    assert manager.get_batch(batch_id)["items"][0]["status"] == "failed"
    message = next(row for row in store.search_messages(channel_id="1") if row["message_id"] == 10)
    assert message["raw_text"] == "تحديث أحدث"


def test_rollback_preserves_message_changed_after_batch(tmp_path):
    store, manager = make_manager(tmp_path)
    batch_id = manager.create_batch("تعديل", "", [
        {"channel_id": "1", "message_id": 10, "before": "قبل", "after": "بعد"}
    ])
    manager.approve_batch(batch_id)
    manager.execute_local(batch_id)
    store.upsert_message("1", {"id": 10, "date": "2026-01-01", "raw_text": "تحديث أحدث"})

    assert manager.rollback(batch_id) == {"restored": 0, "conflicts": 1}
    message = next(row for row in store.search_messages(channel_id="1") if row["message_id"] == 10)
    assert message["raw_text"] == "تحديث أحدث"
