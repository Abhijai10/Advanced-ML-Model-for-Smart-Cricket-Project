"""Tests for rate-limit keying and adapter behavior."""

from __future__ import annotations

import unittest
from collections import defaultdict, deque
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from backend.api import services
from backend.api.rate_limit import MemoryRateLimiter, client_ip_from_request, request_rate_key


def _request(*, host: str = "10.0.0.10", forwarded: str | None = None, user_id: str | None = None):
    headers = {}
    if forwarded:
        headers["x-forwarded-for"] = forwarded
    auth = SimpleNamespace(user_id=user_id) if user_id else None
    return SimpleNamespace(
        client=SimpleNamespace(host=host),
        headers=headers,
        state=SimpleNamespace(request_id="request-1", auth=auth),
    )


class RateLimitTests(unittest.TestCase):
    def test_client_ip_ignores_forwarded_for_without_trusted_proxy(self) -> None:
        request = _request(host="10.0.0.10", forwarded="1.1.1.1, 2.2.2.2")
        self.assertEqual(client_ip_from_request(request, trusted_proxy_hops=0), "10.0.0.10")

    def test_client_ip_uses_address_before_trusted_proxy_chain(self) -> None:
        request = _request(host="10.0.0.10", forwarded="1.1.1.1, 2.2.2.2, 3.3.3.3")
        self.assertEqual(client_ip_from_request(request, trusted_proxy_hops=1), "2.2.2.2")
        self.assertEqual(client_ip_from_request(request, trusted_proxy_hops=2), "1.1.1.1")

    def test_client_ip_falls_back_when_chain_is_too_short(self) -> None:
        request = _request(host="10.0.0.10", forwarded="1.1.1.1")
        self.assertEqual(client_ip_from_request(request, trusted_proxy_hops=1), "10.0.0.10")

    def test_request_rate_key_prefers_authenticated_user_when_available(self) -> None:
        request = _request(host="10.0.0.10", forwarded="1.1.1.1, 2.2.2.2", user_id="user-1")
        self.assertEqual(request_rate_key(request, scope="feedback", trusted_proxy_hops=1), "feedback:user:user-1")

    def test_memory_rate_limiter_blocks_after_limit(self) -> None:
        limiter = MemoryRateLimiter(defaultdict(deque))
        self.assertTrue(limiter.allow(key="analysis:ip:1.1.1.1", limit=2))
        self.assertTrue(limiter.allow(key="analysis:ip:1.1.1.1", limit=2))
        self.assertFalse(limiter.allow(key="analysis:ip:1.1.1.1", limit=2))

    def test_redis_backend_without_url_returns_503(self) -> None:
        settings = SimpleNamespace(rate_limit_backend="redis", redis_url=None, trusted_proxy_hops=0)
        with patch("backend.api.services.SETTINGS", settings):
            with self.assertRaises(HTTPException) as ctx:
                services._enforce_limit(
                    request=_request(),
                    scope="analysis",
                    limit=1,
                    message="limited",
                )
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.detail["error_code"], "rate_limit_backend_unavailable")

    def test_production_readiness_rejects_memory_backend(self) -> None:
        settings = SimpleNamespace(environment="production", rate_limit_backend="memory", redis_url=None)
        with patch("backend.api.services.SETTINGS", settings):
            self.assertFalse(services._rate_limit_config_ready())
            self.assertIn("memory limiter is local only", services._rate_limit_config_detail())

    def test_production_readiness_accepts_gateway_backend(self) -> None:
        settings = SimpleNamespace(environment="production", rate_limit_backend="gateway", redis_url=None)
        with patch("backend.api.services.SETTINGS", settings):
            self.assertTrue(services._rate_limit_config_ready())
            self.assertIn("gateway", services._rate_limit_config_detail())


if __name__ == "__main__":
    unittest.main()
