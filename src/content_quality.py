"""Deterministic content-quality checks for Telegram posts."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Dict, Iterable, List
from urllib.parse import urlparse

URL_RE = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)
HASHTAG_RE = re.compile(r"#[\w\u0600-\u06ff]+")


@dataclass(frozen=True)
class ContentIssue:
    code: str
    severity: str
    message: str
    channel_id: str
    message_id: int

    def as_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def extract_urls(text: str) -> List[str]:
    return URL_RE.findall(text or "")


def valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def normalize_text(text: str) -> str:
    text = "\n".join(line.strip() for line in (text or "").splitlines())
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def analyze_posts(posts: Iterable[Dict[str, Any]], *, short_limit: int = 20) -> List[ContentIssue]:
    issues: List[ContentIssue] = []
    seen: Dict[str, tuple[str, int]] = {}
    for post in posts:
        channel_id = str(post.get("channel_id", ""))
        message_id = int(post.get("message_id", post.get("id", 0)))
        text = post.get("raw_text") or post.get("text") or ""
        fingerprint = sha256(normalize_text(text).casefold().encode("utf-8")).hexdigest() if text else ""
        if fingerprint and fingerprint in seen:
            old_channel, old_message = seen[fingerprint]
            issues.append(ContentIssue("duplicate_text", "warning", f"مطابق للمنشور {old_message} في القناة {old_channel}", channel_id, message_id))
        elif fingerprint:
            seen[fingerprint] = (channel_id, message_id)
        urls = extract_urls(text)
        for url in urls:
            if not valid_url(url):
                issues.append(ContentIssue("invalid_url", "error", f"رابط غير صالح: {url}", channel_id, message_id))
        hashtags = [tag.casefold() for tag in HASHTAG_RE.findall(text)]
        duplicates = [tag for tag, count in Counter(hashtags).items() if count > 1]
        if duplicates:
            issues.append(ContentIssue("duplicate_hashtag", "warning", f"وسم مكرر: {', '.join(duplicates)}", channel_id, message_id))
        if text and len(text.strip()) < short_limit:
            issues.append(ContentIssue("short_text", "info", "النص قصير بشكل غير معتاد", channel_id, message_id))
        if post.get("has_media") and not post.get("media_type"):
            issues.append(ContentIssue("missing_media_metadata", "warning", "منشور وسائط بلا نوع وسائط محفوظ", channel_id, message_id))
        if post.get("media_file_path") and post.get("media_file_path") == "missing":
            issues.append(ContentIssue("missing_media_file", "error", "ملف الوسائط غير موجود محليًا", channel_id, message_id))
    return issues


def issue_summary(issues: Iterable[ContentIssue]) -> Dict[str, int]:
    return dict(Counter(issue.code for issue in issues))
