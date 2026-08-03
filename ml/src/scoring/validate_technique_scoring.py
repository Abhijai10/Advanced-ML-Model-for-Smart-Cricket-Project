"""Validation entry point for Phase 10 technique scoring artifacts."""

from __future__ import annotations

import sys

from technique_scoring import generate_phase10_artifacts


def main() -> int:
    health = generate_phase10_artifacts()
    if not health["validation_passed"]:
        print("FAIL: Phase 10 technique scoring validation failed.")
        return 1
    print("PASS: Phase 10 technique scoring artifacts are valid.")
    print(f"Templates created: {health['templates_created']}")
    print(f"Samples scored: {health['samples_scored']}")
    print(f"Report path: {health['output_files']['technique_score_report_json']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
