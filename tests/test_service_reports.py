from src.studio_service import StudioService
from src.studio_store import StudioStore


def test_quality_similarity_and_query_reports(tmp_path):
    store = StudioStore(tmp_path / "studio.sqlite3")
    store.upsert_channel({"id": "a", "title": "أخبار"})
    store.upsert_channel({"id": "b", "title": "تقنية"})
    store.upsert_message("a", {"id": 1, "date": "2026-01-01", "raw_text": "الذكاء الاصطناعي يغير مستقبل العمل"})
    store.upsert_message("b", {"id": 2, "date": "2026-01-02", "raw_text": "الذكاء الاصطناعي يغير مستقبل العمل بسرعة"})
    service = StudioService(store)
    assert service.quality_report()["total"] >= 0
    assert service.similar_report(threshold=0.6)["total"] == 1
    assert service.explain_query('أرني منشورات قناة التقنية التي تحتوي على "الذكاء الاصطناعي"')["channel_name"] == "التقنية"
