"""Transport-agnostic repost executor with idempotency and retry policy."""
from __future__ import annotations

import time
import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Set


class RetryableTransferError(Exception):
    def __init__(self, message: str, retry_after: float = 0.0):
        super().__init__(message)
        self.retry_after = retry_after


@dataclass
class TransferResult:
    key: str
    status: str
    attempts: int
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def execute_repost_plan(plan: Dict[str, Any], sender: Callable[[Dict[str, Any]], Any], *, approved: bool = False,
                        max_retries: int = 3, sleep: Callable[[float], None] = time.sleep,
                        completed_keys: Optional[Set[str]] = None) -> List[TransferResult]:
    if not approved:
        raise ValueError("يجب اعتماد خطة إعادة النشر قبل التنفيذ")
    if not isinstance(max_retries, int) or isinstance(max_retries, bool) or max_retries < 1:
        raise ValueError("عدد محاولات إعادة النشر يجب أن يكون عددًا صحيحًا موجبًا")
    completed_keys = set() if completed_keys is None else completed_keys
    results: List[TransferResult] = []
    for item in plan.get("items", []):
        key = f"{item['source_channel_id']}:{item['message_id']}->{item['destination_channel_id']}:{item.get('mode', 'copy')}"
        if key in completed_keys:
            results.append(TransferResult(key, "skipped_duplicate", 0))
            continue
        attempts = 0
        while attempts < max_retries:
            attempts += 1
            try:
                sender(item)
                completed_keys.add(key)
                results.append(TransferResult(key, "sent", attempts))
                break
            except RetryableTransferError as exc:
                if attempts >= max_retries:
                    results.append(TransferResult(key, "failed", attempts, str(exc)))
                    break
                try:
                    retry_after = float(exc.retry_after)
                except (TypeError, ValueError):
                    results.append(TransferResult(key, "failed", attempts, "مدة إعادة المحاولة غير صالحة"))
                    break
                if not math.isfinite(retry_after) or retry_after < 0:
                    results.append(TransferResult(key, "failed", attempts, "مدة إعادة المحاولة غير صالحة"))
                    break
                sleep(retry_after)
            except Exception as exc:
                results.append(TransferResult(key, "failed", attempts, str(exc)))
                break
    return results
