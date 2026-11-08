import pytest

from src.session_runtime import TelegramSessionRuntime


def test_session_runtime_validates_phone(tmp_path):
    runtime = TelegramSessionRuntime(tmp_path)
    with pytest.raises(ValueError):
        runtime.configure(123, "hash", "12345")


def test_session_runtime_status_does_not_expose_hash(tmp_path):
    runtime = TelegramSessionRuntime(tmp_path)
    status = runtime.configure(123, "secret-hash", "+963900000000")
    assert status.configured is True
    assert "secret-hash" not in repr(status)
    assert status.phone == "+963900000000"
    account_dirs = list(tmp_path.iterdir())
    assert len(account_dirs) == 1
    assert account_dirs[0].stat().st_mode & 0o777 == 0o700


def test_session_runtime_rejects_overlong_phone_number(tmp_path):
    runtime = TelegramSessionRuntime(tmp_path)
    with pytest.raises(ValueError):
        runtime.configure(123, "hash", "+1234567890123456")
