import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from threading import Lock
from fastapi import HTTPException, Request


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1)
    return f"scrypt${salt}${key.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, salt, expected = encoded.split("$")
        actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


_buckets = defaultdict(deque)
_lock = Lock()


def rate_limit(request: Request, scope: str, limit: int, seconds: int = 60):
    # Single-process MVP; use a shared store before adding workers.
    key = (scope, request.client.host if request.client else "unknown")
    current = time.monotonic()
    with _lock:
        if len(_buckets) > 10000:
            for old_key in list(_buckets):
                if not _buckets[old_key] or current - _buckets[old_key][-1] > 3600:
                    del _buckets[old_key]
        bucket = _buckets[key]
        while bucket and bucket[0] <= current - seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(
                429,
                "Bạn thao tác quá nhanh. Vui lòng thử lại sau.",
                headers={"Retry-After": str(seconds)},
            )
        bucket.append(current)
