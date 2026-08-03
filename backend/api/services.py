"""Service layer that keeps API transport separate from ML inference logic."""

from __future__ import annotations

import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import UploadFile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ML_SRC = PROJECT_ROOT / "ml" / "src"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from inference.analysis_pipeline import analyze_sequence, load_dataset_sequence  # noqa: E402
from inference.inference_config import PHASE12_VERSION  # noqa: E402
from inference.raw_video_pipeline import analyze_raw_video  # noqa: E402
from voice.tts_service import build_frontend_audio_ready_response, synthesize_spoken_feedback  # noqa: E402


PHASE13_VERSION = "phase_13_api_integration_v1"
ALLOWED_VIDEO_EXTENSIONS = {".avi", ".mkv", ".mov", ".mp4", ".webm"}
MAX_UPLOAD_BYTES = 250 * 1024 * 1024


class APIValidationError(ValueError):
    """Expected user/input validation error for API responses."""

    def __init__(self, message: str, error_code: str = "invalid_request") -> None:
        super().__init__(message)
        self.error_code = error_code


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_video_upload(file: UploadFile) -> str:
    filename = Path(file.filename or "").name
    if not filename:
        raise APIValidationError("Upload must include a filename.", "missing_filename")
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_VIDEO_EXTENSIONS:
        raise APIValidationError(
            f"Unsupported file type {suffix!r}. Expected one of {sorted(ALLOWED_VIDEO_EXTENSIONS)}.",
            "unsupported_file_type",
        )
    return filename


def _save_upload_to_temp(file: UploadFile, filename: str) -> tuple[Path, int]:
    temp_dir = Path(tempfile.mkdtemp(prefix="smart_cricket_api_"))
    temp_path = temp_dir / filename
    total_bytes = 0
    try:
        with temp_path.open("wb") as out:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_BYTES:
                    raise APIValidationError("Uploaded video exceeds maximum size.", "file_too_large")
                out.write(chunk)
        return temp_path, total_bytes
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def _cleanup_temp_path(path: Path) -> None:
    shutil.rmtree(path.parent, ignore_errors=True)


def _attach_voice_and_metadata(
    result: dict[str, Any],
    *,
    filename: str,
    upload_bytes: int,
    analysis_mode: str,
) -> dict[str, Any]:
    voice_ready = build_frontend_audio_ready_response(
        analysis_response=result,
        voice_output=synthesize_spoken_feedback(result["spoken_feedback"]),
    )
    result["voice_output"] = voice_ready["audio"]
    result["api_metadata"] = {
        "phase": "Phase 13",
        "version": PHASE13_VERSION,
        "created_at": _utc_now(),
        "upload_filename": filename,
        "upload_bytes": upload_bytes,
        "temporary_file_saved": True,
        "temporary_file_cleaned": True,
        "analysis_mode": analysis_mode,
        "pipeline_version": PHASE12_VERSION,
        "voice_output_ready": bool(voice_ready["audio"]["available"]),
        "api_note": (
            "API transport is separate from ML business logic. This endpoint calls "
            "the Smart Cricket inference pipeline."
        ),
    }
    return result


def analyze_uploaded_video(file: UploadFile) -> dict[str, Any]:
    """Analyze one uploaded cricket video using the Phase 12 pipeline.

    Phase 13 v1 accepts a video upload and uses the upload filename to resolve a
    finalized temporal sequence from the locked v1 dataset. Arbitrary raw-video
    feature extraction remains a later integration hardening task.
    """
    filename = _validate_video_upload(file)
    temp_path, upload_bytes = _save_upload_to_temp(file, filename)
    try:
        try:
            sequence, source_metadata = load_dataset_sequence(file_name=filename)
            result = analyze_sequence(sequence, source_metadata).to_dict()
            return _attach_voice_and_metadata(
                result,
                filename=filename,
                upload_bytes=upload_bytes,
                analysis_mode="finalized_dataset_sequence",
            )
        except ValueError as exc:
            if Path(filename).suffix.lower() not in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
                raise exc

        try:
            raw_result = analyze_raw_video(temp_path)
        except Exception as exc:
            raise APIValidationError(
                (
                    "The uploaded video could not be converted into a valid Smart Cricket "
                    "temporal sequence. Record a clear batting motion with the full body visible."
                ),
                "raw_video_analysis_failed",
            ) from exc
        return _attach_voice_and_metadata(
            raw_result,
            filename=filename,
            upload_bytes=upload_bytes,
            analysis_mode="raw_video_upload",
        )
    finally:
        _cleanup_temp_path(temp_path)


def api_health() -> dict[str, Any]:
    """Return API health information without running inference."""
    return {
        "status": "ok",
        "service": "smart_cricket_api",
        "phase": "Phase 13",
        "inference_ready": True,
        "version": PHASE13_VERSION,
    }
