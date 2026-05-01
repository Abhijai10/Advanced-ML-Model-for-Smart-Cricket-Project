import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "ml" / "data" / "processed" / "pose_aligned"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "ml" / "data" / "processed" / "pose_sequences"
TARGET_SEQUENCE_LENGTH = 60


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert aligned pose JSON files to fixed-length sequences."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Directory containing aligned pose JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write fixed-length pose sequence JSON files.",
    )
    parser.add_argument(
        "--target-length",
        type=int,
        default=TARGET_SEQUENCE_LENGTH,
        help="Target number of frames per output sequence.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.input_dir.exists() or not args.input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")
    if args.target_length < 1:
        raise ValueError("--target-length must be >= 1.")


def list_json_files(input_dir: Path) -> List[Path]:
    return sorted(input_dir.glob("*.json"))


def build_output_name(input_path: Path) -> str:
    stem = input_path.stem
    suffix_to_strip = "_normalized_aligned"
    if stem.endswith(suffix_to_strip):
        stem = stem[: -len(suffix_to_strip)]
    return f"{stem}_sequence.json"


def compute_resample_indices(original_len: int, target_len: int) -> List[int]:
    if original_len == target_len:
        return list(range(original_len))
    if target_len == 1:
        return [0]

    indices: List[int] = []
    for i in range(target_len):
        position = i * (original_len - 1) / (target_len - 1)
        idx = int(math.floor(position))
        indices.append(idx)
    return indices


def resample_frames(frames: List[Any], target_len: int) -> List[Any]:
    if not frames:
        return []
    indices = compute_resample_indices(len(frames), target_len)
    return [frames[idx] for idx in indices]


def prepare_one_file(input_path: Path, output_path: Path, target_len: int) -> Dict[str, int]:
    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Top-level JSON must be an object.")

    frames = data.get("frames", [])
    if not isinstance(frames, list):
        frames = []

    original_len = len(frames)
    prepared_frames = resample_frames(frames, target_len)

    if original_len > 0 and len(prepared_frames) != target_len:
        raise RuntimeError("Resampling failed to create the target sequence length.")

    output_data = dict(data)
    output_data["frames"] = prepared_frames

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    return {
        "original_len": original_len,
        "final_len": len(prepared_frames),
    }


def main() -> None:
    args = parse_args()
    validate_args(args)

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    target_len = args.target_length

    json_files = list_json_files(input_dir)
    if not json_files:
        print(f"No JSON files found in: {input_dir}")
        return

    total_files_processed = 0
    total_sequences_created = 0
    all_sequences_correct_length = True

    for input_path in json_files:
        output_name = build_output_name(input_path)
        output_path = output_dir / output_name

        lengths = prepare_one_file(input_path, output_path, target_len)
        original_len = lengths["original_len"]
        final_len = lengths["final_len"]

        total_files_processed += 1
        if final_len == target_len:
            total_sequences_created += 1
        else:
            all_sequences_correct_length = False

        print(
            f"{input_path.name} | original frames: {original_len} | final frames: {final_len}"
        )

    print("\nSequence preparation summary")
    print(f"Total files processed      : {total_files_processed}")
    print(f"Total sequences created    : {total_sequences_created}")
    print(f"All sequences length = {target_len}: {all_sequences_correct_length}")


if __name__ == "__main__":
    main()
