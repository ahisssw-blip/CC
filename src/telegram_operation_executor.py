"""Live Telegram executor for approved text/button change batches.

This module is deliberately separate from the local SQLite executor. It never
runs without explicit approval and it refuses unsupported media changes.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Iterable, Optional

from src.repost_executor import RetryableTransferError


@dataclass
class TelegramOperationResult:
    item_id: int
    status: str
    attempts: int = 0
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


async def execute_telegram_batch(
    gateway: Any,
    batch: Dict[str, Any],
    resolve_channel: Callable[[str], Awaitable[Any] | Any],
    *,
    approved: bool = False,
    batch_size: int = 50,
    max_retries: int = 3,
    retry_delay: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> Dict[str, Any]:
    """Execute only approved, pending, text-only items against Telegram."""
    if not approved or batch.get("status") != "approved":
        raise ValueError("يجب اعتماد الحزمة قبل تنفيذها على Telegram")
    if batch_size < 1:
        raise ValueError("حجم الدفعة يجب أن يكون موجبًا")
    results = []
    for item in list(batch.get("items", []))[:batch_size]:
        item_id = int(item["id"])
        if item.get("status") not in {None, "pending"}:
            results.append(TelegramOperationResult(item_id, "skipped", 0, "العنصر ليس بانتظار التنفيذ"))
            continue
        if item.get("media") or item.get("album"):
            results.append(TelegramOperationResult(item_id, "failed", 0, "تعديل الوسائط يحتاج مسارًا منفصلًا"))
            continue
        attempts = 0
        while attempts < max_retries:
            attempts += 1
            try:
                channel = resolve_channel(str(item["channel_id"]))
                if asyncio.iscoroutine(channel):
                    channel = await channel
                permission = await gateway.permissions(channel)
                if not permission.can_edit_messages:
                    raise PermissionError("لا توجد صلاحية تعديل الرسائل في القناة")
                before = item.get("before", item.get("before_text"))
                if before is not None and hasattr(gateway, "get_message"):
                    current = await gateway.get_message(channel, int(item["message_id"]))
                    current_text = getattr(current, "raw_text", getattr(current, "text", current if isinstance(current, str) else None))
                    if current_text != before:
                        raise ValueError("تغير المنشور على Telegram منذ إنشاء المعاينة؛ أعد المراجعة")
                entities = item.get("entities") or []
                await gateway.edit_message(channel, int(item["message_id"]), item.get("after", item.get("after_text", "")), entities)
                results.append(TelegramOperationResult(item_id, "applied", attempts))
                break
            except RetryableTransferError as exc:
                if attempts >= max_retries:
                    results.append(TelegramOperationResult(item_id, "failed", attempts, str(exc)))
                    break
                await retry_delay(max(0.0, float(exc.retry_after)))
            except Exception as exc:
                wait_seconds = getattr(exc, "seconds", None)
                if wait_seconds is not None and attempts < max_retries:
                    await retry_delay(max(0.0, float(wait_seconds)))
                    continue
                results.append(TelegramOperationResult(item_id, "failed", attempts, str(exc)))
                break
    return {
        "batch_id": batch.get("id"),
        "status": "completed" if results and all(item.status == "applied" for item in results) else "partially_applied",
        "results": [item.as_dict() for item in results],
    }
