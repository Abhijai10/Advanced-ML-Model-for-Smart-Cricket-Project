import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "ml" / "data" / "processed" / "pose_json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "ml" / "data" / "processed" / "sequences"
DEFAULT_SEQUENCE_LENGTH = 60
DEFAULT_LANDMARK_COUNT = 33
FEATURE_SIZE = 4  # x, y, z, visibility
EPS = 1e-6

LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_HIP = 23
RIGHT_HIP = 24

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)


def load_pose_json(file_path: Path) -> Dict:
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def infer_landmark_count(frames: List[Dict]) -> int:
    for frame in frames:
        landmarks = frame.get("landmarks", [])
        if landmarks:
            return len(landmarks)
    return DEFAULT_LANDMARK_COUNT


def extract_landmark_array(frames: List[Dict], landmark_count: int) -> np.ndarray:
    """Build [num_frames, landmark_count, 4] with NaN for missing landmarks."""
    num_frames = len(frames)
    data = np.full((num_frames, landmark_count, FEATURE_SIZE), np.nan, dtype=np.float32)

    for frame_idx, frame in enumerate(frames):
        landmarks = frame.get("landmarks", [])
        if not landmarks:
            continue

        for lm_idx in range(min(landmark_count, len(landmarks))):
            lm = landmarks[lm_idx]
            data[frame_idx, lm_idx, 0] = float(lm.get("x", np.nan))
            data[frame_idx, lm_idx, 1] = float(lm.get("y", np.nan))
            data[frame_idx, lm_idx, 2] = float(lm.get("z", np.nan))
            data[frame_idx, lm_idx, 3] = float(lm.get("visibility", 0.0))

    return data


def interpolate_missing_landmarks(data: np.ndarray) -> np.ndarray:
    """Interpolate missing values across time; fallback to zeros if no signal."""
    output = data.copy()
    num_frames, landmark_count, feature_count = output.shape
    frame_axis = np.arange(num_frames)

    for lm_idx in range(landmark_count):
        for feat_idx in range(feature_count):
            series = output[:, lm_idx, feat_idx]
            valid_mask = ~np.isnan(series)
            valid_count = int(np.sum(valid_mask))

            if valid_count == 0:
                output[:, lm_idx, feat_idx] = 0.0
            elif valid_count == 1:
                output[:, lm_idx, feat_idx] = float(series[valid_mask][0])
            else:
                output[:, lm_idx, feat_idx] = np.interp(
                    frame_axis,
                    frame_axis[valid_mask],
                    series[valid_mask],
                )

    return output


def compute_hip_midpoint(frame: np.ndarray) -> np.ndarray:
    if frame.shape[0] > RIGHT_HIP:
        return (frame[LEFT_HIP, :3] + frame[RIGHT_HIP, :3]) / 2.0
    return np.zeros(3, dtype=np.float32)


def compute_torso_scale(frame: np.ndarray) -> float:
    if frame.shape[0] > RIGHT_HIP and frame.shape[0] > RIGHT_SHOULDER:
        hip_mid = (frame[LEFT_HIP, :3] + frame[RIGHT_HIP, :3]) / 2.0
        shoulder_mid = (frame[LEFT_SHOULDER, :3] + frame[RIGHT_SHOULDER, :3]) / 2.0
        torso_dist = float(np.linalg.norm(shoulder_mid - hip_mid))
        if torso_dist > EPS:
            return torso_dist

    y_values = frame[:, 1]
    body_height = float(np.max(y_values) - np.min(y_values))
    return body_height if body_height > EPS else 1.0


def normalize_landmarks(data: np.ndarray) -> np.ndarray:
    """Center using hip midpoint and normalize by torso/body scale."""
    normalized = data.copy()
    num_frames = normalized.shape[0]

    for frame_idx in range(num_frames):
        frame = normalized[frame_idx]
        hip_center = compute_hip_midpoint(frame)
        scale = compute_torso_scale(frame)

        frame[:, 0] = (frame[:, 0] - hip_center[0]) / scale
        frame[:, 1] = (frame[:, 1] - hip_center[1]) / scale
        frame[:, 2] = (frame[:, 2] - hip_center[2]) / scale
        # visibility is kept as-is in channel 3

    return normalized


def to_fixed_length(data: np.ndarray, sequence_length: int) -> np.ndarray:
    num_frames = data.shape[0]
    if num_frames == sequence_length:
        return data

    if num_frames == 0:
        return np.zeros((sequence_length, data.shape[1], data.shape[2]), dtype=np.float32)

    if num_frames > sequence_length:
        indices = np.linspace(0, num_frames - 1, sequence_length).astype(int)
        return data[indices]

    pad_count = sequence_length - num_frames
    pad_frame = data[-1:]
    padding = np.repeat(pad_frame, pad_count, axis=0)
    return np.concatenate([data, padding], axis=0)


def flatten_sequence(data: np.ndarray) -> np.ndarray:
    """Convert [T, landmarks, features] -> [T, landmarks*features]."""
    return data.reshape(data.shape[0], -1).astype(np.float32)


def process_pose_json_file(input_file: Path, output_dir: Path, sequence_length: int) -> Path:
    payload = load_pose_json(input_file)
    frames = payload.get("frames", [])
    landmark_count = infer_landmark_count(frames)

    raw_array = extract_landmark_array(frames, landmark_count)
    interpolated = interpolate_missing_landmarks(raw_array)
    normalized = normalize_landmarks(interpolated)
    fixed_length = to_fixed_length(normalized, sequence_length)
    flattened = flatten_sequence(fixed_length)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{input_file.stem}.npy"
    np.save(output_path, flattened)
    return output_path


def collect_input_files(input_path: Path) -> List[Path]:
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        return sorted(input_path.glob("*.json"))
    raise FileNotFoundError(f"Input path not found: {input_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preprocess raw pose JSON into normalized fixed-length sequences."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to one pose JSON file or a folder containing pose JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to save processed sequence .npy files.",
    )
    parser.add_argument(
        "--sequence-length",
        type=int,
        default=DEFAULT_SEQUENCE_LENGTH,
        help="Target fixed sequence length (default: 60).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_dir = args.output_dir.resolve()
    sequence_length = int(args.sequence_length)

    if sequence_length <= 0:
        raise ValueError("--sequence-length must be greater than 0.")

    files = collect_input_files(input_path)
    if not files:
        raise FileNotFoundError(
            f"No pose JSON files found in: {input_path}. "
            f"Expected files from {DEFAULT_INPUT_DIR}."
        )

    LOGGER.info("Found %d file(s) for preprocessing.", len(files))
    for file_path in files:
        output_path = process_pose_json_file(file_path, output_dir, sequence_length)
        LOGGER.info("Saved sequence: %s", output_path)

    LOGGER.info("Preprocessing completed. Output directory: %s", output_dir)


if __name__ == "__main__":
    main()
