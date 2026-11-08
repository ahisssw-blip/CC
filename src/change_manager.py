"""Auditable change batches with review, partial execution and rollback."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from src.studio_store import StudioStore


class ChangeManager:
    def __init__(self, store: StudioStore):
        self.store = store
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.store.connection() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS change_batches(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, description TEXT DEFAULT '', status TEXT NOT NULL,
                created_at TEXT NOT NULL, scheduled_at TEXT, reviewed_at TEXT, executed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS change_items(
                id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id INTEGER NOT NULL,
                channel_id TEXT NOT NULL, message_id INTEGER NOT NULL,
                before_text TEXT NOT NULL, after_text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending', error TEXT, executed_at TEXT,
                FOREIGN KEY(batch_id) REFERENCES change_batches(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS message_versions(
                id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL, channel_id TEXT NOT NULL, message_id INTEGER NOT NULL,
                version_type TEXT NOT NULL, text TEXT NOT NULL, created_at TEXT NOT NULL,
                FOREIGN KEY(batch_id) REFERENCES change_batches(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_change_items_batch ON change_items(batch_id,status);
            """)

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def create_batch(self, name: str, description: str, items: Iterable[Dict[str, Any]], scheduled_at: Optional[str] = None) -> int:
        items = list(items)
        if not name.strip():
            raise ValueError("اسم الحزمة مطلوب")
        if not items:
            raise ValueError("لا يمكن إنشاء حزمة بلا عناصر")
        with self.store.connection() as db:
            cursor = db.execute(
                "INSERT INTO change_batches(name,description,status,created_at,scheduled_at) VALUES(?,?,?,?,?)",
                (name.strip(), description.strip(), "pending_review", self.now(), scheduled_at),
            )
            batch_id = int(cursor.lastrowid)
            for item in items:
                if item.get("before") == item.get("after"):
                    continue
                db.execute(
                    """INSERT INTO change_items(batch_id,channel_id,message_id,before_text,after_text,status)
                       VALUES(?,?,?,?,?,'pending')""",
                    (batch_id, str(item["channel_id"]), int(item["message_id"]), item.get("before", ""), item.get("after", "")),
                )
            count = db.execute("SELECT COUNT(*) FROM change_items WHERE batch_id=?", (batch_id,)).fetchone()[0]
            if not count:
                db.execute("DELETE FROM change_batches WHERE id=?", (batch_id,))
                raise ValueError("الحزمة لا تحتوي تغييرات فعلية")
        return batch_id

    def get_batch(self, batch_id: int) -> Dict[str, Any]:
        with self.store.connection() as db:
            batch = db.execute("SELECT * FROM change_batches WHERE id=?", (batch_id,)).fetchone()
            if not batch:
                raise ValueError("حزمة التغييرات غير موجودة")
            items = db.execute("SELECT * FROM change_items WHERE batch_id=? ORDER BY id", (batch_id,)).fetchall()
        result = dict(batch)
        result["items"] = [dict(item) for item in items]
        result["item_count"] = len(items)
        return result

    def list_batches(self) -> List[Dict[str, Any]]:
        with self.store.connection() as db:
            rows = db.execute("""SELECT b.*, COUNT(i.id) AS item_count
                FROM change_batches b LEFT JOIN change_items i ON i.batch_id=b.id
                GROUP BY b.id ORDER BY b.id DESC""").fetchall()
        return [dict(row) for row in rows]

    def approve_batch(self, batch_id: int) -> None:
        with self.store.connection() as db:
            changed = db.execute("UPDATE change_batches SET status='approved', reviewed_at=? WHERE id=? AND status='pending_review'", (self.now(), batch_id)).rowcount
            if not changed:
                raise ValueError("الحزمة ليست بانتظار المراجعة")

    def cancel_item(self, item_id: int) -> None:
        with self.store.connection() as db:
            changed = db.execute("UPDATE change_items SET status='cancelled' WHERE id=? AND status='pending'", (item_id,)).rowcount
            if not changed:
                raise ValueError("العنصر غير قابل للإلغاء في حالته الحالية")

    def execute_local(self, batch_id: int, batch_size: int = 50) -> Dict[str, Any]:
        if batch_size < 1:
            raise ValueError("حجم الدفعة يجب أن يكون موجبًا")
        with self.store.connection() as db:
            batch = db.execute("SELECT * FROM change_batches WHERE id=?", (batch_id,)).fetchone()
            if not batch or batch["status"] not in {"approved", "partially_applied"}:
                raise ValueError("يجب اعتماد الحزمة قبل التنفيذ")
            items = db.execute("SELECT * FROM change_items WHERE batch_id=? AND status='pending' ORDER BY id LIMIT ?", (batch_id, batch_size)).fetchall()
            applied = failed = 0
            for item in items:
                db.execute("SAVEPOINT apply_change_item")
                try:
                    updated = db.execute(
                        """UPDATE messages SET raw_text=?, text=?, updated_at=?
                           WHERE channel_id=? AND message_id=? AND COALESCE(raw_text,text,'')=?""",
                        (item["after_text"], item["after_text"], self.now(), item["channel_id"],
                         item["message_id"], item["before_text"]),
                    )
                    if updated.rowcount != 1:
                        raise ValueError("تغير نص الرسالة منذ إنشاء الخطة أو أن الرسالة غير موجودة")
                    db.execute("INSERT INTO message_versions(batch_id,item_id,channel_id,message_id,version_type,text,created_at) VALUES(?,?,?,?,?,?,?)",
                               (batch_id, item["id"], item["channel_id"], item["message_id"], "before", item["before_text"], self.now()))
                    db.execute("INSERT INTO message_versions(batch_id,item_id,channel_id,message_id,version_type,text,created_at) VALUES(?,?,?,?,?,?,?)",
                               (batch_id, item["id"], item["channel_id"], item["message_id"], "after", item["after_text"], self.now()))
                    db.execute("UPDATE change_items SET status='applied', executed_at=? WHERE id=?", (self.now(), item["id"]))
                    db.execute("RELEASE SAVEPOINT apply_change_item")
                    applied += 1
                except Exception as exc:
                    db.execute("ROLLBACK TO SAVEPOINT apply_change_item")
                    db.execute("RELEASE SAVEPOINT apply_change_item")
                    db.execute("UPDATE change_items SET status='failed', error=? WHERE id=?", (str(exc), item["id"]))
                    failed += 1
            pending = db.execute("SELECT COUNT(*) FROM change_items WHERE batch_id=? AND status='pending'", (batch_id,)).fetchone()[0]
            new_status = "partially_applied" if pending else ("failed" if failed and not applied else "completed")
            db.execute("UPDATE change_batches SET status=?, executed_at=? WHERE id=?", (new_status, self.now(), batch_id))
        return {"applied": applied, "failed": failed, "remaining": pending, "status": new_status}

    def rollback(self, batch_id: int) -> Dict[str, int]:
        with self.store.connection() as db:
            items = db.execute("SELECT * FROM change_items WHERE batch_id=? AND status='applied'", (batch_id,)).fetchall()
            restored = conflicts = 0
            for item in items:
                updated = db.execute(
                    """UPDATE messages SET raw_text=?, text=?, updated_at=?
                       WHERE channel_id=? AND message_id=? AND COALESCE(raw_text,text,'')=?""",
                    (item["before_text"], item["before_text"], self.now(), item["channel_id"],
                     item["message_id"], item["after_text"]),
                )
                if updated.rowcount == 1:
                    db.execute("UPDATE change_items SET status='rolled_back' WHERE id=?", (item["id"],))
                    restored += 1
                else:
                    db.execute("UPDATE change_items SET status='rollback_conflict', error=? WHERE id=?",
                               ("لم يُستعد النص لأن الرسالة تغيرت بعد تطبيق الحزمة", item["id"]))
                    conflicts += 1
            batch_status = "partially_rolled_back" if conflicts else "rolled_back"
            db.execute("UPDATE change_batches SET status=?, executed_at=? WHERE id=?", (batch_status, self.now(), batch_id))
        result = {"restored": restored}
        if conflicts:
            result["conflicts"] = conflicts
        return result

    def run_due_batches(self, now: Optional[str] = None, batch_size: int = 50) -> List[Dict[str, Any]]:
        """Run only approved batches whose local schedule has arrived."""
        current = now or self.now()
        with self.store.connection() as db:
            rows = db.execute(
                "SELECT id FROM change_batches WHERE status='approved' AND scheduled_at IS NOT NULL AND scheduled_at<=? ORDER BY scheduled_at",
                (current,),
            ).fetchall()
        return [{"batch_id": row["id"], **self.execute_local(row["id"], batch_size=batch_size)} for row in rows]

    async def execute_telegram(self, batch_id: int, gateway: Any, resolve_channel: Any, *, batch_size: int = 50) -> Dict[str, Any]:
        """Execute an approved batch on Telegram; local execution remains separate."""
        from src.telegram_operation_executor import execute_telegram_batch
        batch = self.get_batch(batch_id)
        result = await execute_telegram_batch(gateway, batch, resolve_channel, approved=True, batch_size=batch_size)
        with self.store.connection() as db:
            for item in result["results"]:
                status = "applied" if item["status"] == "applied" else ("failed" if item["status"] == "failed" else "cancelled")
                db.execute("UPDATE change_items SET status=?, error=?, executed_at=? WHERE id=?", (status, item.get("error"), self.now(), item["item_id"]))
            pending = db.execute("SELECT COUNT(*) FROM change_items WHERE batch_id=? AND status='pending'", (batch_id,)).fetchone()[0]
            failed = db.execute("SELECT COUNT(*) FROM change_items WHERE batch_id=? AND status='failed'", (batch_id,)).fetchone()[0]
            applied = db.execute("SELECT COUNT(*) FROM change_items WHERE batch_id=? AND status='applied'", (batch_id,)).fetchone()[0]
            status = "partially_applied" if pending or failed else ("completed" if applied else "failed")
            db.execute("UPDATE change_batches SET status=?, executed_at=? WHERE id=?", (status, self.now(), batch_id))
        result["status"] = status
        return result
