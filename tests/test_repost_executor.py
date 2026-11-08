import math
import pytest

from src.repost_executor import RetryableTransferError, execute_repost_plan


def test_repost_retries_and_deduplicates():
    plan = {"items": [{"source_channel_id": "a", "message_id": 1, "destination_channel_id": "b", "mode": "copy"}]}
    calls = []
    attempts = {"count": 0}
    def sender(item):
        attempts["count"] += 1
        calls.append(item)
        if attempts["count"] == 1:
            raise RetryableTransferError("انتظر", 0)
    result = execute_repost_plan(plan, sender, approved=True, sleep=lambda _: None)
    assert result[0].status == "sent"
    assert result[0].attempts == 2
    result = execute_repost_plan(plan, sender, approved=True, completed_keys={result[0].key})
    assert result[0].status == "skipped_duplicate"


def test_repost_requires_approval():
    try:
        execute_repost_plan({"items": []}, lambda _: None)
    except ValueError as exc:
        assert "اعتماد" in str(exc)
    else:
        raise AssertionError("approval should be required")


def test_empty_completed_set_is_updated_after_success():
    plan = {"items": [{"source_channel_id": "a", "message_id": 2, "destination_channel_id": "b"}]}
    completed = set()
    result = execute_repost_plan(plan, lambda _: None, approved=True, completed_keys=completed)
    assert result[0].status == "sent"
    assert completed == {result[0].key}


def test_repost_rejects_nonpositive_retry_limit():
    with pytest.raises(ValueError):
        execute_repost_plan({"items": []}, lambda _: None, approved=True, max_retries=0)


def test_repost_rejects_nonfinite_retry_delay():
    plan = {"items": [{"source_channel_id": "a", "message_id": 2, "destination_channel_id": "b"}]}
    result = execute_repost_plan(
        plan,
        lambda _: (_ for _ in ()).throw(RetryableTransferError("bad delay", math.inf)),
        approved=True,
        max_retries=2,
        sleep=lambda _: None,
    )
    assert result[0].status == "failed"
    assert "غير صالحة" in result[0].error
