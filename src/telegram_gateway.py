"""Safe, UI-independent gateway to Telegram via a user MTProto session."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional

from src.message_model import EditablePost

@dataclass(frozen=True)
class ChannelPermission:
    channel_id: str
    can_edit_messages: bool = False
    can_post_messages: bool = False
    can_delete_messages: bool = False
    can_invite_users: bool = False
    is_creator: bool = False
    reason: str = ""


class TelegramGateway:
    """A narrow adapter; no UI code or database writes belong here."""

    def __init__(self, api_id: int, api_hash: str, session_path: str | Path):
        if not api_id or not api_hash:
            raise ValueError("API_ID وAPI_HASH مطلوبان")
        self.api_id = int(api_id)
        self.api_hash = api_hash
        self.session_path = str(session_path)
        self.client: Any = None

    async def connect(self) -> bool:
        from telethon import TelegramClient
        if self.client is None:
            self.client = TelegramClient(self.session_path, self.api_id, self.api_hash)
        await self.client.connect()
        return bool(await self.client.is_user_authorized())

    async def disconnect(self) -> None:
        if self.client is not None:
            await self.client.disconnect()
            self.client = None

    def require_client(self) -> Any:
        if self.client is None:
            raise RuntimeError("بوابة Telegram غير متصلة")
        return self.client

    async def request_login_code(self, phone: str) -> None:
        await self.require_client().send_code_request(phone)

    async def complete_login(self, phone: str, code: str, password: Optional[str] = None) -> Any:
        from telethon.errors import SessionPasswordNeededError
        client = self.require_client()
        try:
            await client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            if not password:
                raise ValueError("الحساب محمي بالتحقق بخطوتين ويحتاج كلمة المرور")
            await client.sign_in(password=password)
        return await client.get_me()

    async def list_channels(self) -> list[Dict[str, Any]]:
        dialogs = await self.require_client().get_dialogs()
        result = []
        for dialog in dialogs:
            if not (dialog.is_channel or dialog.is_group):
                continue
            entity = dialog.entity
            result.append({
                "id": entity.id, "title": entity.title,
                "username": getattr(entity, "username", None),
                "participants_count": getattr(entity, "participants_count", 0) or 0,
                "type": "Channel" if dialog.is_channel else "Group",
            })
        return sorted(result, key=lambda item: item["title"].casefold())

    async def permissions(self, channel: Any) -> ChannelPermission:
        try:
            permissions = await self.require_client().get_permissions(channel, "me")
            rights = getattr(permissions, "admin_rights", None)
            return ChannelPermission(
                channel_id=str(getattr(channel, "id", channel)),
                can_edit_messages=bool(getattr(permissions, "is_creator", False) or getattr(rights, "edit_messages", False)),
                can_post_messages=bool(getattr(permissions, "is_creator", False) or getattr(rights, "post_messages", False)),
                can_delete_messages=bool(getattr(permissions, "is_creator", False) or getattr(rights, "delete_messages", False)),
                can_invite_users=bool(getattr(permissions, "is_creator", False) or getattr(rights, "invite_users", False)),
                is_creator=bool(getattr(permissions, "is_creator", False)),
            )
        except Exception as exc:
            return ChannelPermission(str(getattr(channel, "id", channel)), reason=str(exc))

    async def iter_messages(self, channel: Any, *, limit: Optional[int] = None,
                            min_id: int = 0, max_id: int = 0) -> AsyncIterator[Dict[str, Any]]:
        kwargs: Dict[str, Any] = {"limit": limit}
        if min_id:
            kwargs["min_id"] = min_id
        if max_id:
            kwargs["max_id"] = max_id
        async for message in self.require_client().iter_messages(channel, **kwargs):
            yield self.serialize_message(message)

    async def iter_participants(self, channel: Any, *, limit: Optional[int] = None) -> AsyncIterator[Dict[str, Any]]:
        """Yield only member fields returned by Telegram after a permission check."""
        permission = await self.permissions(channel)
        if not (permission.can_invite_users or permission.is_creator):
            raise PermissionError("لا يملك الحساب صلاحية قراءة أعضاء هذه القناة")
        async for user in self.require_client().iter_participants(channel, limit=limit):
            yield self.serialize_participant(user)

    @staticmethod
    def serialize_participant(user: Any) -> Dict[str, Any]:
        return {
            "id": str(getattr(user, "id")),
            "username": getattr(user, "username", None),
            "first_name": getattr(user, "first_name", None),
            "last_name": getattr(user, "last_name", None),
            "bot": bool(getattr(user, "bot", False)),
            "premium": bool(getattr(user, "premium", False)),
            "verified": bool(getattr(user, "verified", False)),
            "observable_fields": ["id", "username", "first_name", "last_name", "bot", "premium", "verified"],
        }

    @staticmethod
    def serialize_message(message: Any) -> Dict[str, Any]:
        try:
            from src.formatting import entities_to_dicts
            serialized_entities = entities_to_dicts(getattr(message, "entities", None))
        except ModuleNotFoundError:
            serialized_entities = []
        media = getattr(message, "media", None)
        reactions = []
        for item in getattr(getattr(message, "reactions", None), "results", []) or []:
            reaction = getattr(item, "reaction", None)
            reactions.append({
                "emoticon": getattr(reaction, "emoticon", None),
                "document_id": getattr(reaction, "document_id", None),
                "count": getattr(item, "count", 0),
            })
        return {
            "id": message.id, "date": message.date.isoformat() if message.date else None,
            "edit_date": message.edit_date.isoformat() if message.edit_date else None,
            "text": message.text or "", "raw_text": message.raw_text or "",
            "text_html": getattr(message, "text_html", message.raw_text or ""),
            "entities": serialized_entities,
            "media_type": type(media).__name__ if media else None,
            "has_media": bool(media), "views": getattr(message, "views", 0) or 0,
            "forwards": getattr(message, "forwards", 0) or 0,
            "pinned": bool(getattr(message, "pinned", False)),
            "reply_to": getattr(getattr(message, "reply_to", None), "reply_to_msg_id", None),
            "reactions": reactions,
        }

    async def edit_message(self, channel: Any, message_id: int, text: str, entities: list[Any]) -> Any:
        return await self.require_client().edit_message(channel, message_id, text, formatting_entities=entities)

    async def edit_post(self, channel: Any, post: EditablePost) -> Any:
        """Edit text/entities/buttons only; media replacement is explicit and separate."""
        post.validate()
        if post.media:
            raise NotImplementedError("تعديل الوسائط يحتاج مسار إعادة رفع منفصلًا وآمنًا")
        from src.formatting import dicts_to_entities
        from telethon import Button
        buttons = [[Button.url(item.label, item.url) for item in post.buttons]] if post.buttons else None
        return await self.require_client().edit_message(
            channel, post.message_id, post.raw_text,
            formatting_entities=dicts_to_entities(post.entities), buttons=buttons,
        )

    async def forward_message(self, destination: Any, source: Any, message_id: int) -> Any:
        return await self.require_client().forward_messages(destination, message_id, from_peer=source)
