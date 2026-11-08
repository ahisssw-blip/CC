from src.editor_engine import (
    DEFAULT_TEMPLATES, LayerConfig, Template, apply_layers, apply_template,
    archive_post, clean_post, prepare_republish, preview_change,
)


def test_layers_and_hashtags_are_deterministic():
    result = apply_layers("تفاصيل الخبر", LayerConfig(title_prefix="عنوان", hashtags=["خبر", "#خبر"], signature="توقيع"))
    assert result == "عنوان\n\nتفاصيل الخبر\n\n#خبر\n\nتوقيع"


def test_operations_and_preview():
    cleaned = clean_post("  نص  \n\n\n #خبر #خبر ", signature="قناة الأخبار")
    assert "#خبر" in cleaned
    assert cleaned.count("#خبر") == 1
    archived = archive_post("محتوى", date_text="2026-01-01", source_url="https://example.com")
    assert "#أرشيف" in archived and "المنشور الأصلي" in archived
    prepared = prepare_republish("خبر عاجل مهم", introduction="مقدمة", source_url="https://example.com")
    assert "عاجل" not in prepared and "المصدر" in prepared
    assert preview_change("قبل", "بعد")["changed"] is True


def test_templates_render_without_leaking_placeholders():
    template = Template("اختبار", "العنوان: {{العنوان}}\n{{النص}}")
    assert apply_template(template, "المحتوى", {"العنوان": "خبر"}) == "العنوان: خبر\nالمحتوى"
    assert len(DEFAULT_TEMPLATES) == 3
