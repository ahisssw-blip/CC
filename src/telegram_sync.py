"""Incremental Telegram-to-SQLite synchronization services."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from src.studio_store import StudioStore
from src.telegram_gateway import TelegramGateway


@dataclass
class SyncResult:
    channel_id: str
    fetched: int = 0
    stored: int = 0
    failed: int = 0
    last_message_id: int = 0


class TelegramSyncService:
    def __init__(self, gateway: TelegramGateway, store: StudioStore):
        self.gateway = gateway
        self.store = store

    async def sync_channel(self, channel: Any, channel_info: dict[str, Any], *, limit: Optional[int] = None,
                           progress: Optional[Callable[[int, int], None]] = None) -> SyncResult:
        channel_id = str(channel_info["id"])
        self.store.upsert_channel(channel_info)
        result = SyncResult(channel_id=channel_id)
        with self.store.connection() as db:
            row = db.execute("SELECT MAX(message_id) FROM messages WHERE channel_id=?", (channel_id,)).fetchone()
        newest = int(row[0] or 0)
        async for message in self.gateway.iter_messages(channel, limit=limit):
            result.fetched += 1
            if message["id"] <= newest:
                continue
            try:
                self.store.upsert_message(channel_id, message)
                result.stored += 1
                result.last_message_id = max(result.last_message_id, message["id"])
                if progress:
                    progress(result.fetched, limit or 0)
            except Exception:
                result.failed += 1
        return result
