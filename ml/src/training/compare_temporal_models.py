"""Print the saved Phase 8 temporal model comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--comparison",
        type=Path,
        default=Path("ml/artifacts/phase8/comparisons/model_comparison.json"),
    )
    args = parser.parse_args()
    with args.comparison.open(encoding="utf-8") as f:
        rows = json.load(f)
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
