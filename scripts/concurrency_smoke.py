#!/usr/bin/env python3
"""Controlled concurrency smoke for Smart Cricket analysis capacity."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def _multipart_body(field_name: str, filename: str, content_type: str, payload: bytes) -> tuple[bytes, str]:
    boundary = f"smart-cricket-boundary-{int(time.time() * 1000)}"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            payload,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    return body, f"multipart/form-data; boundary={boundary}"


def _post_analysis(base_url: str, video_path: Path, timeout: int) -> dict:
    payload = video_path.read_bytes()
    body, content_type = _multipart_body("file", video_path.name, "video/mp4", payload)
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/analyze",
        data=body,
        method="POST",
        headers={"content-type": content_type, "x-request-id": f"concurrency-smoke-{time.time_ns()}"},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
            status = int(response.status)
    except urllib.error.HTTPError as exc:
        exc.read()
        status = int(exc.code)
    except Exception as exc:
        return {"status": "error", "error": type(exc).__name__, "duration_seconds": round(time.perf_counter() - started, 3)}
    return {"status": status, "duration_seconds": round(time.perf_counter() - started, 3)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="API base URL")
    parser.add_argument("video_path", type=Path, help="Short non-sensitive MP4 fixture")
    parser.add_argument("--workers", type=int, default=3, help="Concurrent requests to send")
    parser.add_argument("--timeout", type=int, default=120, help="Client timeout per request")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()
    if not args.video_path.is_file():
        raise SystemExit(f"video_path not found: {args.video_path}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        results = list(executor.map(lambda _: _post_analysis(args.base_url, args.video_path, args.timeout), range(args.workers)))

    statuses = [result.get("status") for result in results]
    overloaded = sum(1 for status in statuses if status in {429, 503})
    successful = sum(1 for status in statuses if status == 200)
    summary = {"requests": len(results), "successful": successful, "overloaded_or_busy": overloaded, "results": results}
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print("Smart Cricket Controlled Concurrency Smoke")
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if successful >= 1 or overloaded >= 1 else 1


if __name__ == "__main__":
    sys.exit(main())
