"""Validation entry point for Phase 11 feedback artifacts."""

from __future__ import annotations

import sys

from feedback_engine import generate_phase11_artifacts


def main() -> int:
    health = generate_phase11_artifacts()
    if not health["validation_passed"]:
        print("FAIL: Phase 11 feedback validation failed.")
        return 1
    print("PASS: Phase 11 feedback artifacts are valid.")
    print(f"Samples processed: {health['samples_processed']}")
    print(f"Detected issues: {health['detected_issue_count']}")
    print(f"Sample output path: {health['output_files']['sample_feedback_outputs']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
