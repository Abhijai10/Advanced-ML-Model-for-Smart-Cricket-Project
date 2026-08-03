"""CLI for running the Phase 12 offline Smart Cricket inference pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from inference.analysis_pipeline import analyze_sequence, load_dataset_sequence  # noqa: E402
from inference.inference_config import DEFAULT_SAMPLE_INDEX, SAMPLE_OUTPUT_PATH  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 12 offline inference.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--sample-index", type=int, default=None, help="Final temporal dataset sample index.")
    source.add_argument("--file-name", type=str, default=None, help="Final temporal dataset file_name.")
    source.add_argument("--sequence-npy", type=Path, default=None, help="Path to one [60,32] sequence .npy file.")
    parser.add_argument("--output", type=Path, default=SAMPLE_OUTPUT_PATH, help="Output JSON path.")
    args = parser.parse_args()

    if args.sequence_npy is not None:
        sequence = np.load(args.sequence_npy)
        metadata = {"file_name": args.sequence_npy.name, "true_label_name": "unknown", "input_path": str(args.sequence_npy)}
    else:
        sample_index = DEFAULT_SAMPLE_INDEX if args.sample_index is None and args.file_name is None else args.sample_index
        sequence, metadata = load_dataset_sequence(sample_index=sample_index, file_name=args.file_name)

    result = analyze_sequence(sequence, metadata)
    payload = result.to_dict()
    _write_json(args.output, payload)
    print("Phase 12 Offline Inference")
    print(f"predicted_shot: {payload['predicted_shot']}")
    print(f"shot_confidence: {payload['shot_confidence']:.4f}")
    print(f"technique_match_score: {payload['technique_match_score']:.4f}")
    print(f"detected_issues: {len(payload['detected_issues'])}")
    print(f"output_path: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
