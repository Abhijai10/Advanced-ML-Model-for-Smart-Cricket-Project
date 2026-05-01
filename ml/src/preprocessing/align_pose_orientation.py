import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "ml" / "data" / "processed" / "pose_normalized"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "ml" / "data" / "processed" / "pose_aligned"

LEFT_SHOULDER_IDX = 11
RIGHT_SHOULDER_IDX = 12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Align normalized pose orientation using shoulder-line rotation."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Directory containing normalized pose JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write orientation-aligned pose JSON files.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.input_dir.exists() or not args.input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")


def list_json_files(input_dir: Path) -> List[Path]:
    return sorted(input_dir.glob("*.json"))


def is_numeric(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def has_numeric_xy(landmark: Any) -> bool:
    if not isinstance(landmark, dict):
        return False
    return (
        "x" in landmark
        and "y" in landmark
        and is_numeric(landmark["x"])
        and is_numeric(landmark["y"])
    )


def get_xy(landmark: Dict[str, Any]) -> Tuple[float, float]:
    return float(landmark["x"]), float(landmark["y"])


def rotate_xy(x: float, y: float, angle: float) -> Tuple[float, float]:
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    x_new = x * cos_a - y * sin_a
    y_new = x * sin_a + y * cos_a
    return x_new, y_new


def align_frame_landmarks(
    landmarks: List[Any],
) -> Tuple[List[Any], bool]:
    if len(landmarks) <= RIGHT_SHOULDER_IDX:
        return landmarks, False

    left_shoulder = landmarks[LEFT_SHOULDER_IDX]
    right_shoulder = landmarks[RIGHT_SHOULDER_IDX]
    if not has_numeric_xy(left_shoulder) or not has_numeric_xy(right_shoulder):
        return landmarks, False

    left_x, left_y = get_xy(left_shoulder)
    right_x, right_y = get_xy(right_shoulder)
    dx = right_x - left_x
    dy = right_y - left_y

    if not math.isfinite(dx) or not math.isfinite(dy):
        return landmarks, False

    angle = math.atan2(dy, dx)
    rotation_angle = -angle

    aligned_landmarks: List[Any] = []
    for landmark in landmarks:
        if not isinstance(landmark, dict):
            aligned_landmarks.append(landmark)
            continue

        aligned_landmark = dict(landmark)
        if has_numeric_xy(landmark):
            x, y = get_xy(landmark)
            x_new, y_new = rotate_xy(x, y, rotation_angle)
            aligned_landmark["x"] = x_new
            aligned_landmark["y"] = y_new
        # Keep z and visibility unchanged.
        aligned_landmarks.append(aligned_landmark)

    return aligned_landmarks, True


def align_one_file(input_path: Path, output_path: Path) -> Tuple[int, int]:
    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Top-level JSON must be an object.")

    frames = data.get("frames", [])
    if not isinstance(frames, list):
        frames = []

    aligned_frames: List[Any] = []
    warning_count = 0
    frames_processed = 0

    for frame_index, frame in enumerate(frames):
        frames_processed += 1

        if not isinstance(frame, dict):
            warning_count += 1
            print(f"WARNING [{input_path.name}] frame {frame_index}: invalid frame object; unchanged.")
            aligned_frames.append(frame)
            continue

        landmarks = frame.get("landmarks")
        if not isinstance(landmarks, list):
            warning_count += 1
            print(
                f"WARNING [{input_path.name}] frame {frame_index}: missing/invalid landmarks; unchanged."
            )
            aligned_frames.append(dict(frame))
            continue

        aligned_landmarks, success = align_frame_landmarks(landmarks)
        aligned_frame = dict(frame)
        aligned_frame["landmarks"] = aligned_landmarks
        aligned_frames.append(aligned_frame)

        if not success:
            warning_count += 1
            print(
                f"WARNING [{input_path.name}] frame {frame_index}: invalid shoulders; rotation skipped."
            )

    aligned_data = dict(data)
    aligned_data["frames"] = aligned_frames

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(aligned_data, f, indent=2)

    return frames_processed, warning_count


def main() -> None:
    args = parse_args()
    validate_args(args)

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    json_files = list_json_files(input_dir)
    if not json_files:
        print(f"No JSON files found in: {input_dir}")
        return

    total_files_processed = 0
    total_frames_processed = 0
    total_warnings = 0

    for input_path in json_files:
        output_path = output_dir / f"{input_path.stem}_aligned.json"
        frames_processed, warning_count = align_one_file(input_path, output_path)

        total_files_processed += 1
        total_frames_processed += frames_processed
        total_warnings += warning_count

        print(
            f"{input_path.name} | total frames processed: {frames_processed} | "
            f"warnings: {warning_count}"
        )

    print("\nAlignment summary")
    print(f"Total files processed : {total_files_processed}")
    print(f"Total frames processed: {total_frames_processed}")
    print(f"Total warnings        : {total_warnings}")


if __name__ == "__main__":
    main()
