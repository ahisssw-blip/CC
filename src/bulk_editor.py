"""Deterministic bulk editing operations with per-post previews and errors."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from src.editor_engine import clean_post, normalize_hashtags


@dataclass
class BulkResult:
    channel_id: str
    message_id: int
    before: str
    after: str = ""
    changed: bool = False
    status: str = "previewed"
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def transform_text(text: str, operation: str, options: Dict[str, Any]) -> str:
    if operation == "replace":
        search = str(options.get("search", ""))
        if not search:
            raise ValueError("نص البحث مطلوب")
        return text.replace(search, str(options.get("replace", "")))
    if operation == "delete":
        phrase = str(options.get("phrase", ""))
        if not phrase:
            raise ValueError("النص المراد حذفه مطلوب")
        return text.replace(phrase, "")
    if operation == "prepend":
        return str(options.get("prefix", "")).strip() + "\n\n" + text if options.get("prefix", "").strip() else text
    if operation == "append_hashtag":
        tags = normalize_hashtags(options.get("hashtags", []))
        return text.rstrip() + ("\n\n" + " ".join(tags) if tags else "")
    if operation == "replace_url":
        old = str(options.get("old_url", ""))
        new = str(options.get("new_url", ""))
        if not old:
            raise ValueError("الرابط القديم مطلوب")
        return text.replace(old, new)
    if operation == "remove_short_links":
        return re.sub(r"https?://(?:bit\.ly|t\.co|tinyurl\.com)/\S+", "", text, flags=re.IGNORECASE).strip()
    if operation == "normalize_punctuation":
        return re.sub(r"[!！]{2,}", "!", re.sub(r"[؟?]{2,}", "؟", text))
    if operation == "signature":
        signature = str(options.get("signature", "")).strip()
        return text.rstrip() + ("\n\n" + signature if signature else "")
    if operation == "date_format":
        return re.sub(r"(\d{4})[-/]([01]\d)[-/]([0-3]\d)", r"\3/\2/\1", text)
    if operation == "remove_emoji":
        return re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", str(options.get("replacement", "")), text)
    if operation == "clean":
        return clean_post(text, signature=str(options.get("signature", "")))
    raise ValueError("عملية جماعية غير معروفة")


def preview_bulk(posts: Iterable[Dict[str, Any]], operation: str, options: Optional[Dict[str, Any]] = None) -> List[BulkResult]:
    options = dict(options or {})
    results = []
    for post in posts:
        before = post.get("raw_text") or post.get("text") or ""
        try:
            after = transform_text(before, operation, options)
            results.append(BulkResult(str(post.get("channel_id", "")), int(post.get("message_id", post.get("id", 0))), before, after, before != after))
        except Exception as exc:
            results.append(BulkResult(str(post.get("channel_id", "")), int(post.get("message_id", post.get("id", 0))), before, before, False, "failed", str(exc)))
    return results
