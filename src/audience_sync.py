"""Permission-aware audience synchronization for Telegram Channel Studio."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.studio_store import StudioStore


async def sync_channel_audience(gateway: Any, store: StudioStore, channel: Any, channel_id: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    """Capture one local snapshot; Telegram remains the source of observable data."""
    resolved_channel_id = str(channel_id or getattr(channel, "id", channel))
    captured_at = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    members = []
    async for member in gateway.iter_participants(channel, limit=limit):
        members.append(member)
    current_ids = {str(member["id"]) for member in members}
    previous = store.latest_membership_snapshot(resolved_channel_id, before=captured_at)
    previous_ids = previous["user_ids"]
    ever_seen = store.ever_seen_members(resolved_channel_id, current_ids)
    new_ids = current_ids - previous_ids
    left_ids = previous_ids - current_ids
    returned_ids = (current_ids & ever_seen) - previous_ids
    for member in members:
        store.upsert_user(resolved_channel_id, {**member, "last_seen": captured_at})
    store.record_membership_snapshot(captured_at, resolved_channel_id, current_ids)
    store.record_audience_snapshot(resolved_channel_id, {
        "member_count": len(current_ids),
        "observable_active_count": 0,
        "new_members": len(new_ids),
        "left_members": len(left_ids),
        "source": "telegram_api",
    }, captured_at)
    return {
        "channel_id": resolved_channel_id,
        "captured_at": captured_at,
        "member_count": len(current_ids),
        "new_member_ids": sorted(new_ids),
        "left_member_ids": sorted(left_ids),
        "returned_member_ids": sorted(returned_ids),
        "activity_note": "النشاط القابل للرصد لا يساوي المشاهدة ولا يتضمن مشاهدي المنشورات",
        "privacy_note": "تم حفظ الحقول التي أعادها Telegram فقط وبقيت محلية",
    }
