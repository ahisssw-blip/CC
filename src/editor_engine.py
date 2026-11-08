"""Pure local editing engine for previews, templates and reusable operations."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class Template:
    name: str
    body: str
    description: str = ""

    def render(self, values: Dict[str, Any]) -> str:
        rendered = self.body
        for key, value in values.items():
            rendered = rendered.replace("{{" + key + "}}", str(value or ""))
        return rendered


@dataclass
class LayerConfig:
    title_prefix: str = ""
    introduction: str = ""
    conclusion: str = ""
    signature: str = ""
    hashtags: List[str] = field(default_factory=list)
    source_url: str = ""
    site_url: str = ""
    warning: str = ""
    emoji_prefix: str = ""


def normalize_hashtags(tags: Iterable[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for tag in tags:
        clean = tag.strip()
        if not clean:
            continue
        if not clean.startswith("#"):
            clean = "#" + clean
        key = clean.casefold()
        if key not in seen:
            result.append(clean)
            seen.add(key)
    return result


def apply_layers(text: str, layers: LayerConfig) -> str:
    parts: List[str] = []
    if layers.warning.strip():
        parts.append(layers.warning.strip())
    if layers.emoji_prefix.strip() or layers.title_prefix.strip():
        parts.append((layers.emoji_prefix + layers.title_prefix).strip())
    if layers.introduction.strip():
        parts.append(layers.introduction.strip())
    if text.strip():
        parts.append(text.strip())
    if layers.conclusion.strip():
        parts.append(layers.conclusion.strip())
    tags = normalize_hashtags(layers.hashtags)
    if tags:
        parts.append(" ".join(tags))
    if layers.source_url.strip():
        parts.append("المصدر: " + layers.source_url.strip())
    if layers.site_url.strip():
        parts.append("التفاصيل: " + layers.site_url.strip())
    if layers.signature.strip():
        parts.append(layers.signature.strip())
    return "\n\n".join(parts)


def apply_template(template: Template, text: str, values: Optional[Dict[str, Any]] = None) -> str:
    values = dict(values or {})
    values.setdefault("المحتوى", text)
    values.setdefault("النص", text)
    return template.render(values)


def clean_post(text: str, *, signature: str = "") -> str:
    text = "\n".join(line.strip() for line in (text or "").splitlines())
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    tags = normalize_hashtags(re.findall(r"#[\w\u0600-\u06ff]+", text))
    text = re.sub(r"#[\w\u0600-\u06ff]+", "", text)
    if tags:
        text = (text.rstrip() + "\n\n" + " ".join(tags)).strip()
    if signature.strip():
        text = (text.rstrip() + "\n\n" + signature.strip()).strip()
    return text


def archive_post(text: str, *, archive_tag: str = "#أرشيف", date_text: str = "", source_url: str = "") -> str:
    additions = [archive_tag]
    if date_text:
        additions.append("التاريخ: " + date_text)
    if source_url:
        additions.append("المنشور الأصلي: " + source_url)
    return (text.rstrip() + "\n\n" + "\n".join(additions)).strip()


def prepare_republish(text: str, *, remove_phrase: str = "عاجل", introduction: str = "", source_url: str = "") -> str:
    result = text.replace(remove_phrase, "") if remove_phrase else text
    layers = LayerConfig(introduction=introduction, source_url=source_url)
    return apply_layers(result, layers)


def preview_change(original: str, updated: str) -> Dict[str, Any]:
    return {
        "original": original,
        "updated": updated,
        "changed": original != updated,
        "original_length": len(original or ""),
        "updated_length": len(updated or ""),
    }


DEFAULT_TEMPLATES = [
    Template("خبر", "{{العنوان}}\n\n{{التفاصيل}}\n\nالمصدر:\n{{الرابط}}", "قالب خبر مع مصدر"),
    Template("إعلان", "إعلان مهم\n\n{{النص}}\n\nللتفاصيل:\n{{الرابط}}", "قالب إعلان جاهز"),
    Template("مراجعة", "{{اسم المنتج}}\n\nالتقييم: {{التقييم}}\n\nالمميزات:\n{{المميزات}}\n\nالعيوب:\n{{العيوب}}\n\nالتفاصيل:\n{{الرابط}}", "قالب مراجعة منتج"),
]
