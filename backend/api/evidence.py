"""Protected evidence retention providers for consented analyses."""

from __future__ import annotations

import hashlib
import json
import secrets
import shutil
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import SETTINGS


RETAINED_STATUSES = {"stored"}


@dataclass(frozen=True)
class EvidenceOutcome:
    retained: bool
    status: str
    provider: str
    object_path: str | None = None
    metadata: dict[str, Any] | None = None
    error_code: str | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def evidence_is_reviewable(record: dict[str, Any], *, now: datetime | None = None) -> bool:
    """Return whether an analysis/feedback record still has reviewable evidence."""
    current = now or _utc_now()
    if record.get("withdrawn_at") or record.get("deleted_at"):
        return False
    if record.get("storage_status") not in RETAINED_STATUSES:
        return False
    if not record.get("evidence_object_path"):
        return False
    expires_at = record.get("retention_expires_at")
    if isinstance(expires_at, str):
        try:
            parsed = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        if parsed <= current:
            return False
    metadata = record.get("evidence_metadata") if isinstance(record.get("evidence_metadata"), dict) else {}
    return bool(metadata.get("user_id") and metadata.get("analysis_session_id") and metadata.get("checksum_sha256"))


class EvidenceProvider:
    provider_id = "none"

    def retain_raw_clip(
        self,
        *,
        source_path: Path,
        user_id: str,
        analysis_session_id: str,
        consent_version: str,
        media_type: str,
        retention_days: int,
    ) -> EvidenceOutcome:
        return EvidenceOutcome(
            retained=False,
            status="not_retained",
            provider=self.provider_id,
            metadata={"reason": "provider_not_configured"},
            error_code="evidence_storage_not_configured",
        )

    def delete(self, object_path: str) -> EvidenceOutcome:
        return EvidenceOutcome(retained=False, status="deleted", provider=self.provider_id, object_path=object_path)

    def reviewer_access_url(self, object_path: str, *, ttl_seconds: int = 300) -> EvidenceOutcome:
        return EvidenceOutcome(
            retained=False,
            status="unavailable",
            provider=self.provider_id,
            object_path=object_path,
            error_code="reviewer_access_not_configured",
        )


class LocalEvidenceProvider(EvidenceProvider):
    provider_id = "local_development"

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(SETTINGS.evidence_local_storage_dir)

    def retain_raw_clip(
        self,
        *,
        source_path: Path,
        user_id: str,
        analysis_session_id: str,
        consent_version: str,
        media_type: str,
        retention_days: int,
    ) -> EvidenceOutcome:
        created = _utc_now()
        expires = created + timedelta(days=max(1, retention_days))
        object_name = f"{user_id}/{analysis_session_id}/{secrets.token_urlsafe(24)}{source_path.suffix.lower()}"
        target = self.root / object_name
        target.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        shutil.copy2(source_path, target)
        byte_count = target.stat().st_size
        metadata = {
            "storage_provider": self.provider_id,
            "object_public": False,
            "object_name_randomized": True,
            "checksum_sha256": digest,
            "media_type": media_type,
            "byte_count": byte_count,
            "created_at": _iso(created),
            "retention_expires_at": _iso(expires),
            "user_id": user_id,
            "analysis_session_id": analysis_session_id,
            "consent_version": consent_version,
            "raw_clip_retained": True,
            "processed_evidence_retained": False,
            "reviewer_access": "backend_only_local_path",
        }
        (target.with_suffix(target.suffix + ".metadata.json")).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return EvidenceOutcome(
            retained=True,
            status="stored",
            provider=self.provider_id,
            object_path=object_name,
            metadata=metadata,
        )

    def delete(self, object_path: str) -> EvidenceOutcome:
        safe = Path(object_path)
        if safe.is_absolute() or ".." in safe.parts:
            return EvidenceOutcome(False, "failed", self.provider_id, object_path, error_code="invalid_evidence_path")
        path = self.root / safe
        path.unlink(missing_ok=True)
        path.with_suffix(path.suffix + ".metadata.json").unlink(missing_ok=True)
        return EvidenceOutcome(False, "deleted", self.provider_id, object_path)

    def reviewer_access_url(self, object_path: str, *, ttl_seconds: int = 300) -> EvidenceOutcome:
        safe = Path(object_path)
        if safe.is_absolute() or ".." in safe.parts:
            return EvidenceOutcome(False, "failed", self.provider_id, object_path, error_code="invalid_evidence_path")
        return EvidenceOutcome(
            True,
            "stored",
            self.provider_id,
            object_path,
            metadata={"local_path": str((self.root / safe).resolve()), "ttl_seconds": min(ttl_seconds, 300)},
        )


