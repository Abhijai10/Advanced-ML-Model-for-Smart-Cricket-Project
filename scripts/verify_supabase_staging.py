#!/usr/bin/env python3
"""Verify a live Supabase staging project for Smart Cricket."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from uuid import uuid4


MARKER = "smart_cricket_staging_verification"
REQUIRED_TABLES = ("profiles", "analysis_sessions", "shot_timeline_events", "analysis_feedback", "product_feedback")


@dataclass
class VerificationConfig:
    supabase_url: str | None
    service_role_key: str | None
    publishable_key: str | None
    evidence_bucket: str | None
    user_a_id: str | None
    user_a_token: str | None
    user_b_id: str | None
    user_b_token: str | None

    @classmethod
    def from_env(cls) -> "VerificationConfig":
        return cls(
            supabase_url=os.getenv("SUPABASE_URL"),
            service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
            publishable_key=os.getenv("SUPABASE_PUBLISHABLE_KEY"),
            evidence_bucket=os.getenv("SMART_CRICKET_EVIDENCE_SUPABASE_BUCKET"),
            user_a_id=os.getenv("SMART_CRICKET_STAGING_TEST_USER_A_ID"),
            user_a_token=os.getenv("SMART_CRICKET_STAGING_TEST_USER_A_TOKEN"),
            user_b_id=os.getenv("SMART_CRICKET_STAGING_TEST_USER_B_ID"),
            user_b_token=os.getenv("SMART_CRICKET_STAGING_TEST_USER_B_TOKEN"),
        )


@dataclass
class Check:
    name: str
    status: str
    detail: str = ""


class SupabaseVerifier:
    def __init__(self, config: VerificationConfig, *, dry_run: bool = False) -> None:
        self.config = config
        self.dry_run = dry_run
        self.run_id = uuid4().hex
        self.created_analysis_id: str | None = None
        self.created_feedback_id: str | None = None
        self.created_product_feedback_id: str | None = None
        self.created_object_path: str | None = None
        self.cleanup_warnings: list[str] = []

    def run(self) -> list[Check]:
        checks = [
            self._connectivity(),
            self._schema(),
            self._trusted_insert(),
            self._user_isolation(),
            self._feedback(),
            self._product_feedback(),
            self._storage(),
        ]
        checks.append(self._cleanup())
        return checks

    def _connectivity(self) -> Check:
        if not self._has_service_config():
            return Check("Connectivity", "FAIL", "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
        rest = self._request("GET", "/rest/v1/", service=True)
        storage = self._request("GET", "/storage/v1/bucket", service=True)
        if rest[0] < 500 and storage[0] < 500:
            return Check("Connectivity", "PASS", "REST and Storage APIs responded")
        return Check("Connectivity", "FAIL", f"REST HTTP {rest[0]}, Storage HTTP {storage[0]}")

    def _schema(self) -> Check:
        if not self._has_service_config():
            return Check("Schema", "FAIL", "service credentials missing")
        missing = []
        for table in REQUIRED_TABLES:
            status, _payload = self._request("GET", f"/rest/v1/{table}?select=*&limit=1", service=True)
            if status >= 400:
                missing.append(f"{table}:HTTP{status}")
        if missing:
            return Check("Schema", "FAIL", ", ".join(missing))
        return Check("Schema", "PASS", "required tables are reachable through REST")

    def _trusted_insert(self) -> Check:
        if not self._has_service_config():
            return Check("Trusted insert", "FAIL", "service credentials missing")
        if not self.config.user_a_id:
            return Check("Trusted insert", "SKIPPED_EXTERNAL_CREDENTIAL", "SMART_CRICKET_STAGING_TEST_USER_A_ID is required")
        if self.dry_run:
            return Check("Trusted insert", "DRY_RUN", "would insert/read/delete marked analysis row")
        analysis_id = str(uuid4())
        row = {
            "id": analysis_id,
            "user_id": self.config.user_a_id,
            "video_file_name": f"{MARKER}_{self.run_id}.webm",
            "predicted_shot": "cover_drive",
            "shot_confidence": 0.8,
            "technique_match_score": 75,
            "shot_start_frame": 1,
            "shot_end_frame": 30,
            "shot_duration_seconds": 1.2,
            "spoken_feedback": MARKER,
            "coaching_tips": [MARKER],
            "full_result": {"marker": MARKER, "run_id": self.run_id},
            "request_id": self.run_id,
            "clip_hash": "a" * 64,
            "model_version": "staging-verification",
            "pipeline_version": "staging-verification",
            "model_provenance": {"marker": MARKER},
            "storage_status": "not_retained",
            "persistence_source": "server_verified_inference",
        }
        status, payload = self._request("POST", "/rest/v1/analysis_sessions", row, service=True, prefer="return=representation")
        if status not in {200, 201}:
            return Check("Trusted insert", "FAIL", f"insert HTTP {status}")
        self.created_analysis_id = analysis_id
        read_status, read_payload = self._request("GET", f"/rest/v1/analysis_sessions?id=eq.{analysis_id}&select=*", service=True)
        if read_status == 200 and isinstance(read_payload, list) and read_payload:
            return Check("Trusted insert", "PASS", "inserted and read back marked analysis")
        return Check("Trusted insert", "FAIL", f"readback HTTP {read_status}")

    def _user_isolation(self) -> Check:
        if not (self.config.publishable_key and self.config.user_a_token and self.config.user_b_token and self.created_analysis_id):
            return Check("User isolation", "SKIPPED_EXTERNAL_CREDENTIAL", "requires publishable key, two user tokens, and trusted insert")
        own_status, own_payload = self._request(
            "GET",
            f"/rest/v1/analysis_sessions?id=eq.{self.created_analysis_id}&select=*",
            bearer=self.config.user_a_token,
            apikey=self.config.publishable_key,
        )
        other_status, other_payload = self._request(
            "GET",
            f"/rest/v1/analysis_sessions?id=eq.{self.created_analysis_id}&select=*",
            bearer=self.config.user_b_token,
            apikey=self.config.publishable_key,
        )
        deny_status, _ = self._request(
            "POST",
            "/rest/v1/analysis_sessions",
            {"user_id": self.config.user_a_id, "video_file_name": f"{MARKER}.webm"},
            bearer=self.config.user_a_token,
            apikey=self.config.publishable_key,
        )
        own_ok = own_status == 200 and isinstance(own_payload, list) and len(own_payload) == 1
        other_ok = other_status == 200 and isinstance(other_payload, list) and len(other_payload) == 0
        deny_ok = deny_status in {401, 403, 404, 405}
        return Check("User isolation", "PASS" if own_ok and other_ok and deny_ok else "FAIL", f"own={own_status} other={other_status} write={deny_status}")

    def _feedback(self) -> Check:
        if not self.created_analysis_id or not self.config.user_a_id:
            return Check("Feedback", "SKIPPED_EXTERNAL_CREDENTIAL", "requires trusted analysis row")
        if self.dry_run:
            return Check("Feedback", "DRY_RUN", "would insert metadata-only analysis feedback")
        row = {
            "user_id": self.config.user_a_id,
            "analysis_session_id": self.created_analysis_id,
            "clip_hash": "a" * 64,
            "predicted_shot": "cover_drive",
            "prediction_was_correct": "unsure",
            "tip_flags": ["useful"],
            "notes": MARKER,
            "consent_to_model_improvement": False,
            "accepted_for_review": False,
            "review_status": "metadata_only",
            "model_version": "staging-verification",
            "pipeline_version": "staging-verification",
            "request_id": self.run_id,
            "auth_present": True,
            "provenance": {"marker": MARKER},
            "storage_status": "not_retained",
            "dataset_eligibility_status": "not_eligible",
        }
        status, payload = self._request("POST", "/rest/v1/analysis_feedback", row, service=True, prefer="return=representation")
        if status not in {200, 201}:
            return Check("Feedback", "FAIL", f"insert HTTP {status}")
        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            self.created_feedback_id = str(payload[0].get("id") or "")
        return Check("Feedback", "PASS", "metadata-only feedback inserted")

    def _product_feedback(self) -> Check:
        if not self._has_service_config() or not self.config.user_a_id:
            return Check("Product feedback", "SKIPPED_EXTERNAL_CREDENTIAL", "requires service credentials and test user id")
        if self.dry_run:
            return Check("Product feedback", "DRY_RUN", "would insert product feedback")
        row = {
            "user_id": self.config.user_a_id,
            "usability_rating": 4,
            "bug_category": "staging_verification",
            "feature_request": MARKER,
            "notes": f"{MARKER}:{self.run_id}",
            "page_context": "staging",
            "request_id": self.run_id,
        }
        status, payload = self._request("POST", "/rest/v1/product_feedback", row, service=True, prefer="return=representation")
        if status not in {200, 201}:
            return Check("Product feedback", "FAIL", f"insert HTTP {status}")
        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            self.created_product_feedback_id = str(payload[0].get("id") or "")
        return Check("Product feedback", "PASS", "product feedback inserted")

    def _storage(self) -> Check:
        if not self._has_service_config() or not self.config.evidence_bucket:
            return Check("Storage upload", "SKIPPED_EXTERNAL_CREDENTIAL", "requires service credentials and SMART_CRICKET_EVIDENCE_SUPABASE_BUCKET")
        if self.dry_run:
            return Check("Storage upload", "DRY_RUN", "would upload/sign/download/delete generated test bytes")
        object_path = f"{MARKER}/{self.run_id}.txt"
        self.created_object_path = object_path
        upload_status, _ = self._storage_request("POST", f"/storage/v1/object/{self.config.evidence_bucket}/{object_path}", b"staging-verification")
        sign_status, signed = self._request("POST", f"/storage/v1/object/sign/{self.config.evidence_bucket}/{object_path}", {"expiresIn": 60}, service=True)
        delete_status, _ = self._request("DELETE", f"/storage/v1/object/{self.config.evidence_bucket}/{object_path}", service=True)
        ok = upload_status in {200, 201} and sign_status in {200, 201} and delete_status in {200, 204}
        return Check("Storage upload", "PASS" if ok else "FAIL", f"upload={upload_status} sign={sign_status} delete={delete_status}")

    def _cleanup(self) -> Check:
        if self.dry_run:
            return Check("Cleanup", "DRY_RUN", "no writes performed")
        for table, record_id in (
            ("analysis_feedback", self.created_feedback_id),
            ("product_feedback", self.created_product_feedback_id),
            ("analysis_sessions", self.created_analysis_id),
        ):
            if not record_id:
                continue
            status, _ = self._request("DELETE", f"/rest/v1/{table}?id=eq.{record_id}", service=True)
            if status not in {200, 204}:
                self.cleanup_warnings.append(f"{table}:{record_id}:HTTP{status}")
        if self.created_object_path and self.config.evidence_bucket:
            status, _ = self._request("DELETE", f"/storage/v1/object/{self.config.evidence_bucket}/{self.created_object_path}", service=True)
            if status not in {200, 204, 404}:
                self.cleanup_warnings.append(f"storage:{self.created_object_path}:HTTP{status}")
        if self.cleanup_warnings:
            return Check("Cleanup", "FAIL", "; ".join(self.cleanup_warnings))
        return Check("Cleanup", "PASS", "created records/objects removed or none created")

    def _has_service_config(self) -> bool:
        return bool(self.config.supabase_url and self.config.service_role_key)

    def _request(
        self,
        method: str,
        path: str,
        payload: object | None = None,
        *,
        service: bool = False,
        bearer: str | None = None,
        apikey: str | None = None,
        prefer: str | None = None,
    ) -> tuple[int, object]:
        assert self.config.supabase_url
        key = self.config.service_role_key if service else apikey
        headers = {"accept": "application/json", "apikey": key or ""}
        if service:
            headers["authorization"] = f"Bearer {self.config.service_role_key}"
        elif bearer:
            headers["authorization"] = f"Bearer {bearer}"
        if prefer:
            headers["prefer"] = prefer
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["content-type"] = "application/json"
        request = urllib.request.Request(f"{self.config.supabase_url.rstrip('/')}{path}", data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = response.read().decode("utf-8") or "null"
                return int(response.status), json.loads(body)
        except urllib.error.HTTPError as exc:
            return int(exc.code), {"error": "http_error"}
        except Exception:
            return 599, {"error": "request_failed"}

    def _storage_request(self, method: str, path: str, payload: bytes) -> tuple[int, object]:
        assert self.config.supabase_url
        headers = {
            "apikey": self.config.service_role_key or "",
            "authorization": f"Bearer {self.config.service_role_key}",
            "content-type": "application/octet-stream",
        }
        request = urllib.request.Request(f"{self.config.supabase_url.rstrip('/')}{path}", data=payload, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = response.read().decode("utf-8") or "null"
                try:
                    return int(response.status), json.loads(body)
                except json.JSONDecodeError:
                    return int(response.status), {}
        except urllib.error.HTTPError as exc:
            return int(exc.code), {"error": "http_error"}
        except Exception:
            return 599, {"error": "request_failed"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Validate config and describe operations without writes.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()
    verifier = SupabaseVerifier(VerificationConfig.from_env(), dry_run=args.dry_run)
    checks = verifier.run()
    if args.json:
        print(json.dumps([check.__dict__ for check in checks], indent=2, sort_keys=True))
    else:
        print("Smart Cricket Supabase Staging Verification")
        print()
        for check in checks:
            print(f"{check.name:.<28} {check.status}  {check.detail}")
    return 1 if any(check.status == "FAIL" for check in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
