"""Serializable Telegram post model used by the editor and safe previews."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse


@dataclass(frozen=True)
class InlineButton:
    label: str
    url: str

    def validate(self) -> None:
        if not self.label.strip():
            raise ValueError("نص الزر مطلوب")
        parsed = urlparse(self.url.strip())
        if parsed.scheme not in {"http", "https", "tg"} or not parsed.netloc and parsed.scheme != "tg":
            raise ValueError("رابط الزر يجب أن يكون رابطًا صالحًا")

    def as_dict(self) -> Dict[str, str]:
        self.validate()
        return {"label": self.label.strip(), "url": self.url.strip()}


@dataclass(frozen=True)
class MediaItem:
    kind: str
    file_path: str
    caption: str = ""
    order: int = 0

    def validate(self) -> None:
        if self.kind not in {"photo", "video", "document", "audio"}:
            raise ValueError("نوع الوسائط غير مدعوم")
        if not self.file_path.strip():
            raise ValueError("مسار الوسائط مطلوب")

    def as_dict(self) -> Dict[str, Any]:
        self.validate()
        return {"kind": self.kind, "file_path": self.file_path, "caption": self.caption, "order": self.order}


@dataclass
class EditablePost:
    channel_id: str
    message_id: int
    raw_text: str = ""
    entities: List[Dict[str, Any]] = field(default_factory=list)
    buttons: List[InlineButton] = field(default_factory=list)
    media: List[MediaItem] = field(default_factory=list)
    media_group_id: Optional[str] = None

    def validate(self) -> None:
        if not self.channel_id:
            raise ValueError("معرف القناة مطلوب")
        if self.message_id < 1:
            raise ValueError("معرف المنشور غير صالح")
        for button in self.buttons:
            button.validate()
        for media in self.media:
            media.validate()
        if len(self.media) > 1 and not self.media_group_id:
            raise ValueError("الألبوم يحتاج إلى معرف مجموعة الوسائط")

    def as_dict(self) -> Dict[str, Any]:
        self.validate()
        return {"channel_id": self.channel_id, "message_id": self.message_id, "raw_text": self.raw_text,
                "entities": self.entities, "buttons": [button.as_dict() for button in self.buttons],
                "media": [media.as_dict() for media in sorted(self.media, key=lambda item: item.order)],
                "media_group_id": self.media_group_id}


def buttons_from_dict(items: Iterable[Dict[str, Any]]) -> List[InlineButton]:
    return [InlineButton(str(item.get("label", "")), str(item.get("url", ""))) for item in items]


def media_from_dict(items: Iterable[Dict[str, Any]]) -> List[MediaItem]:
    return [MediaItem(str(item.get("kind", "")), str(item.get("file_path", "")), str(item.get("caption", "")), int(item.get("order", index))) for index, item in enumerate(items)]


def build_edit_plan(original: EditablePost, updated: EditablePost) -> Dict[str, Any]:
    original.validate()
    updated.validate()
    if (original.channel_id, original.message_id) != (updated.channel_id, updated.message_id):
        raise ValueError("لا يمكن تغيير هوية المنشور داخل خطة التعديل")
    changed = {
        "text": original.raw_text != updated.raw_text or original.entities != updated.entities,
        "buttons": [button.as_dict() for button in original.buttons] != [button.as_dict() for button in updated.buttons],
        "media": [media.as_dict() for media in original.media] != [media.as_dict() for media in updated.media],
    }
    return {"channel_id": original.channel_id, "message_id": original.message_id, "changed": changed,
            "requires_media_reupload": changed["media"], "requires_review": any(changed.values()),
            "before": original.as_dict(), "after": updated.as_dict()}
