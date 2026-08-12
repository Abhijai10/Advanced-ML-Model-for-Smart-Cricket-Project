"""Rate-limiting adapters and trusted client-key derivation."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Protocol

from fastapi import Request


class RateLimiter(Protocol):
    """Small contract shared by local and production limiter adapters."""

    backend_id: str

    def allow(self, *, key: str, limit: int, window_seconds: int = 60) -> bool:
        """Return whether a request is allowed for this key/window."""


@dataclass
class MemoryRateLimiter:
    """Single-process limiter for local development, tests, and one-worker demos."""

    buckets: dict[str, deque[float]]
    backend_id: str = "memory"

    def allow(self, *, key: str, limit: int, window_seconds: int = 60) -> bool:
        if limit <= 0:
            return True
        now = time.monotonic()
        bucket = self.buckets[key]
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


class RedisRateLimiter:
    """Optional Redis-backed limiter for multi-instance deployments.

    The adapter imports `redis` lazily so local/test installs do not require a
    Redis client dependency. Production deployments that set
    `SMART_CRICKET_RATE_LIMIT_BACKEND=redis` must install and configure it.
    """

    backend_id = "redis"

    def __init__(self, *, redis_url: str | None, namespace: str = "smart-cricket") -> None:
        if not redis_url:
            raise RuntimeError("SMART_CRICKET_REDIS_URL is required when rate-limit backend is redis.")
        try:
            import redis  # type: ignore[import-not-found]
        except Exception as exc:
            raise RuntimeError("Install the optional redis package to use Redis rate limiting.") from exc
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._namespace = namespace

    def allow(self, *, key: str, limit: int, window_seconds: int = 60) -> bool:
        if limit <= 0:
            return True
        window = int(time.time() // window_seconds)
        redis_key = f"{self._namespace}:rate-limit:{key}:{window}"
        count = int(self._client.incr(redis_key))
        if count == 1:
            self._client.expire(redis_key, window_seconds + 5)
        return count <= limit


def client_ip_from_request(request: Request, *, trusted_proxy_hops: int) -> str:
    """Derive a client IP without trusting spoofed forwarding headers by default."""
    direct_host = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded or trusted_proxy_hops <= 0:
        return direct_host
    chain = [part.strip() for part in forwarded.split(",") if part.strip()]
    if len(chain) <= trusted_proxy_hops:
        return direct_host
    return chain[-(trusted_proxy_hops + 1)]


def request_rate_key(request: Request, *, scope: str, trusted_proxy_hops: int) -> str:
    """Build a limiter key using authenticated user state when already available."""
    auth = getattr(request.state, "auth", None)
    user_id = getattr(auth, "user_id", None)
    if user_id:
        return f"{scope}:user:{user_id}"
    return f"{scope}:ip:{client_ip_from_request(request, trusted_proxy_hops=trusted_proxy_hops)}"


def memory_buckets() -> dict[str, deque[float]]:
    """Factory used by services/tests to keep bucket state explicit."""
    return defaultdict(deque)
