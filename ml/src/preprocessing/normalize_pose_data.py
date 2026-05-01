import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "ml" / "data" / "processed" / "pose_cleaned"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "ml" / "data" / "processed" / "pose_normalized"

LEFT_SHOULDER_IDX = 11
RIGHT_SHOULDER_IDX = 12
LEFT_HIP_IDX = 23
RIGHT_HIP_IDX = 24


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize cleaned pose JSON files using hip-centered torso scaling."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Directory containing cleaned pose JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write normalized pose JSON files.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.input_dir.exists() or not args.input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")


def list_json_files(input_dir: Path) -> List[Path]:
    return sorted(input_dir.glob("*.json"))


def get_numeric_xyz(landmark: Dict[str, Any]) -> Tuple[float, float, float]:
    return float(landmark["x"]), float(landmark["y"]), float(landmark["z"])


def get_midpoint(a: Dict[str, Any], b: Dict[str, Any]) -> Tuple[float, float, float]:
    ax, ay, az = get_numeric_xyz(a)
    bx, by, bz = get_numeric_xyz(b)
    return (ax + bx) / 2.0, (ay + by) / 2.0, (az + bz) / 2.0


def euclidean_distance_3d(
    p1: Tuple[float, float, float], p2: Tuple[float, float, float]
) -> float:
    return math.sqrt(
        (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2
    )


def landmark_has_numeric_xyz(landmark: Any) -> bool:
    if not isinstance(landmark, dict):
        return False
    for key in ("x", "y", "z"):
        if key not in landmark:
            return False
        try:
            float(landmark[key])
        except (TypeError, ValueError):
            return False
    return True


def normalize_frame_landmarks(
    landmarks: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], bool]:
    required_indices = [LEFT_SHOULDER_IDX, RIGHT_SHOULDER_IDX, LEFT_HIP_IDX, RIGHT_HIP_IDX]
    if len(landmarks) <= max(required_indices):
        return landmarks, False

    for idx in required_indices:
        if not landmark_has_numeric_xyz(landmarks[idx]):
            return landmarks, False

    hip_mid = get_midpoint(landmarks[LEFT_HIP_IDX], landmarks[RIGHT_HIP_IDX])
    shoulder_mid = get_midpoint(landmarks[LEFT_SHOULDER_IDX], landmarks[RIGHT_SHOULDER_IDX])
    body_scale = euclidean_distance_3d(shoulder_mid, hip_mid)

    if not math.isfinite(body_scale) or body_scale <= 0.0:
        return landmarks, False

    normalized_landmarks: List[Dict[str, Any]] = []
    for landmark in landmarks:
        if not landmark_has_numeric_xyz(landmark):
            normalized_landmarks.append(dict(landmark) if isinstance(landmark, dict) else landmark)
            continue

        lx, ly, lz = get_numeric_xyz(landmark)
        centered_x = lx - hip_mid[0]
        centered_y = ly - hip_mid[1]
        centered_z = lz - hip_mid[2]

        normalized_landmark = dict(landmark)
        normalized_landmark["x"] = centered_x / body_scale
        normalized_landmark["y"] = centered_y / body_scale
        normalized_landmark["z"] = centered_z / body_scale
        # Keep visibility unchanged (if present).
        normalized_landmarks.append(normalized_landmark)

    return normalized_landmarks, True


def normalize_one_file(input_path: Path, output_path: Path) -> Tuple[int, int]:
    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Top-level JSON must be an object.")

    frames = data.get("frames", [])
    if not isinstance(frames, list):
        frames = []

    normalized_frames: List[Dict[str, Any]] = []
    warning_count = 0
    frames_normalized = 0

    for frame_index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            warning_count += 1
            print(f"WARNING [{input_path.name}] frame {frame_index}: invalid frame object; unchanged.")
            normalized_frames.append(frame)
            continue

        landmarks = frame.get("landmarks")
        if not isinstance(landmarks, list):
            warning_count += 1
            print(
                f"WARNING [{input_path.name}] frame {frame_index}: missing/invalid landmarks; unchanged."
            )
            normalized_frames.append(dict(frame))
            continue

        normalized_landmarks, success = normalize_frame_landmarks(landmarks)
        normalized_frame = dict(frame)
        normalized_frame["landmarks"] = normalized_landmarks
        normalized_frames.append(normalized_frame)

        if success:
            frames_normalized += 1
        else:
            warning_count += 1
            print(
                f"WARNING [{input_path.name}] frame {frame_index}: invalid body scale or reference landmarks; unchanged."
            )

    normalized_data = dict(data)
    normalized_data["frames"] = normalized_frames

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(normalized_data, f, indent=2)

    return frames_normalized, warning_count


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
    total_frames_normalized = 0
    total_warnings = 0

    for input_path in json_files:
        output_path = output_dir / f"{input_path.stem}_normalized.json"
        frames_normalized, warning_count = normalize_one_file(input_path, output_path)

        total_files_processed += 1
        total_frames_normalized += frames_normalized
        total_warnings += warning_count

        print(
            f"{input_path.name} | total frames normalized: {frames_normalized} | "
            f"warnings: {warning_count}"
        )

    print("\nNormalization summary")
    print(f"Total files processed  : {total_files_processed}")
    print(f"Total frames normalized: {total_frames_normalized}")
    print(f"Total warnings         : {total_warnings}")


if __name__ == "__main__":
    main()
