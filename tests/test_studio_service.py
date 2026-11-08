from src.studio_service import StudioService
from src.studio_store import StudioStore


def make_service(tmp_path):
    store = StudioStore(tmp_path / "studio.sqlite3")
    store.upsert_channel({"id": "1", "title": "أخبار"})
    store.upsert_message("1", {"id": 10, "date": "2026-01-01 10:00:00", "raw_text": "رابط قديم هنا"})
    store.upsert_message("1", {"id": 11, "date": "2026-01-02 10:00:00", "raw_text": "لا تغيير"})
    return StudioService(store)


def test_preview_and_create_plan(tmp_path):
    service = make_service(tmp_path)
    preview = service.preview_replace("قديم", "جديد")
    assert preview["total"] == 1
    assert preview["items"][0]["updated"] == "رابط جديد هنا"
    operation_id = service.create_replace_plan(preview, "قديم", "جديد")
    assert operation_id == 1
    assert service.list_operations()[0]["status"] == "planned"


def test_apply_local_plan_only_changes_planned_items(tmp_path):
    service = make_service(tmp_path)
    preview = service.preview_replace("قديم", "جديد")
    operation_id = service.create_replace_plan(preview, "قديم", "جديد")
    result = service.apply_local_plan(operation_id)
    assert result == {"applied": 1, "total": 1}
    assert service.search_posts(text="جديد")[0]["message_id"] == 10
