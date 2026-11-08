"""Small local API for the Arabic Studio UI.

It is intentionally local-only. Telegram credentials and session files never
cross this HTTP boundary.
"""
from __future__ import annotations

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.studio_service import StudioService
from src.studio_store import StudioStore
from src.change_manager import ChangeManager

DB_PATH = Path(os.getenv("STUDIO_DB", "temp/studio.sqlite3"))
SERVICE = StudioService(StudioStore(DB_PATH))
CHANGES = ChangeManager(SERVICE.store)
LOGGER = logging.getLogger(__name__)
MAX_REQUEST_BYTES = 1_048_576


class StudioAPIHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:8765")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send(204, {})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/api/health":
                self._send(200, {"ok": True, "summary": SERVICE.store.summary()})
            elif parsed.path == "/api/channels":
                self._send(200, {"items": SERVICE.list_channels()})
            elif parsed.path == "/api/posts":
                self._send(200, {"items": SERVICE.search_posts(
                    text=query.get("text", [None])[0], channel_id=query.get("channel", [None])[0],
                    date_from=query.get("from", [None])[0], date_to=query.get("to", [None])[0],
                    limit=int(query.get("limit", [100])[0]),
                )})
            elif parsed.path == "/api/operations":
                self._send(200, {"items": SERVICE.list_operations()})
            elif parsed.path == "/api/audit":
                self._send(200, SERVICE.quality_report())
            elif parsed.path == "/api/similar":
                threshold = float(query.get("threshold", [0.82])[0])
                self._send(200, SERVICE.similar_report(threshold=threshold))
            elif parsed.path == "/api/query":
                self._send(200, SERVICE.explain_query(query.get("q", [""])[0]))
            elif parsed.path == "/api/templates":
                self._send(200, {"items": SERVICE.list_templates()})
            elif parsed.path == "/api/advanced-filter":
                spec = {key: value[0] for key, value in query.items()}
                for key in ("has_media", "has_url", "has_hashtag", "modified"):
                    if key in spec:
                        spec[key] = spec[key].lower() == "true"
                for key in ("min_views", "max_views", "low_performance_below"):
                    if key in spec:
                        spec[key] = int(spec[key])
                self._send(200, SERVICE.advanced_filter(spec))
            elif parsed.path == "/api/audience/snapshots":
                self._send(200, SERVICE.audience_snapshots(query.get("channel", [None])[0], int(query.get("limit", [100])[0])))
            elif parsed.path == "/api/analytics/editorial":
                self._send(200, SERVICE.editorial_analytics(int(query.get("limit", [10000])[0])))
            elif parsed.path == "/api/batches":
                self._send(200, {"items": CHANGES.list_batches()})
            elif parsed.path.startswith("/api/batches/"):
                batch_id = int(parsed.path.split("/")[3])
                self._send(200, CHANGES.get_batch(batch_id))
            else:
                self._send(404, {"error": "المسار غير موجود"})
        except Exception as exc:
            LOGGER.exception("GET request failed for %s", parsed.path)
            self._send(500, {"error": "تعذر تنفيذ الطلب. راجع سجل الخادم للمزيد من المعلومات."})

    def do_POST(self) -> None:
        parsed_path = urlparse(self.path).path
        allowed = {"/api/operations/replace/preview", "/api/operations/replace/plan", "/api/editor/preview", "/api/batches", "/api/bulk/preview", "/api/repost/plan", "/api/audience/report", "/api/audience/overlap", "/api/audience/snapshot-delta"}
        if parsed_path not in allowed and not parsed_path.startswith("/api/batches/"):
            self._send(404, {"error": "المسار غير موجود"})
            return
        try:
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                self._send(411, {"error": "يجب تحديد حجم الطلب"})
                return
            length = int(raw_length)
            if length < 0:
                self._send(400, {"error": "حجم الطلب غير صالح"})
                return
            if length > MAX_REQUEST_BYTES:
                self._send(413, {"error": "حجم الطلب أكبر من الحد المسموح (1 ميغابايت)"})
                return
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/json":
                self._send(415, {"error": "نوع المحتوى المطلوب هو application/json"})
                return
            data = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(data, dict):
                self._send(400, {"error": "يجب أن يكون جسم الطلب كائن JSON"})
                return
            if parsed_path == "/api/editor/preview":
                self._send(200, SERVICE.editor_preview(data.get("operation", ""), data.get("text", ""), data.get("options", {})))
                return
            if parsed_path == "/api/bulk/preview":
                self._send(200, SERVICE.bulk_preview(data.get("posts", []), data.get("operation", ""), data.get("options", {})))
                return
            if parsed_path == "/api/repost/plan":
                self._send(200, SERVICE.repost_plan(data.get("items", [])))
                return
            if parsed_path in {"/api/operations/replace/preview", "/api/operations/replace/plan"}:
                preview = SERVICE.preview_replace(
                    data.get("search", ""), data.get("replace", ""),
                    channel_id=data.get("channel_id"), date_from=data.get("date_from"),
                    date_to=data.get("date_to"), case_sensitive=bool(data.get("case_sensitive")),
                )
                if parsed_path.endswith("/plan"):
                    preview["operation_id"] = SERVICE.create_replace_plan(
                        preview, data.get("search", ""), data.get("replace", "")
                    )
                self._send(200, preview)
                return
            if parsed_path == "/api/audience/report":
                self._send(200, SERVICE.audience_report(data.get("members", [])))
                return
            if parsed_path == "/api/audience/overlap":
                self._send(200, SERVICE.audience_overlap(data.get("memberships", {})))
                return
            if parsed_path == "/api/audience/snapshot-delta":
                self._send(200, SERVICE.audience_snapshot_delta(data.get("previous", {}), data.get("current", {})))
                return
            if parsed_path == "/api/batches":
                batch_id = CHANGES.create_batch(data.get("name", ""), data.get("description", ""), data.get("items", []), data.get("scheduled_at"))
                self._send(201, CHANGES.get_batch(batch_id))
                return
            parts = parsed_path.split("/")
            batch_id = int(parts[3])
            action = parts[4] if len(parts) > 4 else ""
            if action == "approve":
                CHANGES.approve_batch(batch_id)
                self._send(200, CHANGES.get_batch(batch_id))
            elif action == "execute":
                self._send(200, CHANGES.execute_local(batch_id, int(data.get("batch_size", 50))))
            elif action == "rollback":
                self._send(200, CHANGES.rollback(batch_id))
            elif action == "cancel-item":
                CHANGES.cancel_item(int(data["item_id"]))
                self._send(200, CHANGES.get_batch(batch_id))
            else:
                self._send(404, {"error": "عملية الحزمة غير موجودة"})
            return
        except ValueError as exc:
            LOGGER.info("Invalid POST request for %s: %s", parsed_path, exc)
            self._send(400, {"error": "المدخلات غير صالحة؛ راجع الحقول المطلوبة وقيمها."})
        except Exception as exc:
            LOGGER.exception("POST request failed for %s", parsed_path)
            self._send(500, {"error": "تعذر تنفيذ الطلب. لم تُعرض تفاصيل داخلية حفاظًا على الأمان."})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8766), StudioAPIHandler)
    print(f"واجهة Studio المحلية على http://127.0.0.1:8766 — قاعدة البيانات: {DB_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
