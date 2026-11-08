from src.studio_service import StudioService
from src.studio_store import StudioStore


def test_editor_preview_operations(tmp_path):
    service = StudioService(StudioStore(tmp_path / "studio.sqlite3"))
    result = service.editor_preview("layers", "تفاصيل", {"title_prefix": "عنوان", "signature": "توقيع"})
    assert result["changed"] is True
    assert "عنوان" in result["updated"]
    clean = service.editor_preview("clean", "  نص  ", {"signature": "قناة"})
    assert clean["updated"].endswith("قناة")
    template = service.editor_preview("template", "محتوى", {"body": "عنوان: {{النص}}"})
    assert template["updated"] == "عنوان: محتوى"
    assert len(service.list_templates()) == 3
