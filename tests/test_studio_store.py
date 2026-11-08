import json

from src.studio_store import StudioStore, import_json_file


def legacy_database():
    return {
        "channels": [{"id": 1, "title": "الأخبار", "type": "channel"}],
        "messages": {
            "1": {
                "10": {"id": 10, "date": "2026-01-02 10:00:00", "raw_text": "خبر مهم", "text": "خبر مهم", "has_media": False},
                "11": {"id": 11, "date": "2026-01-03 10:00:00", "raw_text": "صورة جديدة", "text": "صورة جديدة", "has_media": True, "media_type": "Photo"},
            }
        },
        "users": {"1": {"7": {"id": 7, "username": "reader", "first_name": "Reader"}}},
    }


def test_import_and_search(tmp_path):
    source = tmp_path / "database.json"
    sqlite_path = tmp_path / "studio.sqlite3"
    source.write_text(json.dumps(legacy_database()), encoding="utf-8")

    result = import_json_file(source, sqlite_path)
    assert result == {"channels": 1, "messages": 2, "users": 1}

    store = StudioStore(sqlite_path)
    assert store.summary() == {"channels": 1, "messages": 2, "users": 1}
    rows = store.search_messages(text="صورة", has_media=True)
    assert len(rows) == 1
    assert rows[0]["message_id"] == 11
    assert rows[0]["channel_title"] == "الأخبار"


def test_search_filters_by_date_and_channel(tmp_path):
    store = StudioStore(tmp_path / "studio.sqlite3")
    store.upsert_channel({"id": "1", "title": "A"})
    store.upsert_channel({"id": "2", "title": "B"})
    store.upsert_message("1", {"id": 1, "date": "2026-01-01 00:00:00", "raw_text": "same"})
    store.upsert_message("2", {"id": 2, "date": "2026-02-01 00:00:00", "raw_text": "same"})

    rows = store.search_messages(text="same", channel_id="2", date_from="2026-02-01")
    assert [row["message_id"] for row in rows] == [2]


def test_schema_version_and_backup(tmp_path):
    store = StudioStore(tmp_path / "studio.sqlite3")
    assert store.schema_version() == 1
    backup = store.backup(tmp_path / "backup" / "studio.sqlite3")
    assert backup.exists()
    assert backup.stat().st_size == store.path.stat().st_size
