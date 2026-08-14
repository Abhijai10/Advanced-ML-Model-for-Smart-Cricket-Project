"""Deployment smoke script tests."""

from __future__ import annotations

import json
import unittest
from unittest.mock import Mock, patch

from scripts.smoke_deployment import run_smoke


class _Response:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class DeploymentSmokeTests(unittest.TestCase):
    def test_deployment_smoke_checks_core_endpoints(self) -> None:
        responses = [
            _Response({"status": "ok", "version": "phase13"}),
            _Response({"status": "ready"}),
            _Response({"api_version": "phase13", "auth_required": False}),
            _Response({"detail": [{"loc": ["body"], "msg": "missing"}]}, status=422),
        ]

        def fake_urlopen(request, timeout):
            response = responses.pop(0)
            if response.status >= 400:
                import urllib.error

                raise urllib.error.HTTPError(
                    request.full_url,
                    response.status,
                    "error",
                    hdrs={},
                    fp=Mock(read=response.read),
                )
            return response

        with patch("scripts.smoke_deployment.urllib.request.urlopen", side_effect=fake_urlopen):
            results = run_smoke("https://api.example.com")

        self.assertEqual([result.status for result in results], ["PASS", "PASS", "PASS", "PASS", "PASS"])


if __name__ == "__main__":
    unittest.main()
