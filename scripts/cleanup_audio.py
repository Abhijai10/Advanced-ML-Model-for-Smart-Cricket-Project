"""Delete expired generated audio artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.api.audio import cleanup_expired_audio


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up expired Smart Cricket audio artifacts.")
    parser.add_argument("--dry-run", action="store_true", help="Report expired artifacts without deleting them.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    result = cleanup_expired_audio(dry_run=args.dry_run)
    payload = {
        "scanned": result.scanned,
        "expired": result.expired,
        "deleted": result.deleted,
        "failed": result.failed,
        "skipped": result.skipped,
        "dry_run": args.dry_run,
    }
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(
            " ".join(
                f"{key}={value}"
                for key, value in payload.items()
            )
        )
