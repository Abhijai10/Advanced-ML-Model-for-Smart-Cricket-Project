import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "ml" / "data" / "processed" / "pose_json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "ml" / "data" / "processed" / "pose_cleaned"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Light cleaning for pose JSON files by removing only clearly bad frames."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Directory containing original pose JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write cleaned pose JSON files.",
    )
    parser.add_argument(
        "--visibility-threshold",
        type=float,
        default=0.3,
        help="Remove frame if average landmark visibility is below this value.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.input_dir.exists() or not args.input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")
    if args.visibility_threshold < 0.0 or args.visibility_threshold > 1.0:
        raise ValueError("--visibility-threshold must be between 0.0 and 1.0.")


def list_json_files(input_dir: Path) -> List[Path]:
    return sorted(input_dir.glob("*.json"))


def average_visibility(landmarks: List[Dict[str, Any]]) -> float:
    if not landmarks:
        return 0.0
    visibility_values: List[float] = []
    for landmark in landmarks:
        if not isinstance(landmark, dict):
            visibility_values.append(0.0)
            continue
        raw_visibility = landmark.get("visibility", 0.0)
        try:
            visibility_values.append(float(raw_visibility))
        except (TypeError, ValueError):
            visibility_values.append(0.0)
    return sum(visibility_values) / len(visibility_values)


def should_remove_frame(frame: Dict[str, Any], visibility_threshold: float) -> bool:
    landmarks = frame.get("landmarks")
    if not isinstance(landmarks, list):
        return True
    if len(landmarks) == 0:
        return True
    return average_visibility(landmarks) < visibility_threshold


def clean_one_file(
    input_path: Path,
    output_path: Path,
    visibility_threshold: float,
) -> Tuple[int, int, int]:
    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Top-level JSON must be an object.")

    original_frames = data.get("frames", [])
    if not isinstance(original_frames, list):
        original_frames = []

    cleaned_frames: List[Dict[str, Any]] = []
    removed_count = 0

    for frame in original_frames:
        if not isinstance(frame, dict):
            removed_count += 1
            continue
        if should_remove_frame(frame, visibility_threshold):
            removed_count += 1
            continue
        cleaned_frames.append(frame)

    cleaned_data = dict(data)
    cleaned_data["frames"] = cleaned_frames

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, indent=2)

    original_count = len(original_frames)
    cleaned_count = len(cleaned_frames)
    return original_count, removed_count, cleaned_count


def main() -> None:
    args = parse_args()
    validate_args(args)

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    visibility_threshold = args.visibility_threshold

    json_files = list_json_files(input_dir)
    if not json_files:
        print(f"No JSON files found in: {input_dir}")
        return

    total_files_processed = 0
    total_frames_before = 0
    total_frames_after = 0
    total_frames_removed = 0

    for input_path in json_files:
        output_path = output_dir / input_path.name
        original_count, removed_count, cleaned_count = clean_one_file(
            input_path=input_path,
            output_path=output_path,
            visibility_threshold=visibility_threshold,
        )

        total_files_processed += 1
        total_frames_before += original_count
        total_frames_after += cleaned_count
        total_frames_removed += removed_count

        print(
            f"{input_path.name} | original: {original_count} | "
            f"removed: {removed_count} | cleaned: {cleaned_count}"
        )

    print("\nCleaning summary")
    print(f"Total files processed : {total_files_processed}")
    print(f"Total frames before   : {total_frames_before}")
    print(f"Total frames after    : {total_frames_after}")
    print(f"Total removed frames  : {total_frames_removed}")


if __name__ == "__main__":
    main()
