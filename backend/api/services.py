"""Service layer that keeps API transport separate from ML inference logic."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import shutil
import tempfile
import time
import threading
import urllib.request
import concurrent.futures
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import cv2
from fastapi import Header, HTTPException, Request, UploadFile
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa, utils
from cryptography.hazmat.primitives import hashes

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

from .audio import sign_audio_url
from .config import SETTINGS
from .evidence import EvidenceOutcome, get_evidence_provider
from .persistence import persist_analysis_session
from .provenance import build_provenance
from .services_version import PHASE13_VERSION


ALLOWED_VIDEO_EXTENSIONS = {".avi", ".mkv", ".mov", ".mp4", ".webm"}
_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_FEEDBACK_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_ANALYSIS_SEMAPHORE = threading.BoundedSemaphore(max(1, SETTINGS.max_concurrent_analyses))
_JWKS_CACHE: dict[str, Any] = {"loaded_at": 0.0, "keys": []}


class APIValidationError(ValueError):
    """Expected user/input validation error for API responses."""

    def __init__(self, message: str, error_code: str = "invalid_request") -> None:
        super().__init__(message)
        self.error_code = error_code


class AnalysisOverloadError(RuntimeError):
    """Raised when analysis capacity is exhausted before validation starts."""

    error_code = "analysis_overloaded"


class AnalysisTimeoutError(RuntimeError):
    """Raised when bounded inference execution exceeds the configured limit."""

    error_code = "analysis_timeout"


class JWKSUnavailableError(RuntimeError):
    """Raised when configured JWKS verification cannot reach the identity provider."""

    error_code = "jwks_unavailable"


@dataclass(frozen=True)
class AuthContext:
    """Trusted identity extracted by the API layer."""

    user_id: str | None = None
    claims: dict[str, Any] | None = None
    authorization_present: bool = False


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


def _save_upload_to_temp(file: UploadFile, filename: str) -> tuple[Path, int, str, dict[str, Any]]:
    temp_dir = Path(tempfile.mkdtemp(prefix="smart_cricket_api_"))
    temp_path = temp_dir / filename
    total_bytes = 0
    try:
        digest = hashlib.sha256()
        with temp_path.open("wb") as out:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > SETTINGS.max_upload_bytes:
                    raise APIValidationError("Uploaded video exceeds maximum size.", "file_too_large")
                digest.update(chunk)
                out.write(chunk)
        if total_bytes == 0:
            raise APIValidationError("Uploaded video is empty.", "empty_upload")
        suffix = temp_path.suffix.lower()
        if not _looks_like_video(temp_path, suffix):
            raise APIValidationError("Uploaded bytes do not match a supported video container.", "invalid_video_bytes")
        video_probe = _inspect_video_container(temp_path)
        return temp_path, total_bytes, digest.hexdigest(), video_probe
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def _cleanup_temp_path(path: Path) -> None:
    shutil.rmtree(path.parent, ignore_errors=True)


def _run_raw_video_with_timeout(temp_path: Path) -> dict[str, Any]:
    """Run raw-video inference with bounded caller wait and clear timeout status."""
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(analyze_raw_video, temp_path)
    try:
        return future.result(timeout=SETTINGS.analysis_execution_timeout_seconds)
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        raise AnalysisTimeoutError("Analysis took too long and was stopped. Try a shorter, clearer clip.") from exc
    finally:
        if future.done():
            executor.shutdown(wait=True, cancel_futures=True)


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
    clip_hash: str | None = None,
) -> dict[str, Any]:
    result["analysis_quality"] = _analysis_quality(result)
    provenance = build_provenance()
    result.setdefault("debug_metadata", {})["model_version"] = provenance["model_version"]
    result.setdefault("debug_metadata", {})["feature_contract_version"] = provenance["feature_contract_version"]
    result["model_provenance"] = provenance
    audio_name = f"{request_id}-{uuid4().hex}.wav"
    try:
        voice_output = synthesize_spoken_feedback(
            result["spoken_feedback"],
            output_path=AUDIO_OUTPUT_DIR / audio_name,
        )
        voice_ready = build_frontend_audio_ready_response(
            analysis_response=result,
            voice_output=voice_output,
        )
        voice_error = None
    except Exception as exc:
        voice_error = type(exc).__name__
        voice_ready = {
            "audio": {
                "available": False,
                "provider": "unavailable",
                "audio_path": "",
                "audio_filename": None,
                "audio_format": "none",
                "audio_bytes": 0,
                "is_spoken_tts": False,
                "degraded_to_text_only": True,
            }
        }
    result["voice_output"] = voice_ready["audio"]
    if result["voice_output"].get("audio_path"):
        audio_filename = Path(result["voice_output"]["audio_path"]).name
        result["voice_output"]["audio_url"] = sign_audio_url(audio_filename)
        result["voice_output"]["audio_path"] = ""
    else:
        result["voice_output"]["audio_url"] = None
    result["timing"] = _segment_timing(result)
    result["api_metadata"] = {
        "phase": "Phase 13",
        "version": PHASE13_VERSION,
        "created_at": _utc_now(),
        "request_id": request_id,
        "upload_filename": filename,
        "upload_bytes": upload_bytes,
        "clip_hash": clip_hash,
        "temporary_file_saved": True,
        "temporary_file_cleaned": True,
        "analysis_mode": analysis_mode,
        "pipeline_version": PHASE12_VERSION,
        "model_version": provenance["model_version"],
        "model_provenance": provenance,
        "voice_output_ready": bool(voice_ready["audio"]["available"]),
        "voice_error": voice_error,
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
    if not _ANALYSIS_SEMAPHORE.acquire(timeout=SETTINGS.analysis_queue_timeout_seconds):
        raise AnalysisOverloadError("The analysis queue is busy. Wait a moment and try again.")
    try:
        filename = _validate_video_upload(file)
        temp_path, upload_bytes, clip_hash, video_probe = _save_upload_to_temp(file, filename)
        try:
            try:
                raw_result = _run_raw_video_with_timeout(temp_path)
                raw_result.setdefault("debug_metadata", {})["upload_video_probe"] = video_probe
            except Exception as exc:
                if isinstance(exc, AnalysisTimeoutError):
                    raise
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
                clip_hash=clip_hash,
            )
        finally:
            _cleanup_temp_path(temp_path)
    finally:
        _ANALYSIS_SEMAPHORE.release()


def analyze_uploaded_video_with_retention(
    file: UploadFile,
    *,
    request_id: str,
    auth: AuthContext,
    retain_evidence: bool = False,
) -> tuple[dict[str, Any], EvidenceOutcome | None]:
    """Analyze an upload and optionally retain consented raw evidence before temp cleanup."""
    if not _ANALYSIS_SEMAPHORE.acquire(timeout=SETTINGS.analysis_queue_timeout_seconds):
        raise AnalysisOverloadError("The analysis queue is busy. Wait a moment and try again.")
    try:
        filename = _validate_video_upload(file)
        temp_path, upload_bytes, clip_hash, video_probe = _save_upload_to_temp(file, filename)
        evidence_outcome: EvidenceOutcome | None = None
        analysis_session_id = str(uuid4())
        try:
            try:
                raw_result = _run_raw_video_with_timeout(temp_path)
                raw_result.setdefault("debug_metadata", {})["upload_video_probe"] = video_probe
            except Exception as exc:
                if isinstance(exc, AnalysisTimeoutError):
                    raise
                raise APIValidationError(
                    (
                        "The uploaded video could not be converted into a valid Smart Cricket "
                        "temporal sequence. Record a clear batting motion with the full body visible."
                    ),
                    "raw_video_analysis_failed",
                ) from exc
            if retain_evidence:
                if not SETTINGS.allow_model_improvement_participation:
                    evidence_outcome = EvidenceOutcome(
                        retained=False,
                        status="disabled",
                        provider=SETTINGS.evidence_storage_backend,
                        error_code="model_improvement_disabled",
                        metadata={
                            "storage_provider": SETTINGS.evidence_storage_backend,
                            "raw_clip_retained": False,
                            "processed_evidence_retained": False,
                            "reason": "model_improvement_disabled",
                        },
                    )
                elif not auth.user_id:
                    evidence_outcome = EvidenceOutcome(
                        retained=False,
                        status="failed",
                        provider=SETTINGS.evidence_storage_backend,
                        error_code="auth_required_for_evidence_retention",
                    )
                else:
                    media_type = getattr(file, "content_type", None) or "application/octet-stream"
                    evidence_outcome = get_evidence_provider().retain_raw_clip(
                        source_path=temp_path,
                        user_id=auth.user_id,
                        analysis_session_id=analysis_session_id,
                        consent_version=SETTINGS.consent_version,
                        media_type=media_type,
                        retention_days=SETTINGS.evidence_retention_days,
                    )
            result = _attach_voice_and_metadata(
                raw_result,
                filename=filename,
                upload_bytes=upload_bytes,
                analysis_mode="raw_video_upload",
                request_id=request_id,
                clip_hash=clip_hash,
            )
            result["api_metadata"]["evidence_retention"] = {
                "requested": retain_evidence,
                "status": evidence_outcome.status if evidence_outcome else "not_requested",
                "retained": bool(evidence_outcome and evidence_outcome.retained),
                "provider": evidence_outcome.provider if evidence_outcome else SETTINGS.evidence_storage_backend,
                "error_code": evidence_outcome.error_code if evidence_outcome else None,
                "retention_expires_at": (evidence_outcome.metadata or {}).get("retention_expires_at") if evidence_outcome else None,
            }
            result["api_metadata"]["planned_analysis_session_id"] = analysis_session_id
            return result, evidence_outcome
        finally:
            _cleanup_temp_path(temp_path)
    finally:
        _ANALYSIS_SEMAPHORE.release()


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
        "inference_ready": False,
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
        _auth_config_ready(),
        _auth_config_detail(),
    )
    record(
        "audio_signing_secret",
        _audio_config_ready(),
        "SMART_CRICKET_AUDIO_SIGNING_SECRET configured or local development/test mode",
    )
    if SETTINGS.environment == "production":
        record(
            "persistence_configuration",
            bool(SETTINGS.supabase_url and SETTINGS.supabase_service_role_key),
            "production requires Supabase URL and service-role key for server persistence",
        )
        if SETTINGS.allow_model_improvement_participation:
            record(
                "evidence_storage_configuration",
                SETTINGS.evidence_storage_backend == "supabase" and bool(SETTINGS.evidence_supabase_bucket),
                "production model-improvement participation requires private Supabase Storage bucket",
            )
        record(
            "rate_limit_backend",
            SETTINGS.rate_limit_backend != "memory",
            "production multi-instance deployments require Redis/gateway rate limiting",
        )

    return {
        "status": "ready" if all(item["ok"] for item in checks.values()) else "not_ready",
        "service": "smart_cricket_api",
        "version": PHASE13_VERSION,
        "checks": checks,
    }


def _auth_config_ready() -> bool:
    if not SETTINGS.require_auth:
        return True
    if SETTINGS.environment == "production" and (not SETTINGS.jwt_audience or not SETTINGS.jwt_issuer):
        return False
    return bool(SETTINGS.supabase_jwt_secret or SETTINGS.supabase_url)


def _auth_config_detail() -> str:
    if not SETTINGS.require_auth:
        return "auth optional"
    return "JWT secret or JWKS-capable Supabase URL configured with issuer/audience in production"


def _audio_config_ready() -> bool:
    if SETTINGS.audio_signing_secret and len(SETTINGS.audio_signing_secret) >= 32:
        return True
    return SETTINGS.environment in {"development", "test"}


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and SETTINGS.trusted_proxy_hops > 0:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(request: Request) -> None:
    """Small in-memory rate limiter for single-process deployments/tests."""
    _enforce_bucket_limit(
        request=request,
        buckets=_RATE_LIMIT_BUCKETS,
        limit=SETTINGS.rate_limit_per_minute,
        message="Too many analysis requests. Wait a moment and try again.",
    )


def enforce_feedback_rate_limit(request: Request) -> None:
    """Small in-memory feedback limiter for single-process deployments/tests."""
    _enforce_bucket_limit(
        request=request,
        buckets=_FEEDBACK_RATE_LIMIT_BUCKETS,
        limit=SETTINGS.feedback_rate_limit_per_minute,
        message="Too many feedback requests. Wait a moment and try again.",
    )


def _enforce_bucket_limit(
    *,
    request: Request,
    buckets: dict[str, deque[float]],
    limit: int,
    message: str,
) -> None:
    if limit <= 0:
        return
    now = time.monotonic()
    bucket = buckets[_client_key(request)]
    while bucket and now - bucket[0] > 60.0:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(
            status_code=429,
            detail={
                "detail": message,
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
    _validate_jwt_claims(payload)
    return payload


def _validate_jwt_claims(payload: dict[str, Any]) -> None:
    now = time.time()
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)) or exp < now:
        raise APIValidationError("Authorization token has expired.", "expired_token")
    nbf = payload.get("nbf")
    if isinstance(nbf, (int, float)) and nbf > now:
        raise APIValidationError("Authorization token is not valid yet.", "invalid_token")
    if not payload.get("sub"):
        raise APIValidationError("Authorization token is missing a subject.", "invalid_token")
    if SETTINGS.jwt_audience and payload.get("aud") != SETTINGS.jwt_audience:
        raise APIValidationError("Authorization token audience is not allowed.", "invalid_token")
    if SETTINGS.jwt_issuer and payload.get("iss") != SETTINGS.jwt_issuer:
        raise APIValidationError("Authorization token issuer is not allowed.", "invalid_token")


def _jwk_int(value: str) -> int:
    return int.from_bytes(_base64url_decode(value), "big")


def _load_jwks() -> list[dict[str, Any]]:
    if not SETTINGS.supabase_url:
        return []
    if time.time() - float(_JWKS_CACHE["loaded_at"]) < SETTINGS.jwks_cache_ttl_seconds:
        return list(_JWKS_CACHE["keys"])
    url = f"{SETTINGS.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    try:
        with urllib.request.urlopen(url, timeout=SETTINGS.jwks_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8") or "{}")
    except Exception as exc:
        raise JWKSUnavailableError("Identity provider signing keys are temporarily unavailable.") from exc
    keys = payload.get("keys") if isinstance(payload, dict) else None
    if not isinstance(keys, list):
        raise JWKSUnavailableError("Identity provider signing keys response is invalid.")
    _JWKS_CACHE["loaded_at"] = time.time()
    _JWKS_CACHE["keys"] = keys if isinstance(keys, list) else []
    return list(_JWKS_CACHE["keys"])


def _verify_asymmetric_jwt(token: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        header = json.loads(_base64url_decode(header_b64))
        payload = json.loads(_base64url_decode(payload_b64))
    except Exception as exc:
        raise APIValidationError("Invalid authorization token.", "invalid_token") from exc
    alg = header.get("alg")
    kid = header.get("kid")
    if alg not in {"RS256", "ES256"}:
        raise APIValidationError("Unsupported authorization token algorithm.", "invalid_token")
    try:
        keys = _load_jwks()
    except JWKSUnavailableError:
        raise
    key = next((item for item in keys if item.get("kid") == kid and item.get("alg") in {None, alg}), None)
    if not key:
        raise APIValidationError("Authorization signing key was not found.", "invalid_token")
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = _base64url_decode(signature_b64)
    try:
        if alg == "RS256":
            public_key = rsa.RSAPublicNumbers(e=_jwk_int(key["e"]), n=_jwk_int(key["n"])).public_key()
            public_key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
        else:
            x = _jwk_int(key["x"])
            y = _jwk_int(key["y"])
            public_key = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
            half = len(signature) // 2
            der_signature = utils.encode_dss_signature(
                int.from_bytes(signature[:half], "big"),
                int.from_bytes(signature[half:], "big"),
            )
            public_key.verify(der_signature, signing_input, ec.ECDSA(hashes.SHA256()))
    except Exception as exc:
        raise APIValidationError("Invalid authorization token signature.", "invalid_token") from exc
    _validate_jwt_claims(payload)
    return payload


def enforce_auth(request: Request, authorization: str | None = Header(default=None)) -> AuthContext:
    """Verify Supabase JWTs when auth is enabled by configuration."""
    request.state.auth = AuthContext(authorization_present=bool(authorization))
    if not SETTINGS.require_auth:
        return request.state.auth
    if not SETTINGS.supabase_jwt_secret and not SETTINGS.supabase_url:
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
        token = authorization.split(" ", 1)[1].strip()
        try:
            header = json.loads(_base64url_decode(token.split(".", 1)[0]))
        except Exception as exc:
            raise APIValidationError("Invalid authorization token.", "invalid_token") from exc
        if header.get("alg") == "HS256":
            if not SETTINGS.supabase_jwt_secret:
                raise APIValidationError("HS256 token verification is not configured.", "invalid_token")
            claims = _verify_hs256_jwt(token, SETTINGS.supabase_jwt_secret)
        else:
            claims = _verify_asymmetric_jwt(token)
    except APIValidationError as exc:
        raise HTTPException(
            status_code=401,
            detail={
                "detail": str(exc),
                "error_code": exc.error_code,
                "request_id": request.state.request_id,
            },
        ) from exc
    except JWKSUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "detail": str(exc),
                "error_code": exc.error_code,
                "request_id": request.state.request_id,
            },
        ) from exc
    context = AuthContext(
        user_id=str(claims.get("sub")) if claims.get("sub") else None,
        claims=claims,
        authorization_present=True,
    )
    request.state.auth = context
    return context


def persist_verified_analysis_for_auth_user(
    *,
    auth: AuthContext,
    result: dict[str, Any],
    filename: str,
    request_id: str,
    analysis_session_id: str | None = None,
    evidence_outcome: EvidenceOutcome | None = None,
) -> None:
    """Attach non-fatal backend persistence metadata to an analysis response."""
    api_metadata = result.setdefault("api_metadata", {})
    clip_hash = api_metadata.get("clip_hash")
    provenance = api_metadata.get("model_provenance") if isinstance(api_metadata.get("model_provenance"), dict) else build_provenance()
    outcome = persist_analysis_session(
        user_id=auth.user_id,
        result=result,
        filename=filename,
        request_id=request_id,
        clip_hash=str(clip_hash or ""),
        provenance=provenance,
        analysis_session_id=analysis_session_id,
        evidence_outcome=evidence_outcome,
    )
    if evidence_outcome and evidence_outcome.retained and not outcome.stored and evidence_outcome.object_path:
        delete_outcome = get_evidence_provider().delete(evidence_outcome.object_path)
        evidence_meta = api_metadata.setdefault("evidence_retention", {})
        evidence_meta["retained"] = False
        evidence_meta["status"] = "deleted_after_persistence_failure" if delete_outcome.status == "deleted" else "orphan_cleanup_failed"
        evidence_meta["error_code"] = delete_outcome.error_code or outcome.error_code or outcome.status
    api_metadata["analysis_persistence"] = {
        "attempted": bool(auth.user_id),
        "stored": outcome.stored,
        "record_id": outcome.record_id,
        "error_code": outcome.error_code,
        "storage_status": outcome.status,
    }
    api_metadata["analysis_session_id"] = outcome.record_id if outcome.stored else None
