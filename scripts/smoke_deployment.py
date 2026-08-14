#!/usr/bin/env python3
"""Smoke test a deployed Smart Cricket API without requiring a cricket fixture."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str


def _request_json(base_url: str, path: str, *, method: str = "GET", data: bytes | None = None) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"accept": "application/json", "content-type": "application/json", "x-request-id": "smoke-deployment"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8") or "{}"
            return int(response.status), json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8") or "{}"
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"raw": body[:200]}
        return int(exc.code), payload


def run_smoke(base_url: str) -> list[CheckResult]:
    results: list[CheckResult] = []

    health_code, health = _request_json(base_url, "/health")
    results.append(CheckResult("Health", "PASS" if health_code == 200 and health.get("status") == "ok" else "FAIL", f"HTTP {health_code}"))

    ready_code, ready = _request_json(base_url, "/ready")
    results.append(CheckResult("Readiness", "PASS" if ready_code == 200 and ready.get("status") == "ready" else "FAIL", f"HTTP {ready_code}"))

    capabilities_code, capabilities = _request_json(base_url, "/capabilities")
    capabilities_ok = capabilities_code == 200 and "api_version" in capabilities and "audio_signing_secret" not in capabilities
    results.append(CheckResult("Capabilities", "PASS" if capabilities_ok else "FAIL", f"HTTP {capabilities_code}"))

    error_code, error_payload = _request_json(base_url, "/analyze", method="POST", data=b"{}")
    detail = error_payload.get("detail")
    leaked = "Traceback" in json.dumps(error_payload) or "SUPABASE_SERVICE_ROLE_KEY" in json.dumps(error_payload)
    safe_error = error_code in {400, 422} and not leaked and detail is not None
    results.append(CheckResult("Safe error", "PASS" if safe_error else "FAIL", f"HTTP {error_code}"))

    version = health.get("version") or capabilities.get("api_version")
    results.append(CheckResult("Version metadata", "PASS" if version else "FAIL", str(version or "missing")))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Base URL of the deployed API, for example https://api.example.com")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON output.")
    args = parser.parse_args()

    results = run_smoke(args.base_url)
    if args.json:
        print(json.dumps([result.__dict__ for result in results], indent=2, sort_keys=True))
    else:
        print("Smart Cricket Deployment Smoke")
        print()
        for result in results:
            print(f"{result.name:.<24} {result.status}  {result.detail}")
    return 0 if all(result.status == "PASS" for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