class SupabaseEvidenceProvider(EvidenceProvider):
    provider_id = "supabase_storage"

    def _configured(self) -> bool:
        return bool(SETTINGS.supabase_url and SETTINGS.supabase_service_role_key and SETTINGS.evidence_supabase_bucket)

    def retain_raw_clip(
        self,
        *,
        source_path: Path,
        user_id: str,
        analysis_session_id: str,
        consent_version: str,
        media_type: str,
        retention_days: int,
    ) -> EvidenceOutcome:
        if not self._configured():
            return EvidenceOutcome(False, "failed", self.provider_id, error_code="supabase_storage_not_configured")
        created = _utc_now()
        expires = created + timedelta(days=max(1, retention_days))
        digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        object_path = f"{user_id}/{analysis_session_id}/{secrets.token_urlsafe(24)}{source_path.suffix.lower()}"
        encoded_path = urllib.parse.quote(object_path)
        url = f"{SETTINGS.supabase_url.rstrip('/')}/storage/v1/object/{SETTINGS.evidence_supabase_bucket}/{encoded_path}"
        request = urllib.request.Request(
            url,
            data=source_path.read_bytes(),
            method="POST",
            headers={
                "authorization": f"Bearer {SETTINGS.supabase_service_role_key}",
                "apikey": SETTINGS.supabase_service_role_key or "",
                "content-type": media_type,
                "x-upsert": "false",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=SETTINGS.persistence_timeout_seconds):
                pass
        except urllib.error.HTTPError as exc:
            return EvidenceOutcome(False, "failed", self.provider_id, object_path, error_code=f"supabase_storage_http_{exc.code}")
        except Exception:
            return EvidenceOutcome(False, "temporary_failure", self.provider_id, object_path, error_code="supabase_storage_failed")
        return EvidenceOutcome(
            True,
            "stored",
            self.provider_id,
            object_path,
            {
                "storage_provider": self.provider_id,
                "bucket": SETTINGS.evidence_supabase_bucket,
                "object_public": False,
                "object_name_randomized": True,
                "checksum_sha256": digest,
                "media_type": media_type,
                "byte_count": source_path.stat().st_size,
                "created_at": _iso(created),
                "retention_expires_at": _iso(expires),
                "user_id": user_id,
                "analysis_session_id": analysis_session_id,
                "consent_version": consent_version,
                "raw_clip_retained": True,
                "processed_evidence_retained": False,
                "reviewer_access": "short_lived_signed_url_required",
            },
        )

    def delete(self, object_path: str) -> EvidenceOutcome:
        if not self._configured():
            return EvidenceOutcome(False, "failed", self.provider_id, object_path, error_code="supabase_storage_not_configured")
        encoded_path = urllib.parse.quote(object_path)
        url = f"{SETTINGS.supabase_url.rstrip('/')}/storage/v1/object/{SETTINGS.evidence_supabase_bucket}/{encoded_path}"
        request = urllib.request.Request(
            url,
            method="DELETE",
            headers={"authorization": f"Bearer {SETTINGS.supabase_service_role_key}", "apikey": SETTINGS.supabase_service_role_key or ""},
        )
        try:
            with urllib.request.urlopen(request, timeout=SETTINGS.persistence_timeout_seconds):
                pass
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                return EvidenceOutcome(False, "temporary_failure", self.provider_id, object_path, error_code=f"supabase_storage_http_{exc.code}")
        except Exception:
            return EvidenceOutcome(False, "temporary_failure", self.provider_id, object_path, error_code="supabase_storage_failed")
        return EvidenceOutcome(False, "deleted", self.provider_id, object_path)


def get_evidence_provider() -> EvidenceProvider:
    backend = (SETTINGS.evidence_storage_backend or "none").strip().lower()
    if backend == "local":
        return LocalEvidenceProvider()
    if backend == "supabase":
        return SupabaseEvidenceProvider()
    return EvidenceProvider()
