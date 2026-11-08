"""Application services for Telegram Channel Studio.

This layer is deliberately split from Telethon and from the UI. It makes
previewable, auditable operations possible before any Telegram write occurs.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.studio_store import StudioStore
from src.content_quality import analyze_posts, issue_summary
from src.content_similarity import find_similar_posts
from src.natural_query import parse_arabic_query
from src.editor_engine import (
    DEFAULT_TEMPLATES, LayerConfig, Template, apply_layers, apply_template,
    archive_post, clean_post, prepare_republish, preview_change,
)
from src.bulk_editor import preview_bulk
from src.advanced_filters import filter_posts
from src.repost_queue import RepostItem, build_repost_plan
from src.audience_analytics import enrich_members, audience_overlap, snapshot_delta, campaign_signals
from src.editor_analytics import editorial_report


class StudioService:
    def __init__(self, store: StudioStore):
        self.store = store

    def list_channels(self) -> List[Dict[str, Any]]:
        with self.store.connection() as db:
            rows = db.execute(
                """SELECT c.*, COUNT(m.message_id) AS message_count
                   FROM channels c LEFT JOIN messages m ON m.channel_id=c.channel_id
                   GROUP BY c.channel_id ORDER BY c.title COLLATE NOCASE"""
            ).fetchall()
        return [dict(row) for row in rows]

    def search_posts(self, **filters: Any) -> List[Dict[str, Any]]:
        return self.store.search_messages(**filters)

    def all_posts(self, limit: int = 10000) -> List[Dict[str, Any]]:
        return self.store.search_messages(limit=limit)

    def quality_report(self, limit: int = 10000) -> Dict[str, Any]:
        issues = analyze_posts(self.all_posts(limit))
        return {"summary": issue_summary(issues), "total": len(issues), "items": [issue.as_dict() for issue in issues]}

    def similar_report(self, threshold: float = 0.82, limit: int = 10000) -> Dict[str, Any]:
        matches = find_similar_posts(self.all_posts(limit), threshold=threshold)
        return {"total": len(matches), "items": [match.as_dict() for match in matches]}

    def explain_query(self, query: str) -> Dict[str, Any]:
        return parse_arabic_query(query).as_dict()

    def editor_preview(self, operation: str, text: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        options = dict(options or {})
        if operation == "layers":
            updated = apply_layers(text, LayerConfig(**{key: value for key, value in options.items() if key in LayerConfig.__dataclass_fields__}))
        elif operation == "template":
            template = Template(options.get("name", "قالب مخصص"), options.get("body", "{{النص}}"))
            updated = apply_template(template, text, options.get("values", {}))
        elif operation == "clean":
            updated = clean_post(text, signature=options.get("signature", ""))
        elif operation == "archive":
            updated = archive_post(text, archive_tag=options.get("archive_tag", "#أرشيف"), date_text=options.get("date_text", ""), source_url=options.get("source_url", ""))
        elif operation == "republish":
            updated = prepare_republish(text, remove_phrase=options.get("remove_phrase", "عاجل"), introduction=options.get("introduction", ""), source_url=options.get("source_url", ""))
        else:
            raise ValueError("عملية التحرير غير معروفة")
        result = preview_change(text, updated)
        result["operation"] = operation
        return result

    def list_templates(self) -> List[Dict[str, str]]:
        return [{"name": template.name, "body": template.body, "description": template.description} for template in DEFAULT_TEMPLATES]

    def bulk_preview(self, posts: List[Dict[str, Any]], operation: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        results = preview_bulk(posts, operation, options)
        return {"total": len(results), "changed": sum(result.changed for result in results), "failed": sum(result.status == "failed" for result in results), "items": [result.as_dict() for result in results]}

    def advanced_filter(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        items = filter_posts(self.all_posts(), spec)
        return {"total": len(items), "items": items}

    def repost_plan(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        return build_repost_plan([RepostItem(**item) for item in items])

    def audience_report(self, members: List[Dict[str, Any]]) -> Dict[str, Any]:
        enriched = enrich_members(members)
        segments: Dict[str, int] = {}
        for member in enriched:
            segments[member["segment"]] = segments.get(member["segment"], 0) + 1
        return {"total": len(enriched), "segments": segments, "members": enriched}

    @staticmethod
    def audience_overlap(memberships: Dict[str, List[str]]) -> Dict[str, Any]:
        return audience_overlap(memberships)

    @staticmethod
    def audience_snapshot_delta(previous: Dict[str, int], current: Dict[str, int]) -> Dict[str, Any]:
        return snapshot_delta(previous, current)

    @staticmethod
    def campaign_signals(post_metrics: List[Dict[str, Any]], snapshots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return campaign_signals(post_metrics, snapshots)

    def audience_snapshots(self, channel_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        rows = self.store.list_audience_snapshots(channel_id, limit)
        return {"total": len(rows), "items": rows, "privacy_note": "السجل محلي ويعكس ما تم رصده منذ تشغيل البرنامج"}

    def editorial_analytics(self, limit: int = 10000) -> Dict[str, Any]:
        return editorial_report(self.all_posts(limit))

    def preview_replace(self, search: str, replace: str, *, channel_id: Optional[str] = None,
                        date_from: Optional[str] = None, date_to: Optional[str] = None,
                        case_sensitive: bool = False, limit: int = 1000) -> Dict[str, Any]:
        if not search:
            raise ValueError("نص البحث لا يمكن أن يكون فارغًا")
        rows = self.store.search_messages(text=search, channel_id=channel_id,
                                          date_from=date_from, date_to=date_to, limit=limit)
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(re.escape(search), flags)
        previews = []
        for row in rows:
            original = row.get("raw_text") or row.get("text") or ""
            updated, count = pattern.subn(replace, original)
            if count:
                previews.append({
                    "channel_id": row["channel_id"], "message_id": row["message_id"],
                    "channel_title": row.get("channel_title"), "date": row.get("date"),
                    "original": original, "updated": updated, "replacement_count": count,
                })
        return {"total": len(previews), "replacements": sum(p["replacement_count"] for p in previews), "items": previews}

    def create_replace_plan(self, preview: Dict[str, Any], search: str, replace: str) -> int:
        if not preview.get("items"):
            raise ValueError("لا توجد منشورات مطابقة لإنشاء حزمة")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.store.connection() as db:
            cursor = db.execute(
                "INSERT INTO operations(operation_type,status,created_at) VALUES(?,?,?)",
                ("bulk_replace", "planned", now),
            )
            operation_id = cursor.lastrowid
            for item in preview["items"]:
                db.execute(
                    """INSERT INTO operations(operation_type,channel_id,message_id,before_text,after_text,status,created_at)
                       VALUES(?,?,?,?,?,?,?)""",
                    (f"bulk_replace:{operation_id}", item["channel_id"], item["message_id"],
                     item["original"], item["updated"], "planned", now),
                )
        return int(operation_id)

    def list_operations(self) -> List[Dict[str, Any]]:
        with self.store.connection() as db:
            rows = db.execute(
                """SELECT operation_type, status, created_at, COUNT(*) AS item_count
                   FROM operations GROUP BY operation_type, status, created_at
                   ORDER BY id DESC"""
            ).fetchall()
        return [dict(row) for row in rows]

    def apply_local_plan(self, operation_id: int) -> Dict[str, int]:
        """Apply a plan to the local index only; Telegram writes come later."""
        prefix = f"bulk_replace:{operation_id}"
        with self.store.connection() as db:
            rows = db.execute(
                "SELECT channel_id,message_id,after_text,status FROM operations WHERE operation_type=?",
                (prefix,),
            ).fetchall()
            applied = 0
            for row in rows:
                if row["status"] != "planned":
                    continue
                db.execute(
                    "UPDATE messages SET raw_text=?, text=?, updated_at=? WHERE channel_id=? AND message_id=?",
                    (row["after_text"], row["after_text"], datetime.now(timezone.utc).isoformat(timespec="seconds"),
                     row["channel_id"], row["message_id"]),
                )
                db.execute(
                    "UPDATE operations SET status='local_applied' WHERE operation_type=? AND channel_id=? AND message_id=?",
                    (prefix, row["channel_id"], row["message_id"]),
                )
                applied += 1
            db.execute("UPDATE operations SET status='local_applied' WHERE operation_type=?", ("bulk_replace",))
        return {"applied": applied, "total": len(rows)}
