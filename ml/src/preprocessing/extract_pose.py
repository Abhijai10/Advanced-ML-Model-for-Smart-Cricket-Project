import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "ml" / "data" / "processed" / "pose_json"
POSE_LANDMARKER_MODEL_ASSET_PATH = (
    PROJECT_ROOT / "ml" / "models" / "pose_landmarker_full.task"
)


def build_output_path(input_video_path: Path, output_dir: Path) -> Path:
    """Create output JSON path from input video name."""
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{input_video_path.stem}.json"


def landmark_to_dict(landmark: Any) -> Dict[str, float]:
    """Convert a MediaPipe landmark into a serializable dictionary."""
    return {
        "x": float(landmark.x),
        "y": float(landmark.y),
        "z": float(landmark.z),
        "visibility": float(getattr(landmark, "visibility", 0.0)),
    }


def create_pose_landmarker() -> vision.PoseLandmarker:
    """Create a Pose Landmarker instance using the MediaPipe Tasks API."""
    if not POSE_LANDMARKER_MODEL_ASSET_PATH.exists():
        raise FileNotFoundError(
            "Pose Landmarker model asset not found. "
            f"Place the model file at: {POSE_LANDMARKER_MODEL_ASSET_PATH} "
            "(for example, pose_landmarker_full.task)."
        )

    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(
            model_asset_path=str(POSE_LANDMARKER_MODEL_ASSET_PATH)
        ),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return vision.PoseLandmarker.create_from_options(options)


def extract_pose_from_video(input_video: Path) -> Dict[str, Any]:
    """Extract frame-wise pose landmarks and video metadata."""
    cap = cv2.VideoCapture(str(input_video))
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {input_video}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = (total_frames / fps) if fps > 0 else 0.0

    pose_landmarker = create_pose_landmarker()

    frames: List[Dict[str, Any]] = []
    detected_frames = 0
    frame_index = 0

    try:
        while True:
            success, frame = cap.read()
            if not success:
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            timestamp_ms = int((frame_index / fps) * 1000) if fps > 0 else frame_index * 33
            results = pose_landmarker.detect_for_video(mp_image, timestamp_ms)

            if results.pose_landmarks:
                landmarks = [
                    landmark_to_dict(landmark)
                    for landmark in results.pose_landmarks[0]
                ]
                detected_frames += 1
            else:
                # Keep structure consistent even when no pose is found.
                landmarks = []

            timestamp = (frame_index / fps) if fps > 0 else None
            frames.append(
                {
                    "frame_index": frame_index,
                    "timestamp": timestamp,
                    "landmarks": landmarks,
                }
            )
            frame_index += 1
    finally:
        cap.release()
        pose_landmarker.close()

    extraction_status = "success" if frame_index > 0 else "failed"
    if frame_index > 0 and detected_frames == 0:
        extraction_status = "no_pose_detected"

    return {
        "video_metadata": {
            "input_path": str(input_video),
            "fps": fps,
            "total_frames": total_frames,
            "width": width,
            "height": height,
            "duration": duration,
            "extraction_status": extraction_status,
        },
        "frames": frames,
    }


def save_pose_json(data: Dict[str, Any], output_path: Path) -> None:
    """Save extracted pose data into a JSON file."""
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract MediaPipe Pose landmarks from a cricket video."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to input cricket batting video.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to save output pose JSON (default: ml/data/processed/pose_json/).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_video = args.input.resolve()
    output_dir = args.output_dir.resolve()

    if not input_video.exists():
        raise FileNotFoundError(f"Input video does not exist: {input_video}")

    output_path = build_output_path(input_video, output_dir)
    pose_data = extract_pose_from_video(input_video)
    save_pose_json(pose_data, output_path)

    print(f"Pose extraction completed: {output_path}")


if __name__ == "__main__":
    main()
