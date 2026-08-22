"""Non-secret runtime diagnostics for Smart Cricket API operators.

Run with ``python -m backend.api.diagnostics`` after installing both runtime
requirements files.  MediaPipe initialization is probed in a child process so
an unstable native delegate cannot take down the diagnostics command itself.
"""

from __future__ import annotations

import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from .config import APISettings
from ml.src.inference.inference_config import DATASET_DIR, PHASE10_TEMPLATE_PATH, PHASE8_BEST_MODEL_DIR
from ml.src.preprocessing.extract_pose import POSE_LANDMARKER_MODEL_ASSET_PATH, pose_model_status


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _path_status(path: Path) -> dict[str, Any]:
    return {"path": str(path), "exists": path.is_file(), "size_bytes": path.stat().st_size if path.is_file() else None}


def _mediapipe_probe(delegate: str) -> dict[str, Any]:
    code = (
        "from ml.src.preprocessing.extract_pose import create_pose_landmarker; "
        "landmarker=create_pose_landmarker('" + delegate + "'); landmarker.close(); print('ok')"
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-c", code],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        return {"available": False, "reason": "probe_timed_out"}
    return {
        "available": completed.returncode == 0,
        "return_code": completed.returncode,
        "stderr_tail": completed.stderr.strip().splitlines()[-1:] or None,
    }


def collect_diagnostics() -> dict[str, Any]:
    """Collect package, artifact, and native-backend readiness facts."""

    settings = APISettings()
    cv2_status: dict[str, Any]
    try:
        import cv2

        cv2_status = {"available": hasattr(cv2, "VideoCapture"), "version": getattr(cv2, "__version__", None)}
    except Exception as exc:
        cv2_status = {"available": False, "error": type(exc).__name__}
    torch_status: dict[str, Any]
    try:
        import torch

        torch_status = {
            "available": True,
            "version": torch.__version__,
            "cuda_available": bool(torch.cuda.is_available()),
            "mps_available": bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()),
        }
    except Exception as exc:
        torch_status = {"available": False, "error": type(exc).__name__}

    delegate = settings.mediapipe_delegate
    probe_delegate = "cpu" if delegate == "auto" else delegate
    return {
        "python": {"version": sys.version.split()[0], "implementation": platform.python_implementation()},
        "platform": {"system": platform.system(), "machine": platform.machine()},
        "packages": {name: _package_version(name) for name in ("fastapi", "uvicorn", "mediapipe", "opencv-contrib-python", "torch", "pandas", "scikit-learn", "cryptography")},
        "opencv": cv2_status,
        "torch": torch_status,
        "mediapipe": {"configured_delegate": delegate, "probe": _mediapipe_probe(probe_delegate)},
        "model_files": {
            "pose_landmarker": pose_model_status(),
            "checkpoint": _path_status(PHASE8_BEST_MODEL_DIR / "checkpoint.pt"),
            "scaler": _path_status(PHASE8_BEST_MODEL_DIR / "scaler" / "scaler_metadata.json"),
            "feature_schema": _path_status(DATASET_DIR / "temporal_feature_schema.json"),
            "label_mapping": _path_status(DATASET_DIR / "temporal_label_mapping.json"),
            "technique_templates": _path_status(PHASE10_TEMPLATE_PATH),
        },
    }


def main() -> int:
    print(json.dumps(collect_diagnostics(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
