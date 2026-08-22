import argparse
import hashlib
import json
import logging
import os
import platform
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
POSE_LANDMARKER_MODEL_SHA256 = "5134a3aad27a58b93da0088d431f366da362b44e3ccfbe3462b3827a839011b1"
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12),
    (11, 13), (13, 15), (15, 17), (15, 19), (15, 21),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (27, 29), (29, 31),
    (24, 26), (26, 28), (28, 30), (30, 32),
]

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)


class MediaPipeInitializationError(RuntimeError):
    """Raised when the MediaPipe Tasks pose runtime cannot start safely."""

    error_code = "mediapipe_init_failed"


class FeatureExtractionError(RuntimeError):
    """Raised when a readable video cannot be converted into pose landmarks."""

    error_code = "feature_extraction_failed"


def resolve_mediapipe_delegate(delegate: str | None = None) -> mp_python.BaseOptions.Delegate | None:
    """Resolve the supported delegate setting with a stable macOS auto default."""

    value = (delegate or os.getenv("SMART_CRICKET_MEDIAPIPE_DELEGATE", "auto")).strip().lower()
    if value == "auto" and platform.system() != "Darwin":
        return None
    if value == "auto":
        # MediaPipe Metal aborts on the RGB ImageFrame path used by video uploads.
        # CPU/XNNPACK is the verified macOS path; explicit gpu remains available.
        return mp_python.BaseOptions.Delegate.CPU
    if value == "cpu":
        return mp_python.BaseOptions.Delegate.CPU
    if value == "gpu":
        return mp_python.BaseOptions.Delegate.GPU
    raise ValueError("SMART_CRICKET_MEDIAPIPE_DELEGATE must be auto, cpu, or gpu.")


def pose_model_status() -> dict[str, Any]:
    """Return non-secret pose-model integrity details for diagnostics."""

    if not POSE_LANDMARKER_MODEL_ASSET_PATH.is_file():
        return {"exists": False, "path": str(POSE_LANDMARKER_MODEL_ASSET_PATH), "sha256": None, "matches_expected": False}
    digest = hashlib.sha256(POSE_LANDMARKER_MODEL_ASSET_PATH.read_bytes()).hexdigest()
    return {
        "exists": True,
        "path": str(POSE_LANDMARKER_MODEL_ASSET_PATH),
        "sha256": digest,
        "matches_expected": digest == POSE_LANDMARKER_MODEL_SHA256,
    }


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


def create_pose_landmarker(delegate: str | None = None) -> vision.PoseLandmarker:
    """Create a Pose Landmarker instance using the MediaPipe Tasks API."""
    if not POSE_LANDMARKER_MODEL_ASSET_PATH.exists():
        raise FileNotFoundError(
            "Pose Landmarker model asset not found. "
            f"Place the model file at: {POSE_LANDMARKER_MODEL_ASSET_PATH} "
            "(for example, pose_landmarker_full.task)."
        )

    resolved_delegate = resolve_mediapipe_delegate(delegate)
    try:
        base_options_kwargs: dict[str, Any] = {"model_asset_path": str(POSE_LANDMARKER_MODEL_ASSET_PATH)}
        if resolved_delegate is not None:
            base_options_kwargs["delegate"] = resolved_delegate
        options = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(**base_options_kwargs),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        return vision.PoseLandmarker.create_from_options(options)
    except Exception as exc:
        requested = (delegate or os.getenv("SMART_CRICKET_MEDIAPIPE_DELEGATE", "auto")).strip().lower()
        raise MediaPipeInitializationError(
            f"MediaPipe pose runtime could not initialize with delegate={requested}."
        ) from exc


def draw_pose_overlay(frame: Any, landmarks: List[Dict[str, float]]) -> Any:
    """Draw simple pose skeleton overlay for visualization."""
    overlay = frame.copy()
    frame_height, frame_width = overlay.shape[:2]

    for start_idx, end_idx in POSE_CONNECTIONS:
        if start_idx >= len(landmarks) or end_idx >= len(landmarks):
            continue
        start = landmarks[start_idx]
        end = landmarks[end_idx]
        start_point = (int(start["x"] * frame_width), int(start["y"] * frame_height))
        end_point = (int(end["x"] * frame_width), int(end["y"] * frame_height))
        cv2.line(overlay, start_point, end_point, (0, 255, 0), 2)

    for landmark in landmarks:
        point = (
            int(landmark["x"] * frame_width),
            int(landmark["y"] * frame_height),
        )
        cv2.circle(overlay, point, 3, (0, 0, 255), -1)

    return overlay


