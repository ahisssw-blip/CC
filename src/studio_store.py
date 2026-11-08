"""Local SQLite index for Telegram Channel Studio.

The legacy application stores data in nested JSON. This module provides a
stable, queryable local index without changing the existing Telegram client.
It is intentionally independent from Telethon so the future UI can use it
without opening a Telegram session.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS channels (
    channel_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    username TEXT,
    channel_type TEXT,
    member_count INTEGER,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    channel_id TEXT NOT NULL,
    message_id INTEGER NOT NULL,
    date TEXT,
    edit_date TEXT,
    text TEXT,
    raw_text TEXT,
    text_html TEXT,
    media_type TEXT,
    media_file_path TEXT,
    views INTEGER DEFAULT 0,
    forwards INTEGER DEFAULT 0,
    has_media INTEGER DEFAULT 0,
    pinned INTEGER DEFAULT 0,
    reply_to INTEGER,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (channel_id, message_id),
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(date);
CREATE INDEX IF NOT EXISTS idx_messages_channel_date ON messages(channel_id, date);
CREATE INDEX IF NOT EXISTS idx_messages_views ON messages(views);

CREATE TABLE IF NOT EXISTS users (
    channel_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    bot INTEGER DEFAULT 0,
    premium INTEGER DEFAULT 0,
    verified INTEGER DEFAULT 0,
    first_seen TEXT,
    last_seen TEXT,
    PRIMARY KEY (channel_id, user_id),
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audience_snapshots (
    captured_at TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    member_count INTEGER DEFAULT 0,
    observable_active_count INTEGER DEFAULT 0,
    new_members INTEGER DEFAULT 0,
    left_members INTEGER DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'telegram_api',
    PRIMARY KEY (captured_at, channel_id),
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audience_membership_snapshots (
    captured_at TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'present',
    PRIMARY KEY (captured_at, channel_id, user_id),
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_type TEXT NOT NULL,
    channel_id TEXT,
    message_id INTEGER,
    before_text TEXT,
    after_text TEXT,
    status TEXT NOT NULL DEFAULT 'planned',
    created_at TEXT NOT NULL
);
"""


