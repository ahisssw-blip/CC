from pathlib import Path
import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import studio_api


def test_ui_contains_core_arabic_workflows():
    html = Path('ui/index.html').read_text()
    js = Path('ui/app.js').read_text()
    for label in ('مختبر المنشور', 'مختبر التحرير الجماعي', 'من جمهوري الحقيقي؟'):
        assert label in html
    for function_name in ('renderPosts', 'openEditor', 'previewBulk', 'loadAudiencePanel'):
        assert f'function {function_name}' in js


def test_bulk_preview_escapes_ids_and_is_bound_to_current_inputs():
    js = Path('ui/app.js').read_text()
    assert 'escapeHtml(item.message_id)' in js
    assert 'lastBulkPreviewSignature!==JSON.stringify(currentBulkPayload())' in js
    assert 'JSON.stringify(currentBulkPayload())!==signature' in js


def test_api_rejects_oversized_body():
    server = ThreadingHTTPServer(('127.0.0.1', 0), studio_api.StudioAPIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = Request(
            f'http://127.0.0.1:{server.server_port}/api/audience/report',
            data=b' ' * (studio_api.MAX_REQUEST_BYTES + 1),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            urlopen(request)
            assert False, 'Expected HTTP 413'
        except HTTPError as error:
            assert error.code == 413
            assert 'details' not in json.loads(error.read())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_api_does_not_return_internal_exception_details(monkeypatch):
    class BrokenService:
        def quality_report(self):
            raise RuntimeError('private path /home/user/private-secret')

    monkeypatch.setattr(studio_api, 'SERVICE', BrokenService())
    server = ThreadingHTTPServer(('127.0.0.1', 0), studio_api.StudioAPIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        try:
            urlopen(f'http://127.0.0.1:{server.server_port}/api/audit')
            assert False, 'Expected HTTP 500'
        except HTTPError as error:
            payload = error.read().decode('utf-8')
            assert error.code == 500
            assert 'private-secret' not in payload
            assert 'details' not in payload
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
