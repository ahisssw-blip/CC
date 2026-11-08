"""Safe planning models for moving and reposting Telegram messages."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class RepostItem:
    source_channel_id: str
    message_id: int
    destination_channel_id: str
    mode: str = "copy"
    scheduled_at: Optional[str] = None

    def validate(self) -> None:
        if not self.source_channel_id or not self.destination_channel_id:
            raise ValueError("القناة المصدر والوجهة مطلوبتان")
        if self.source_channel_id == self.destination_channel_id:
            raise ValueError("لا يمكن نقل المنشور إلى القناة نفسها")
        if self.mode not in {"copy", "forward", "move"}:
            raise ValueError("نوع النقل غير معروف")
        if self.mode == "move" and self.scheduled_at:
            raise ValueError("النقل الحقيقي لا يقبل جدولة؛ استخدم إعادة النشر")

    def as_dict(self) -> Dict[str, Any]:
        self.validate()
        return self.__dict__.copy()


def build_repost_plan(items: Iterable[RepostItem]) -> Dict[str, Any]:
    normalized = list(items)
    for item in normalized:
        item.validate()
    return {"status": "pending_review", "items": [item.as_dict() for item in normalized], "total": len(normalized), "requires_confirmation": True}
