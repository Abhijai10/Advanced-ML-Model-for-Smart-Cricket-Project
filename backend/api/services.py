"""Service layer that keeps API transport separate from ML inference logic."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import shutil
import tempfile
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import cv2
from fastapi import Header, HTTPException, Request, UploadFile

from ml.src.inference.analysis_pipeline import analyze_sequence, load_dataset_sequence
from ml.src.inference.inference_config import (
    DATASET_DIR,
    PHASE10_TEMPLATE_PATH,
    PHASE12_VERSION,
    PHASE8_BEST_MODEL_DIR,
)
from ml.src.inference.raw_video_pipeline import analyze_raw_video
from ml.src.preprocessing.extract_pose import POSE_LANDMARKER_MODEL_ASSET_PATH
from ml.src.voice.tts_service import build_frontend_audio_ready_response, synthesize_spoken_feedback
from ml.src.voice.voice_config import AUDIO_OUTPUT_DIR

from .config import SETTINGS


PHASE13_VERSION = "phase_13_api_integration_v1"
ALLOWED_VIDEO_EXTENSIONS = {".avi", ".mkv", ".mov", ".mp4", ".webm"}
_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


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


def _looks_like_video(path: Path, suffix: str) -> bool:
    header = path.read_bytes()[:32]
    if suffix in {".mp4", ".mov"}:
        return len(header) >= 12 and header[4:8] == b"ftyp"
    if suffix == ".webm":
        return header.startswith(b"\x1a\x45\xdf\xa3")
    if suffix in {".avi", ".mkv"}:
        return header.startswith((b"RIFF", b"\x1a\x45\xdf\xa3"))
    return False


def _inspect_video_container(path: Path) -> dict[str, Any]:
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise APIValidationError("Uploaded file is not a readable video container.", "invalid_video_container")
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration = (frame_count / fps) if fps > 0 else 0.0
        if width <= 0 or height <= 0 or frame_count <= 0:
            raise APIValidationError("Uploaded video has no readable frames.", "invalid_video_container")
        if duration > SETTINGS.max_video_duration_seconds:
            raise APIValidationError(
                f"Uploaded video is too long. Limit clips to {SETTINGS.max_video_duration_seconds} seconds.",
                "video_too_long",
            )
        if width * height > SETTINGS.max_video_pixels:
            raise APIValidationError("Uploaded video resolution exceeds the configured limit.", "video_too_large")
        return {
            "fps": fps,
            "frame_count": frame_count,
            "width": width,
            "height": height,
            "duration_seconds": duration,
        }
    finally:
        cap.release()


def _save_upload_to_temp(file: UploadFile, filename: str) -> tuple[Path, int, dict[str, Any]]:
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
                if total_bytes > SETTINGS.max_upload_bytes:
                    raise APIValidationError("Uploaded video exceeds maximum size.", "file_too_large")
                out.write(chunk)
        if total_bytes == 0:
            raise APIValidationError("Uploaded video is empty.", "empty_upload")
        suffix = temp_path.suffix.lower()
        if not _looks_like_video(temp_path, suffix):
            raise APIValidationError("Uploaded bytes do not match a supported video container.", "invalid_video_bytes")
        video_probe = _inspect_video_container(temp_path)
        return temp_path, total_bytes, video_probe
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def _cleanup_temp_path(path: Path) -> None:
    shutil.rmtree(path.parent, ignore_errors=True)


def _segment_timing(result: dict[str, Any]) -> dict[str, Any]:
    segment = result.get("segmentation", {})
    source = result.get("source_metadata", {})
    timing = source.get("resampled_timing") if isinstance(source, dict) else None
    start = segment.get("start_frame")
    end = segment.get("end_frame")
    if not isinstance(timing, list) or not isinstance(start, int) or not isinstance(end, int):
        return {"duration_seconds": None, "source": "unavailable"}
    if start < 0 or end < start or end >= len(timing):
        return {"duration_seconds": None, "source": "invalid_segment"}
    start_seconds = timing[start].get("timestamp_seconds")
    end_seconds = timing[end].get("timestamp_seconds")
    if not isinstance(start_seconds, (int, float)) or not isinstance(end_seconds, (int, float)):
        return {"duration_seconds": None, "source": "missing_timestamps"}
    return {
        "start_seconds": round(float(start_seconds), 3),
        "end_seconds": round(float(end_seconds), 3),
        "duration_seconds": round(max(0.0, float(end_seconds) - float(start_seconds)), 3),
        "source": "original_video_timestamps",
    }


def _attach_voice_and_metadata(
    result: dict[str, Any],
    *,
    filename: str,
    upload_bytes: int,
    analysis_mode: str,
    request_id: str,
) -> dict[str, Any]:
    result["analysis_quality"] = _analysis_quality(result)
    audio_name = f"{request_id}-{uuid4().hex}.wav"
    voice_ready = build_frontend_audio_ready_response(
        analysis_response=result,
        voice_output=synthesize_spoken_feedback(
            result["spoken_feedback"],
            output_path=AUDIO_OUTPUT_DIR / audio_name,
        ),
    )
    result["voice_output"] = voice_ready["audio"]
    result["voice_output"]["audio_url"] = f"/audio/{Path(result['voice_output']['audio_path']).name}"
    result["timing"] = _segment_timing(result)
    result["api_metadata"] = {
        "phase": "Phase 13",
        "version": PHASE13_VERSION,
        "created_at": _utc_now(),
        "request_id": request_id,
        "upload_filename": filename,
        "upload_bytes": upload_bytes,
        "temporary_file_saved": True,
        "temporary_file_cleaned": True,
        "analysis_mode": analysis_mode,
        "pipeline_version": PHASE12_VERSION,
        "voice_output_ready": bool(voice_ready["audio"]["available"]),
        "api_note": (
            "Production analysis uses the uploaded video bytes. Stored dataset samples "
            "are available only through the disabled-by-default dev endpoint."
        ),
    }
    return result


def _analysis_quality(result: dict[str, Any]) -> dict[str, Any]:
    """Return an honest quality state for frontend and persisted reports."""
    source = result.get("source_metadata", {})
    confidence = float(result.get("shot_confidence", 0.0) or 0.0)
    frames_after_cleaning = source.get("frames_after_cleaning") if isinstance(source, dict) else None
    frames_extracted = source.get("frames_extracted") if isinstance(source, dict) else None
    confidence_threshold = SETTINGS.uncertainty_confidence_threshold / 100.0
    reasons: list[str] = []
    status = "ok"

    if confidence < confidence_threshold:
        status = "uncertain"
        reasons.append(
            f"Model confidence {confidence:.2f} is below the configured {confidence_threshold:.2f} threshold."
        )
    if isinstance(frames_after_cleaning, int) and frames_after_cleaning < SETTINGS.min_clean_pose_frames:
        status = "insufficient_quality"
        reasons.append(
            f"Only {frames_after_cleaning} clean pose frames were available; at least {SETTINGS.min_clean_pose_frames} are recommended."
        )
    if not reasons:
        reasons.append("Input quality and model confidence meet the current v1 thresholds.")

    return {
        "status": status,
        "reasons": reasons,
        "confidence_threshold": confidence_threshold,
        "min_clean_pose_frames": SETTINGS.min_clean_pose_frames,
        "frames_extracted": frames_extracted,
        "frames_after_cleaning": frames_after_cleaning,
    }


def analyze_uploaded_video(file: UploadFile, *, request_id: str) -> dict[str, Any]:
    """Analyze one uploaded cricket video from its actual bytes."""
    filename = _validate_video_upload(file)
    temp_path, upload_bytes, video_probe = _save_upload_to_temp(file, filename)
    try:
        try:
            raw_result = analyze_raw_video(temp_path)
            raw_result.setdefault("debug_metadata", {})["upload_video_probe"] = video_probe
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
            request_id=request_id,
        )
    finally:
        _cleanup_temp_path(temp_path)


def analyze_dataset_sample(
    *,
    sample_index: int | None,
    file_name: str | None,
    request_id: str,
) -> dict[str, Any]:
    """Analyze a trusted stored sample for local validation."""
    if sample_index is None and file_name is None:
        raise APIValidationError("Provide sample_index or file_name.", "missing_dataset_selector")
    sequence, source_metadata = load_dataset_sequence(sample_index=sample_index, file_name=file_name)
    result = analyze_sequence(sequence, source_metadata).to_dict()
    return _attach_voice_and_metadata(
        result,
        filename=str(file_name or f"sample_{sample_index}"),
        upload_bytes=0,
        analysis_mode="dev_finalized_dataset_sequence",
        request_id=request_id,
    )


def api_health() -> dict[str, Any]:
    """Return lightweight liveness information without checking dependencies."""
    return {
        "status": "ok",
        "service": "smart_cricket_api",
        "phase": "Phase 13",
        "inference_ready": True,
        "version": PHASE13_VERSION,
    }


def api_readiness() -> dict[str, Any]:
    """Check runtime artifacts needed for real inference."""
    checks: dict[str, dict[str, Any]] = {}

    def record(name: str, ok: bool, detail: str) -> None:
        checks[name] = {"ok": bool(ok), "detail": detail}

    record("checkpoint", (PHASE8_BEST_MODEL_DIR / "checkpoint.pt").is_file(), str(PHASE8_BEST_MODEL_DIR / "checkpoint.pt"))
    record("scaler_mean", (PHASE8_BEST_MODEL_DIR / "scaler" / "feature_mean.npy").is_file(), str(PHASE8_BEST_MODEL_DIR / "scaler" / "feature_mean.npy"))
    record("scaler_std", (PHASE8_BEST_MODEL_DIR / "scaler" / "feature_std.npy").is_file(), str(PHASE8_BEST_MODEL_DIR / "scaler" / "feature_std.npy"))
    record("feature_schema", (DATASET_DIR / "temporal_feature_schema.json").is_file(), str(DATASET_DIR / "temporal_feature_schema.json"))
    record("label_schema", (DATASET_DIR / "temporal_label_mapping.json").is_file(), str(DATASET_DIR / "temporal_label_mapping.json"))
    record("technique_templates", PHASE10_TEMPLATE_PATH.is_file(), str(PHASE10_TEMPLATE_PATH))
    record("pose_model", POSE_LANDMARKER_MODEL_ASSET_PATH.is_file(), str(POSE_LANDMARKER_MODEL_ASSET_PATH))
    try:
        probe_dir = Path(tempfile.mkdtemp(prefix="smart_cricket_ready_"))
        probe = probe_dir / "probe.tmp"
        probe.write_text("ok", encoding="utf-8")
        record("temporary_storage", probe.read_text(encoding="utf-8") == "ok", str(probe_dir))
    except Exception as exc:
        record("temporary_storage", False, type(exc).__name__)
    finally:
        if "probe_dir" in locals():
            shutil.rmtree(probe_dir, ignore_errors=True)
    record(
        "auth_configuration",
        (not SETTINGS.require_auth) or bool(SETTINGS.supabase_jwt_secret),
        "auth optional" if not SETTINGS.require_auth else "SUPABASE_JWT_SECRET required",
    )

    return {
        "status": "ready" if all(item["ok"] for item in checks.values()) else "not_ready",
        "service": "smart_cricket_api",
        "version": PHASE13_VERSION,
        "checks": checks,
    }


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(request: Request) -> None:
    """Small in-memory rate limiter for single-process deployments/tests."""
    if SETTINGS.rate_limit_per_minute <= 0:
        return
    now = time.monotonic()
    bucket = _RATE_LIMIT_BUCKETS[_client_key(request)]
    while bucket and now - bucket[0] > 60.0:
        bucket.popleft()
    if len(bucket) >= SETTINGS.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail={
                "detail": "Too many analysis requests. Wait a moment and try again.",
                "error_code": "rate_limited",
                "request_id": request.state.request_id,
            },
        )
    bucket.append(now)


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _verify_hs256_jwt(token: str, secret: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        header = json.loads(_base64url_decode(header_b64))
        payload = json.loads(_base64url_decode(payload_b64))
    except Exception as exc:
        raise APIValidationError("Invalid authorization token.", "invalid_token") from exc
    if header.get("alg") != "HS256":
        raise APIValidationError("Unsupported authorization token algorithm.", "invalid_token")
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual = _base64url_decode(signature_b64)
    if not hmac.compare_digest(expected, actual):
        raise APIValidationError("Invalid authorization token signature.", "invalid_token")
    exp = payload.get("exp")
    if isinstance(exp, (int, float)) and exp < time.time():
        raise APIValidationError("Authorization token has expired.", "expired_token")
    return payload


def enforce_auth(request: Request, authorization: str | None = Header(default=None)) -> None:
    """Verify Supabase JWTs when auth is enabled by configuration."""
    if not SETTINGS.require_auth:
        return
    if not SETTINGS.supabase_jwt_secret:
        raise HTTPException(
            status_code=503,
            detail={
                "detail": "API authentication is enabled but not configured.",
                "error_code": "auth_not_configured",
                "request_id": request.state.request_id,
            },
        )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail={
                "detail": "Authentication is required for analysis.",
                "error_code": "missing_auth",
                "request_id": request.state.request_id,
            },
        )
    try:
        _verify_hs256_jwt(authorization.split(" ", 1)[1].strip(), SETTINGS.supabase_jwt_secret)
    except APIValidationError as exc:
        raise HTTPException(
            status_code=401,
            detail={
                "detail": str(exc),
                "error_code": exc.error_code,
                "request_id": request.state.request_id,
            },
        ) from exc