def build_failure_response(input_video: Path, error_message: str) -> Dict[str, Any]:
    """Return a valid empty response when extraction cannot start."""
    return {
        "video_metadata": {
            "input_path": str(input_video),
            "fps": 0.0,
            "total_frames": 0,
            "width": 0,
            "height": 0,
            "duration": 0.0,
            "extraction_status": error_message,
        },
        "frames": [],
    }


def extract_pose_from_video(
    input_video: Path, frame_skip: int = 1, visualize: bool = False
) -> Dict[str, Any]:
    """Extract frame-wise pose landmarks and video metadata."""
    cap = cv2.VideoCapture(str(input_video))
    if not cap.isOpened():
        error_message = f"failed_to_open_video: Could not open video: {input_video}"
        LOGGER.error(error_message)
        return build_failure_response(input_video, error_message)

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = (total_frames / fps) if fps > 0 else 0.0

    try:
        pose_landmarker = create_pose_landmarker()
    except MediaPipeInitializationError:
        cap.release()
        raise

    frames: List[Dict[str, Any]] = []
    detected_frames = 0
    failed_pose_detections = 0
    skipped_frames = 0
    processed_frames = 0
    frame_index = 0

    try:
        while True:
            success, frame = cap.read()
            if not success:
                break

            if frame_skip > 1 and frame_index % frame_skip != 0:
                skipped_frames += 1
                frame_index += 1
                continue

            try:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            except cv2.error as exc:
                raise FeatureExtractionError("OpenCV could not convert a video frame for pose extraction.") from exc
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            timestamp_ms = int((frame_index / fps) * 1000) if fps > 0 else frame_index * 33
            try:
                results = pose_landmarker.detect_for_video(mp_image, timestamp_ms)
            except Exception as exc:
                raise FeatureExtractionError("MediaPipe failed while extracting pose landmarks from the video.") from exc

            if results.pose_landmarks:
                landmarks = [
                    landmark_to_dict(landmark)
                    for landmark in results.pose_landmarks[0]
                ]
                detected_frames += 1
            else:
                # Keep structure consistent even when no pose is found.
                landmarks = []
                failed_pose_detections += 1

            timestamp = (frame_index / fps) if fps > 0 else None
            frames.append(
                {
                    "frame_index": frame_index,
                    "timestamp": timestamp,
                    "landmarks": landmarks,
                }
            )
            processed_frames += 1

            if visualize:
                display_frame = draw_pose_overlay(frame, landmarks) if landmarks else frame
                cv2.imshow("Pose Extraction", display_frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    LOGGER.info("Visualization interrupted by user.")
                    break

            frame_index += 1
    finally:
        cap.release()
        pose_landmarker.close()
        if visualize:
            cv2.destroyAllWindows()

    extraction_status = "success" if processed_frames > 0 else "failed"
    if processed_frames > 0 and detected_frames == 0:
        extraction_status = "no_pose_detected"

    LOGGER.info("Processed frames: %s", processed_frames)
    LOGGER.info("Skipped frames: %s", skipped_frames)
    LOGGER.info("Failed pose detections: %s", failed_pose_detections)
    LOGGER.info(
        "Extraction summary: status=%s, detections=%s, output_frames=%s",
        extraction_status,
        detected_frames,
        len(frames),
    )

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


def validate_saved_output(output_path: Path) -> None:
    """Confirm JSON output was saved and warn if it is empty."""
    if not output_path.exists():
        raise FileNotFoundError(f"Output JSON was not created: {output_path}")

    with output_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not data.get("frames"):
        LOGGER.warning("Saved JSON is empty or contains no extracted frames: %s", output_path)


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
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Display pose overlay while processing the video.",
    )
    parser.add_argument(
        "--frame-skip",
        type=int,
        default=1,
        help="Process every nth frame for faster extraction (default: 1).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_video = args.input.resolve()
    output_dir = args.output_dir.resolve()

    if not input_video.exists():
        raise FileNotFoundError(f"Input video does not exist: {input_video}")
    if args.frame_skip < 1:
        raise ValueError("--frame-skip must be greater than or equal to 1.")

    output_path = build_output_path(input_video, output_dir)
    pose_data = extract_pose_from_video(
        input_video=input_video,
        frame_skip=args.frame_skip,
        visualize=args.visualize,
    )
    save_pose_json(pose_data, output_path)
    validate_saved_output(output_path)

    print(f"Pose extraction completed: {output_path}")


if __name__ == "__main__":
    main()
