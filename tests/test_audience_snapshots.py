from src.studio_store import StudioStore


def test_audience_snapshots_are_local_and_queryable(tmp_path):
    store = StudioStore(tmp_path / 'studio.sqlite')
    store.upsert_channel({'id': 'a', 'title': 'أخبار'})
    store.record_audience_snapshot('a', {'member_count': 10, 'observable_active_count': 3, 'new_members': 2}, '2026-11-08T10:00:00+00:00')
    store.record_audience_snapshot('a', {'member_count': 12, 'observable_active_count': 4, 'left_members': 1}, '2026-11-09T10:00:00+00:00')
    rows = store.list_audience_snapshots('a')
    assert rows[0]['member_count'] == 12
    assert rows[1]['new_members'] == 2
    store.record_membership_snapshot('2026-11-08T10:00:00+00:00', 'a', ['1', '2'])
    latest = store.latest_membership_snapshot('a')
    assert latest['user_ids'] == {'1', '2'}
