"""Phase 6.7 — build ``dataset_manifest.json`` for ML-ready artifacts in ``ml/data/final/``.

Read-only: validates expected files and reads shapes/metadata. Does not modify arrays
or regenerate splits.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def _ml_root(script_path: Path) -> Path:
    return script_path.resolve().parents[2]


def _file_kind(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".npy": "numpy_array",
        ".json": "json",
        ".csv": "csv",
        ".md": "markdown",
        ".pkl": "joblib_pickle",
    }.get(ext, "unknown")


DATASET_NAME = "smart_cricket_shot_classification_engineered_features"
DATASET_VERSION = "6.7.0"

# Filenames that must exist for the manifest to be written.
REQUIRED_FILES: dict[str, str] = {
    "X.npy": "Full feature matrix; rows align with y.npy.",
    "y.npy": "Encoded class labels for all samples.",
    "X_train.npy": "Training split features.",
    "X_val.npy": "Validation split features.",
    "X_test.npy": "Test split features.",
    "y_train.npy": "Training split labels.",
    "y_val.npy": "Validation split labels.",
    "y_test.npy": "Test split labels.",
    "feature_schema.json": "Feature column contract and schema metadata.",
    "label_mapping.json": "Integer index ↔ shot name mapping.",
    "split_metadata.json": "Split sizes, strategy, and reproducibility fields.",
    "final_dataset_report.md": "Phase 6.6 validation report.",
    "dataset_index.csv": "Full dataset row index / traceability.",
    "train_index.csv": "Training split row index.",
    "val_index.csv": "Validation split row index.",
    "test_index.csv": "Test split row index.",
}

# Documented if present (not required for validation pass).
OPTIONAL_FILES: dict[str, str] = {
    "label_encoder.pkl": "Fitted sklearn LabelEncoder for shot_label.",
    "dataset_manifest.json": "This manifest (rewritten each run).",
}


def main() -> int:
    root = _ml_root(Path(__file__))
    final_dir = root / "data" / "final"
    manifest_path = final_dir / "dataset_manifest.json"

    missing: list[str] = []
    for fname in sorted(REQUIRED_FILES):
        p = final_dir / fname
        if not p.is_file():
            missing.append(p.relative_to(root).as_posix())

    if missing:
        print("──────── Dataset manifest (Phase 6.7) ────────")
        print("validation passed: False")
        print(f"total artifacts registered: 0")
        print(f"dataset version:              {DATASET_VERSION}")
        print(f"manifest path (not written):  {manifest_path}")
        print("Missing required files:")
        for m in missing:
            print(f"  - {m}")
        return 1

    # --- Load factual fields (read-only) ---
    X = np.load(final_dir / "X.npy", mmap_mode="r")
    total_samples = int(X.shape[0])
    num_features = int(X.shape[1])

    with (final_dir / "feature_schema.json").open(encoding="utf-8") as f:
        feature_schema = json.load(f)

    nfs = int(feature_schema.get("num_features", -1))
    if nfs >= 0 and nfs != num_features:
        print(
            f"WARNING: X.npy columns ({num_features}) != feature_schema num_features ({nfs}).",
            file=sys.stderr,
        )

    with (final_dir / "label_mapping.json").open(encoding="utf-8") as f:
        label_mapping = json.load(f)
    index_to_class: dict[str, str] = label_mapping.get("index_to_class") or {}
    class_names = sorted(set(index_to_class.values()))
    num_classes = len(class_names)

    with (final_dir / "split_metadata.json").open(encoding="utf-8") as f:
        split_meta = json.load(f)
    split_strategy = str(split_meta.get("split_strategy", ""))
    ss = split_meta.get("split_sizes") or {}
    split_sizes = {
        "train": int(ss.get("train", 0)),
        "validation": int(ss.get("validation", ss.get("val", 0))),
        "test": int(ss.get("test", 0)),
    }

    split_sum = split_sizes["train"] + split_sizes["validation"] + split_sizes["test"]
    if split_sum != total_samples:
        print(
            f"WARNING: split_sizes sum ({split_sum}) != total_samples ({total_samples}).",
            file=sys.stderr,
        )

    # --- Artifact registry ---
    registry_sources: dict[str, str] = {**REQUIRED_FILES, **OPTIONAL_FILES}
    artifact_registry: list[dict[str, str]] = []

    for fname, purpose in sorted(registry_sources.items()):
        path = final_dir / fname
        if path.is_file():
            artifact_registry.append(
                {
                    "relative_path": path.relative_to(root).as_posix(),
                    "purpose": purpose,
                    "file_type": _file_kind(path),
                }
            )

    for path in sorted(final_dir.iterdir()):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(entry["relative_path"] == rel for entry in artifact_registry):
            continue
        artifact_registry.append(
            {
                "relative_path": rel,
                "purpose": "Present under ml/data/final/ (add description if promoted to first-class artifact).",
                "file_type": _file_kind(path),
            }
        )

    artifact_registry.sort(key=lambda d: d["relative_path"])

    mrp = manifest_path.relative_to(root).as_posix()
    if not any(e["relative_path"] == mrp for e in artifact_registry):
        artifact_registry.append(
            {
                "relative_path": mrp,
                "purpose": OPTIONAL_FILES["dataset_manifest.json"],
                "file_type": _file_kind(manifest_path),
            }
        )
        artifact_registry.sort(key=lambda d: d["relative_path"])

    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    manifest = {
        "dataset_name": DATASET_NAME,
        "dataset_version": DATASET_VERSION,
        "created_at": created_at,
        "total_samples": total_samples,
        "num_features": num_features,
        "num_classes": num_classes,
        "class_names": class_names,
        "split_sizes": split_sizes,
        "split_strategy": split_strategy,
        "feature_schema_path": (
            final_dir / "feature_schema.json"
        ).relative_to(root).as_posix(),
        "label_mapping_path": (
            final_dir / "label_mapping.json"
        ).relative_to(root).as_posix(),
        "dataset_report_path": (
            final_dir / "final_dataset_report.md"
        ).relative_to(root).as_posix(),
        "artifact_registry": artifact_registry,
        "notes": (
            "Paths in artifact_registry use POSIX paths relative to the ml/ project root "
            "(the directory containing data/). This manifest is regenerated by rerunning "
            "create_dataset_manifest.py; it does not alter dataset arrays."
        ),
        "future_phase_dependencies": [
            "Training: load X_train.npy/y_train.npy (and optionally val) with feature_schema ordering.",
            "Evaluation: freeze test arrays; report metrics against y_test decoded via label_mapping.json.",
            "Inference: reconstruct the 32-D vector consistent with feature_schema; apply label_encoder before metrics.",
            "If features.csv or splits change upstream, rerun Phase 6.6 validation and regenerate this manifest.",
        ],
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as mj:
        json.dump(manifest, mj, indent=2)

    n_reg = len(artifact_registry)

    print("──────── Dataset manifest (Phase 6.7) ────────")
    print("validation passed:        True")
    print(f"total artifacts registered: {n_reg}")
    print(f"dataset version:           {DATASET_VERSION}")
    print(f"manifest path:             {manifest_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
