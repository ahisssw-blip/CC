import asyncio
import pytest

from src.audience_sync import sync_channel_audience
from src.studio_store import StudioStore


class FakeGateway:
    def __init__(self, batches):
        self.batches = iter(batches)
    async def iter_participants(self, channel, limit=None):
        for member in next(self.batches):
            yield member


def test_sync_detects_new_left_and_returned_members(tmp_path):
    async def scenario():
        store = StudioStore(tmp_path / 'audience.sqlite')
        store.upsert_channel({'id': 'a', 'title': 'أخبار'})
        gateway = FakeGateway([
            [{'id': '1', 'first_name': 'أ'}, {'id': '2', 'first_name': 'ب'}],
            [{'id': '2', 'first_name': 'ب'}, {'id': '3', 'first_name': 'ج'}],
            [{'id': '1', 'first_name': 'أ'}, {'id': '2', 'first_name': 'ب'}, {'id': '3', 'first_name': 'ج'}],
        ])
        first = await sync_channel_audience(gateway, store, 'a')
        second = await sync_channel_audience(gateway, store, 'a')
        third = await sync_channel_audience(gateway, store, 'a')
        assert first['new_member_ids'] == ['1', '2']
        assert second['new_member_ids'] == ['3']
        assert second['left_member_ids'] == ['1']
        assert third['returned_member_ids'] == ['1']
    asyncio.run(scenario())


def test_permission_error_is_not_hidden(tmp_path):
    class Denied:
        async def iter_participants(self, channel, limit=None):
            raise PermissionError('لا يملك الحساب صلاحية قراءة أعضاء هذه القناة')
            yield
    async def scenario():
        store = StudioStore(tmp_path / 'audience.sqlite')
        with pytest.raises(PermissionError):
            await sync_channel_audience(Denied(), store, 'a')
    asyncio.run(scenario())