class StudioStore:
    """SQLite-backed local index used by the Studio UI and services."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        try:
            # مفاتيح SQLite الخارجية إعداد لكل اتصال، لا إعداد دائم للمخطط.
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 10000")
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript(SCHEMA)
            connection.execute("INSERT OR IGNORE INTO schema_meta(key,value) VALUES('schema_version','1')")
            try:
                self.path.chmod(0o600)
            except OSError:
                pass

    def schema_version(self) -> int:
        with self.connection() as db:
            row = db.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
            return int(row["value"]) if row else 0

    def backup(self, destination: str | Path) -> Path:
        """Create a private byte-for-byte backup of the local index."""
        target = Path(destination).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("PRAGMA wal_checkpoint(FULL)")
        shutil.copy2(self.path, target)
        try:
            target.chmod(0o600)
        except OSError:
            pass
        return target

    def upsert_channel(self, channel: Dict[str, Any]) -> None:
        channel_id = str(channel.get("id") or channel.get("channel_id"))
        if not channel_id or channel_id == "None":
            raise ValueError("channel requires an id")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.connection() as db:
            db.execute(
                """INSERT INTO channels(channel_id,title,username,channel_type,member_count,updated_at)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(channel_id) DO UPDATE SET title=excluded.title,
                   username=excluded.username, channel_type=excluded.channel_type,
                   member_count=excluded.member_count, updated_at=excluded.updated_at""",
                (channel_id, channel.get("title", channel_id), channel.get("username"),
                 channel.get("type"), channel.get("participants_count"), now),
            )

    def upsert_message(self, channel_id: str, message: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.connection() as db:
            db.execute(
                """INSERT INTO messages(channel_id,message_id,date,edit_date,text,raw_text,text_html,
                   media_type,media_file_path,views,forwards,has_media,pinned,reply_to,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(channel_id,message_id) DO UPDATE SET date=excluded.date,
                   edit_date=excluded.edit_date,text=excluded.text,raw_text=excluded.raw_text,
                   text_html=excluded.text_html,media_type=excluded.media_type,
                   media_file_path=excluded.media_file_path,views=excluded.views,
                   forwards=excluded.forwards,has_media=excluded.has_media,pinned=excluded.pinned,
                   reply_to=excluded.reply_to,updated_at=excluded.updated_at""",
                (str(channel_id), int(message["id"]), message.get("date"), message.get("edit_date"),
                 message.get("text"), message.get("raw_text"), message.get("text_html"),
                 message.get("media_type"), message.get("media_file_path"), message.get("views", 0) or 0,
                 message.get("forwards", 0) or 0, int(bool(message.get("has_media"))),
                 int(bool(message.get("pinned"))), message.get("reply_to"), now),
            )

    def upsert_user(self, channel_id: str, user: Dict[str, Any]) -> None:
        with self.connection() as db:
            db.execute(
                """INSERT INTO users(channel_id,user_id,username,first_name,last_name,bot,premium,verified,first_seen,last_seen)
                   VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(channel_id,user_id) DO UPDATE SET username=excluded.username,
                   first_name=excluded.first_name,last_name=excluded.last_name,bot=excluded.bot,
                   premium=excluded.premium,verified=excluded.verified,last_seen=excluded.last_seen""",
                (str(channel_id), str(user["id"]), user.get("username"), user.get("first_name"),
                 user.get("last_name"), int(bool(user.get("bot"))), int(bool(user.get("premium"))),
                 int(bool(user.get("verified"))), user.get("first_seen"), user.get("last_seen")),
            )

    def record_audience_snapshot(self, channel_id: str, snapshot: Dict[str, Any], captured_at: Optional[str] = None) -> None:
        timestamp = captured_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.connection() as db:
            db.execute(
                """INSERT OR REPLACE INTO audience_snapshots
                   (captured_at, channel_id, member_count, observable_active_count, new_members, left_members, source)
                   VALUES(?,?,?,?,?,?,?)""",
                (timestamp, str(channel_id), int(snapshot.get("member_count", 0) or 0),
                 int(snapshot.get("observable_active_count", 0) or 0), int(snapshot.get("new_members", 0) or 0),
                 int(snapshot.get("left_members", 0) or 0), str(snapshot.get("source", "telegram_api"))),
            )

    def list_audience_snapshots(self, channel_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        query = "SELECT * FROM audience_snapshots"
        params: List[Any] = []
        if channel_id is not None:
            query += " WHERE channel_id=?"
            params.append(str(channel_id))
        query += " ORDER BY captured_at DESC LIMIT ?"
        params.append(max(1, min(int(limit), 1000)))
        with self.connection() as db:
            return [dict(row) for row in db.execute(query, params).fetchall()]

    def record_membership_snapshot(self, captured_at: str, channel_id: str, user_ids: Iterable[str]) -> None:
        with self.connection() as db:
            db.executemany(
                "INSERT OR REPLACE INTO audience_membership_snapshots(captured_at,channel_id,user_id,status) VALUES(?,?,?,'present')",
                [(captured_at, str(channel_id), str(user_id)) for user_id in user_ids],
            )

    def latest_membership_snapshot(self, channel_id: str, before: Optional[str] = None) -> Dict[str, Any]:
        with self.connection() as db:
            if before:
                row = db.execute("SELECT MAX(captured_at) AS captured_at FROM audience_membership_snapshots WHERE channel_id=? AND captured_at<?", (str(channel_id), before)).fetchone()
            else:
                row = db.execute("SELECT MAX(captured_at) AS captured_at FROM audience_membership_snapshots WHERE channel_id=?", (str(channel_id),)).fetchone()
            captured_at = row["captured_at"] if row else None
            if not captured_at:
                return {"captured_at": None, "user_ids": set()}
            users = db.execute("SELECT user_id FROM audience_membership_snapshots WHERE channel_id=? AND captured_at=?", (str(channel_id), captured_at)).fetchall()
            return {"captured_at": captured_at, "user_ids": {str(item["user_id"]) for item in users}}

    def ever_seen_members(self, channel_id: str, user_ids: Iterable[str]) -> set[str]:
        ids = [str(item) for item in user_ids]
        if not ids:
            return set()
        placeholders = ",".join("?" for _ in ids)
        with self.connection() as db:
            rows = db.execute(f"SELECT DISTINCT user_id FROM audience_membership_snapshots WHERE channel_id=? AND user_id IN ({placeholders})", [str(channel_id), *ids]).fetchall()
            return {str(item["user_id"]) for item in rows}

    def import_legacy_database(self, database: Dict[str, Any]) -> Dict[str, int]:
        """Import the current nested JSON structure without deleting its source."""
        channels = {str(c.get("id")): c for c in database.get("channels", []) if c.get("id")}
        imported_channels = imported_messages = imported_users = 0
        message_groups = database.get("messages", {})
        user_groups = database.get("users", {})
        for channel_id, messages in message_groups.items():
            channel = channels.get(str(channel_id), {"id": channel_id, "title": str(channel_id)})
            self.upsert_channel(channel)
            imported_channels += 1
            for message in messages.values() if isinstance(messages, dict) else messages:
                if message.get("id") is not None:
                    self.upsert_message(str(channel_id), message)
                    imported_messages += 1
        for channel_id, users in user_groups.items():
            if str(channel_id) not in channels and not self.channel_exists(str(channel_id)):
                self.upsert_channel({"id": channel_id, "title": str(channel_id)})
            for user in users.values() if isinstance(users, dict) else users:
                if user.get("id") is not None:
                    self.upsert_user(str(channel_id), user)
                    imported_users += 1
        return {"channels": imported_channels, "messages": imported_messages, "users": imported_users}

    def channel_exists(self, channel_id: str) -> bool:
        with self.connection() as db:
            return db.execute("SELECT 1 FROM channels WHERE channel_id=?", (str(channel_id),)).fetchone() is not None

    def search_messages(self, text: Optional[str] = None, channel_id: Optional[str] = None,
                        date_from: Optional[str] = None, date_to: Optional[str] = None,
                        has_media: Optional[bool] = None, limit: int = 100) -> List[Dict[str, Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        if text:
            clauses.append("(m.text LIKE ? OR m.raw_text LIKE ?)")
            needle = f"%{text}%"
            params.extend([needle, needle])
        if channel_id:
            clauses.append("m.channel_id = ?")
            params.append(str(channel_id))
        if date_from:
            clauses.append("m.date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("m.date <= ?")
            params.append(date_to)
        if has_media is not None:
            clauses.append("m.has_media = ?")
            params.append(int(has_media))
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(max(1, min(limit, 1000)))
        with self.connection() as db:
            rows = db.execute(
                """SELECT m.*, c.title AS channel_title FROM messages m
                   LEFT JOIN channels c ON c.channel_id=m.channel_id""" +
                where + " ORDER BY datetime(m.date) DESC, m.message_id DESC LIMIT ?", params
            ).fetchall()
        return [dict(row) for row in rows]

    def summary(self) -> Dict[str, int]:
        with self.connection() as db:
            return {
                "channels": db.execute("SELECT COUNT(*) FROM channels").fetchone()[0],
                "messages": db.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
                "users": db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            }


def import_json_file(json_path: str | Path, sqlite_path: str | Path) -> Dict[str, int]:
    with Path(json_path).open("r", encoding="utf-8") as source:
        database = json.load(source)
    return StudioStore(sqlite_path).import_legacy_database(database)
