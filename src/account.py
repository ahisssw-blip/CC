"""
Account context management module.
Handles per-account directory structure and path resolution.
"""
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.config import ACCOUNTS_BASE_DIR


@dataclass
class AccountPaths:
    """Container for account-specific paths"""
    phone: str
    base_dir: str
    session_path: str
    database_path: str
    videos_dir: str
    exports_dir: str

    @classmethod
    def for_phone(cls, phone: str) -> 'AccountPaths':
        """Create safe account paths from a normalized international number."""
        if not isinstance(phone, str):
            raise ValueError("رقم الهاتف يجب أن يكون نصًا بصيغة دولية")
        candidate = phone.strip()
        digits = candidate[1:].replace(" ", "") if candidate.startswith("+") else ""
        if not re.fullmatch(r"\d{7,15}", digits):
            raise ValueError("رقم الهاتف يجب أن يبدأ بعلامة + ويحتوي من 7 إلى 15 رقمًا")
        normalized_phone = "+" + digits
        root = Path(ACCOUNTS_BASE_DIR).expanduser().resolve()
        base_path = (root / normalized_phone).resolve()
        try:
            base_path.relative_to(root)
        except ValueError as exc:
            raise ValueError("مسار الحساب خارج مجلد الحسابات المسموح") from exc
        base = str(base_path)
        return cls(
            phone=normalized_phone,
            base_dir=base,
            session_path=os.path.join(base, 'session'),
            database_path=os.path.join(base, 'database.json'),
            videos_dir=os.path.join(base, 'videos'),
            exports_dir=os.path.join(base, 'exports')
        )

    def ensure_directories(self):
        """Create all required directories for this account"""
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.videos_dir, exist_ok=True)
        os.makedirs(self.exports_dir, exist_ok=True)
        try:
            os.chmod(self.base_dir, 0o700)
            os.chmod(self.videos_dir, 0o700)
            os.chmod(self.exports_dir, 0o700)
        except OSError as exc:
            raise OSError("تعذر تأمين صلاحيات مجلدات الحساب المحلية") from exc


class AccountContext:
    """Singleton-like context manager for current account"""
    _current: Optional[AccountPaths] = None

    @classmethod
    def set_account(cls, phone: str) -> AccountPaths:
        """Set the current account context"""
        cls._current = AccountPaths.for_phone(phone)
        cls._current.ensure_directories()
        return cls._current

    @classmethod
    def get_current(cls) -> Optional[AccountPaths]:
        """Get current account paths, or None if not set"""
        return cls._current

    @classmethod
    def require_current(cls) -> AccountPaths:
        """Get current account paths, raise if not set"""
        if cls._current is None:
            raise RuntimeError("No account context set. Call set_account() first.")
        return cls._current

    @classmethod
    def clear(cls):
        """Clear the current account context"""
        cls._current = None
