"""Explainable Arabic query parsing for the first Studio search experience."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SearchIntent:
    text: Optional[str] = None
    channel_name: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    must_have_media: Optional[bool] = None
    must_have_url: Optional[bool] = None
    keywords: List[str] = field(default_factory=list)
    explanation: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def parse_arabic_query(query: str) -> SearchIntent:
    original = query.strip()
    intent = SearchIntent()
    channel = re.search(r"قناة\s+([^\s،]+)", original)
    if channel:
        intent.channel_name = channel.group(1)
        intent.explanation.append(f"القناة: {intent.channel_name}")
    if re.search(r"لا\s+تحتوي\s+على\s+(صورة|وسائط|فيديو)", original):
        intent.must_have_media = False
        intent.explanation.append("استبعاد المنشورات التي تحتوي وسائط")
    elif re.search(r"تحتوي\s+على\s+(صورة|وسائط|فيديو)", original):
        intent.must_have_media = True
        intent.explanation.append("اشتراط وجود وسائط")
    if re.search(r"رابط|روابط|يوتيوب|لينك", original, re.IGNORECASE):
        intent.must_have_url = True
        intent.explanation.append("اشتراط وجود رابط")
    quoted = re.findall(r"[“\"]([^”\"]+)[”\"]", original)
    if quoted:
        intent.text = quoted[0]
        intent.explanation.append(f"النص: {intent.text}")
    else:
        common = {"أرني", "اعرض", "منشورات", "المنشورات", "التي", "في", "بين", "من", "إلى", "على", "تحتوي", "بدون", "لم", "يتم", "تعديلها"}
        intent.keywords = [word for word in re.findall(r"[\w\u0600-\u06ff]+", original) if word not in common and len(word) > 2]
        if intent.keywords:
            intent.text = " ".join(intent.keywords[:4])
            intent.explanation.append(f"كلمات البحث: {intent.text}")
    if not intent.explanation:
        intent.explanation.append("بحث عام يحتاج إلى تضييق بالفلاتر")
    return intent
