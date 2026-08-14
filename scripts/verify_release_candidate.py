"""Quick release-candidate configuration check for Smart Cricket."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.api.config import SETTINGS, validate_runtime_settings
from backend.api.services import _auth_config_ready, _audio_config_ready, _rate_limit_config_ready
from backend.api.tts import google_tts_credentials_hint_available
from ml.src.inference.inference_config import DATASET_DIR, PHASE10_TEMPLATE_PATH, PHASE8_BEST_MODEL_DIR
from ml.src.preprocessing.extract_pose import POSE_LANDMARKER_MODEL_ASSET_PATH


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def _pass(condition: bool, name: str, detail: str) -> Check:
    return Check(name, "PASS" if condition else "FAIL", detail)


def run_checks() -> list[Check]:
    strict_issues = validate_runtime_settings(SETTINGS)
    checks = [
        Check("Environment", "PASS", SETTINGS.environment),
        _pass(
            all(
                [
                    (PHASE8_BEST_MODEL_DIR / "checkpoint.pt").is_file(),
                    (PHASE8_BEST_MODEL_DIR / "scaler" / "feature_mean.npy").is_file(),
                    (PHASE8_BEST_MODEL_DIR / "scaler" / "feature_std.npy").is_file(),
                    (DATASET_DIR / "temporal_feature_schema.json").is_file(),
                    (DATASET_DIR / "temporal_label_mapping.json").is_file(),
                    PHASE10_TEMPLATE_PATH.is_file(),
                    POSE_LANDMARKER_MODEL_ASSET_PATH.is_file(),
                ]
            ),
            "Inference assets",
            "checkpoint, scaler, schemas, templates, and pose model",
        ),
        _pass(_auth_config_ready(), "Authentication", "auth optional or verifier configured"),
        _pass(bool(SETTINGS.supabase_url and SETTINGS.supabase_service_role_key) or SETTINGS.environment in {"development", "test"}, "Persistence", "Supabase trusted persistence or local mode"),
        _pass(
            (not SETTINGS.allow_model_improvement_participation)
            or (SETTINGS.evidence_storage_backend == "supabase" and bool(SETTINGS.evidence_supabase_bucket)),
            "Evidence storage",
            "disabled or private Supabase evidence bucket configured",
        ),
        _tts_check(),
        _audio_check(),
        _pass(_rate_limit_config_ready(), "Rate limiting", SETTINGS.rate_limit_backend),
        _pass(_audio_config_ready(), "Signed audio access", "signing secret configured or local mode"),
        Check("Observability", "PASS" if SETTINGS.sentry_dsn or SETTINGS.environment in {"development", "test", "staging"} else "SKIPPED_EXTERNAL_CREDENTIAL", "Sentry optional unless production policy requires it"),
        Check("Production config", "PASS" if not strict_issues else "FAIL", "; ".join(issue.code for issue in strict_issues) or "runtime settings valid"),
    ]
    return checks


def _tts_check() -> Check:
    provider = SETTINGS.tts_provider.strip().lower() if SETTINGS.tts_enabled else "text_only"
    if provider in {"text", "text_only", "none", "disabled"} or not SETTINGS.tts_enabled:
        return Check("TTS provider", "CONFIGURED", "text-only graceful fallback")
    if provider == "google":
        if google_tts_credentials_hint_available():
            return Check("TTS provider", "CONFIGURED", "Google selected; live synthesis still requires safe smoke test")
        return Check("TTS provider", "SKIPPED_EXTERNAL_CREDENTIAL", "Google selected but ADC/project hint not present")
    if provider in {"local", "development", "macos"}:
        status = "CONFIGURED" if SETTINGS.environment in {"development", "test"} else "FAIL"
        return Check("TTS provider", status, "local development provider")
    return Check("TTS provider", "FAIL", "unsupported provider")


def _audio_check() -> Check:
    backend = SETTINGS.audio_storage_backend.strip().lower()
    if backend == "local":
        return Check("Audio storage", "PASS" if SETTINGS.environment in {"development", "test"} else "FAIL", "local development storage")
    if backend == "supabase":
        ok = bool(SETTINGS.supabase_url and SETTINGS.supabase_service_role_key and SETTINGS.audio_supabase_bucket)
        return Check("Audio storage", "PASS" if ok else "FAIL", "private Supabase audio bucket")
    return Check("Audio storage", "FAIL", "unsupported backend")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Smart Cricket release-candidate runtime configuration.")
    parser.add_argument("--json", action="store_true", help="Emit JSON without secrets.")
    args = parser.parse_args()
    checks = run_checks()
    failed = [check for check in checks if check.status == "FAIL"]
    if args.json:
        print(json.dumps({"checks": [asdict(check) for check in checks], "ok": not failed}, sort_keys=True))
    else:
        print("Smart Cricket Release Candidate Check\n")
        for check in checks:
            print(f"{check.name:<24} {check.status:<28} {check.detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
