"""Authentication state machine for the local Arabic UI."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from src.telegram_gateway import TelegramGateway


@dataclass
class SessionStatus:
    configured: bool
    connected: bool
    authorized: bool
    phone: Optional[str] = None
    display_name: Optional[str] = None
    message: str = ""


class TelegramSessionRuntime:
    def __init__(self, session_root: str | Path = "temp/accounts"):
        self.session_root = Path(session_root)
        self.gateway: Optional[TelegramGateway] = None
        self.phone: Optional[str] = None
        self.authorized = False
        self.display_name: Optional[str] = None

    def configure(self, api_id: int, api_hash: str, phone: str) -> SessionStatus:
        digits = phone[1:].replace(" ", "") if phone.startswith("+") else ""
        if not digits.isdigit() or not 7 <= len(digits) <= 15:
            raise ValueError("رقم الهاتف يجب أن يبدأ بعلامة + وبصيغة دولية")
        account_dir = self.session_root / phone.replace("+", "00").replace(" ", "")
        account_dir.mkdir(parents=True, exist_ok=True)
        # ملفات Telethon session تحتوي مفاتيح مصادقة تمنح وصولًا للحساب.
        # حصر الوصول إلى مالك العملية يحميها حتى عندما يكون umask النظام واسعًا.
        try:
            account_dir.chmod(0o700)
        except OSError:
            pass
        self.gateway = TelegramGateway(api_id, api_hash, account_dir / "session")
        self.phone = phone
        return self.status("تم تجهيز جلسة الحساب محليًا")

    async def connect(self) -> SessionStatus:
        if self.gateway is None:
            raise RuntimeError("يجب تجهيز بيانات الحساب أولًا")
        self.authorized = await self.gateway.connect()
        message = "تم الاتصال بالحساب" if self.authorized else "تم الاتصال؛ الحساب يحتاج إلى تسجيل الدخول"
        return self.status(message)

    async def request_code(self) -> SessionStatus:
        if not self.gateway or not self.phone:
            raise RuntimeError("بيانات الحساب غير مجهزة")
        await self.gateway.request_login_code(self.phone)
        return self.status("تم إرسال رمز التحقق إلى Telegram")

    async def verify_code(self, code: str, password: Optional[str] = None) -> SessionStatus:
        if not self.gateway or not self.phone:
            raise RuntimeError("بيانات الحساب غير مجهزة")
        user = await self.gateway.complete_login(self.phone, code, password)
        self.authorized = True
        self.display_name = " ".join(filter(None, [getattr(user, "first_name", None), getattr(user, "last_name", None)])) or getattr(user, "username", None)
        return self.status("تم تسجيل الدخول وحفظ الجلسة محليًا")

    async def disconnect(self) -> SessionStatus:
        if self.gateway:
            await self.gateway.disconnect()
        self.authorized = False
        return self.status("تم فصل الحساب")

    def status(self, message: str = "") -> SessionStatus:
        return SessionStatus(
            configured=self.gateway is not None, connected=bool(self.gateway and self.gateway.client),
            authorized=self.authorized, phone=self.phone, display_name=self.display_name, message=message,
        )
