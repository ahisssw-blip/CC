import asyncio

import pytest

from src.telegram_operation_executor import execute_telegram_batch


class Permission:
    can_edit_messages = True


class Gateway:
    def __init__(self):
        self.calls = []
    async def permissions(self, channel):
        return Permission()
    async def edit_message(self, channel, message_id, text, entities):
        self.calls.append((channel, message_id, text, entities))


def run(coro):
    return asyncio.run(coro)


def test_live_executor_requires_approval_and_applies_text():
    gateway = Gateway()
    batch = {"id": 4, "status": "approved", "items": [{"id": 8, "channel_id": "a", "message_id": 2, "before": "قبل", "after": "بعد", "status": "pending"}]}
    result = run(execute_telegram_batch(gateway, batch, lambda channel: channel, approved=True))
    assert result["status"] == "completed"
    assert result["results"][0]["status"] == "applied"
    assert gateway.calls[0][1:3] == (2, "بعد")
    with pytest.raises(ValueError):
        run(execute_telegram_batch(gateway, batch, lambda channel: channel))


def test_live_executor_rejects_media_and_bad_permission():
    gateway = Gateway()
    batch = {"id": 5, "status": "approved", "items": [{"id": 9, "channel_id": "a", "message_id": 3, "after": "x", "media": True}]}
    result = run(execute_telegram_batch(gateway, batch, lambda channel: channel, approved=True))
    assert result["results"][0]["status"] == "failed"


def test_live_executor_rejects_stale_preview():
    class StaleGateway(Gateway):
        async def get_message(self, channel, message_id):
            return type('Message', (), {'raw_text': 'تغير'})()
    batch = {"id": 6, "status": "approved", "items": [{"id": 10, "channel_id": "a", "message_id": 3, "before": "قديم", "after": "جديد"}]}
    result = run(execute_telegram_batch(StaleGateway(), batch, lambda channel: channel, approved=True))
    assert result["results"][0]["status"] == "failed"
    assert 'تغير' in result["results"][0]["error"]


def test_live_executor_retries_flood_wait():
    waits = []
    class Flood(Exception):
        seconds = 0
    class FloodGateway(Gateway):
        def __init__(self):
            super().__init__(); self.calls_count = 0
        async def edit_message(self, channel, message_id, text, entities):
            self.calls_count += 1
            if self.calls_count == 1: raise Flood('انتظر')
    async def delay(seconds): waits.append(seconds)
    batch = {"id": 7, "status": "approved", "items": [{"id": 11, "channel_id": "a", "message_id": 3, "after": "جديد"}]}
    result = run(execute_telegram_batch(FloodGateway(), batch, lambda channel: channel, approved=True, retry_delay=delay))
    assert result["results"][0]["status"] == "applied"
    assert waits == [0.0]
