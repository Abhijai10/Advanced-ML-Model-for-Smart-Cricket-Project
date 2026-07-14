"""Evaluate a saved Phase 8 temporal model checkpoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from training.train_temporal_models import _final_test_evaluation, _load_json  # noqa: E402
from training.metrics import load_class_names  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path, help="Phase 8 experiment run directory.")
    args = parser.parse_args()

    run_dir = args.run_dir
    summary_path = run_dir / "run_summary.json"
    config_path = run_dir / "config.json"
    if not summary_path.exists() or not config_path.exists():
        raise FileNotFoundError("run_dir must contain run_summary.json and config.json")

    best_run = _load_json(summary_path)
    config = _load_json(config_path)
    class_names = load_class_names(config["label_mapping_path"])
    output_dir = run_dir.parents[1]
    metrics = _final_test_evaluation(best_run=best_run, output_dir=output_dir, class_names=class_names)
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
