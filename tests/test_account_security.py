from pathlib import Path

import pytest

from src import account


def test_account_path_rejects_traversal(monkeypatch, tmp_path):
    monkeypatch.setattr(account, "ACCOUNTS_BASE_DIR", str(tmp_path / "accounts"))
    for invalid in ("../../outside", "+123456/../../outside", "+12abc456789", "+123"):
        with pytest.raises(ValueError):
            account.AccountPaths.for_phone(invalid)


def test_account_directories_are_private(monkeypatch, tmp_path):
    root = tmp_path / "accounts"
    monkeypatch.setattr(account, "ACCOUNTS_BASE_DIR", str(root))
    paths = account.AccountPaths.for_phone("+12345678901")
    paths.ensure_directories()
    assert Path(paths.base_dir).resolve().is_relative_to(root.resolve())
    assert Path(paths.base_dir).stat().st_mode & 0o777 == 0o700
