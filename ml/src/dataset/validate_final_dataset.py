"""Phase 6.6 — cross-check all Phase 6 ``ml/data/final/`` artifacts and write a report.

Read-only: does not modify ``.npy`` files, CSVs, or JSON. Does not resplit or train.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def _ml_root(script_path: Path) -> Path:
    return script_path.resolve().parents[2]


def _class_distribution_from_y(
    y_arr: np.ndarray,
    index_to_class: dict[str, str],
    errors: list[str],
    context: str,
) -> dict[str, int]:
    """Count string class names for encoded ``y``; unknown codes become validation errors."""
    counts: Counter[str] = Counter()
    for v in np.asarray(y_arr).flat:
        key = str(int(v))
        if key not in index_to_class:
            errors.append(f"{context}: unknown encoded label {key} (not in label_mapping).")
            continue
        counts[index_to_class[key]] += 1
    return dict(sorted(counts.items()))


def _fmt_dist(d: dict[str, int]) -> str:
    lines = [f"- **{k}**: {v}" for k, v in d.items()]
    return "\n".join(lines) if lines else "(empty)"


def main() -> int:
    root = _ml_root(Path(__file__))
    final_dir = root / "data" / "final"
    report_path = final_dir / "final_dataset_report.md"

    errors: list[str] = []
    warnings: list[str] = []

    paths = {
        "X.npy": final_dir / "X.npy",
        "y.npy": final_dir / "y.npy",
        "feature_schema.json": final_dir / "feature_schema.json",
        "label_encoder.pkl": final_dir / "label_encoder.pkl",
        "label_mapping.json": final_dir / "label_mapping.json",
        "dataset_index.csv": final_dir / "dataset_index.csv",
        "X_train.npy": final_dir / "X_train.npy",
        "X_val.npy": final_dir / "X_val.npy",
        "X_test.npy": final_dir / "X_test.npy",
        "y_train.npy": final_dir / "y_train.npy",
        "y_val.npy": final_dir / "y_val.npy",
        "y_test.npy": final_dir / "y_test.npy",
        "train_index.csv": final_dir / "train_index.csv",
        "val_index.csv": final_dir / "val_index.csv",
        "test_index.csv": final_dir / "test_index.csv",
        "split_metadata.json": final_dir / "split_metadata.json",
    }

    for name, p in paths.items():
        if not p.is_file():
            errors.append(f"Missing file: {name} ({p})")

    if errors:
        _write_report_minimal(report_path, errors)
        print("──────── Final dataset validation (Phase 6.6) ────────")
        print("validation passed: False")
        print(f"report path: {report_path}")
        for e in errors:
            print(f"  ERROR: {e}")
        return 1

    # --- Load JSON (read-only) ---
    with paths["feature_schema.json"].open(encoding="utf-8") as f:
        schema = json.load(f)
    with paths["label_mapping.json"].open(encoding="utf-8") as f:
        label_mapping = json.load(f)
    with paths["split_metadata.json"].open(encoding="utf-8") as f:
        split_meta = json.load(f)

    index_to_class: dict[str, str] = label_mapping.get("index_to_class") or {}
    class_names = sorted(index_to_class.values())
    expected_indices = {int(k) for k in index_to_class}

    # --- Full X, y ---
    X = np.load(paths["X.npy"], mmap_mode="r")
    y = np.load(paths["y.npy"], mmap_mode="r")

    if X.ndim != 2:
        errors.append(f"X.npy must be 2D; got shape {X.shape}.")
    if y.ndim != 1:
        errors.append(f"y.npy must be 1D; got shape {y.shape}.")
    if X.ndim == 2 and y.ndim == 1 and X.shape[0] != y.shape[0]:
        errors.append(
            f"X rows ({X.shape[0]}) != y rows ({y.shape[0]}).",
        )

    if X.ndim == 2:
        if np.isnan(np.asarray(X)).any():
            errors.append("Full X contains NaN.")
        if not np.isfinite(np.asarray(X)).all():
            errors.append("Full X contains non-finite value(s).")

    nf_schema = int(schema.get("num_features", -1))
    n_feat_cols = len(schema.get("feature_columns", []))
    if nf_schema >= 0 and X.ndim == 2 and X.shape[1] != nf_schema:
        errors.append(
            f"X feature count ({X.shape[1]}) != feature_schema num_features ({nf_schema}).",
        )
    if n_feat_cols >= 0 and nf_schema >= 0 and n_feat_cols != nf_schema:
        errors.append(
            f"feature_schema num_features ({nf_schema}) != len(feature_columns) ({n_feat_cols}).",
        )

    # Label validity (full y)
    y_full = np.asarray(y)
    unknown: set[int] = set()
    if y_full.size:
        uniq = {int(v) for v in np.unique(y_full)}
        unknown = uniq - expected_indices
        if unknown:
            errors.append(f"y contains unknown class index(es): {sorted(unknown)}")

    dist_full = _class_distribution_from_y(y_full, index_to_class, errors, "y.npy")

    # Full dataset index row count vs X
    n_idx_full = len(pd.read_csv(paths["dataset_index.csv"]))
    if X.ndim == 2 and n_idx_full != X.shape[0]:
        errors.append(
            f"dataset_index.csv rows ({n_idx_full}) != X rows ({X.shape[0]}).",
        )

    # --- Splits ---
    X_train = np.load(paths["X_train.npy"], mmap_mode="r")
    X_val = np.load(paths["X_val.npy"], mmap_mode="r")
    X_test = np.load(paths["X_test.npy"], mmap_mode="r")
    y_train = np.load(paths["y_train.npy"], mmap_mode="r")
    y_val = np.load(paths["y_val.npy"], mmap_mode="r")
    y_test = np.load(paths["y_test.npy"], mmap_mode="r")

    splits = [
        ("train", X_train, y_train, paths["train_index.csv"]),
        ("val", X_val, y_val, paths["val_index.csv"]),
        ("test", X_test, y_test, paths["test_index.csv"]),
    ]

    n_features_full = int(X.shape[1]) if X.ndim == 2 else -1

    for name, Xs, ys, idx_csv in splits:
        Xa = np.asarray(Xs)
        ya = np.asarray(ys)
        if Xa.ndim != 2:
            errors.append(f"{name}: X_{name} is not 2D (shape {Xa.shape}).")
            continue
        if ya.ndim != 1:
            errors.append(f"{name}: y_{name} is not 1D (shape {ya.shape}).")
            continue
        if Xa.shape[0] != ya.shape[0]:
            errors.append(
                f"{name}: X rows ({Xa.shape[0]}) != y rows ({ya.shape[0]}).",
            )
        if n_features_full >= 0 and Xa.shape[1] != n_features_full:
            errors.append(
                f"{name}: feature dimension {Xa.shape[1]} != full X ({n_features_full}).",
            )
        if np.isnan(Xa).any():
            errors.append(f"{name}: X split contains NaN.")
        if not np.isfinite(Xa).all():
            errors.append(f"{name}: X split contains non-finite value(s).")

        dfc = pd.read_csv(idx_csv)
        if len(dfc) != Xa.shape[0]:
            errors.append(
                f"{name}: index CSV rows ({len(dfc)}) != X_{name} rows ({Xa.shape[0]}).",
            )

    n_full = int(X.shape[0]) if X.ndim >= 1 else 0
    n_tr, n_va, n_te = len(y_train), len(y_val), len(y_test)
    if n_tr + n_va + n_te != n_full:
        errors.append(
            f"Split totals {n_tr}+{n_va}+{n_te} != full sample count {n_full}.",
        )

    # Labels per split
    dist_train = _class_distribution_from_y(
        np.asarray(y_train), index_to_class, errors, "y_train"
    )
    dist_val = _class_distribution_from_y(np.asarray(y_val), index_to_class, errors, "y_val")
    dist_test = _class_distribution_from_y(
        np.asarray(y_test), index_to_class, errors, "y_test"
    )

    for split_name, dist in (
        ("train", dist_train),
        ("val", dist_val),
        ("test", dist_test),
    ):
        for cn in class_names:
            if cn not in dist or dist[cn] == 0:
                warnings.append(
                    f"v1 check: class {cn!r} has zero count in {split_name} split.",
                )

    # split_metadata
    if "random_state" not in split_meta:
        errors.append("split_metadata.json missing random_state.")
    if "split_strategy" not in split_meta:
        errors.append("split_metadata.json missing split_strategy.")

    ss = split_meta.get("split_sizes") or {}
    if ss:
        if int(ss.get("train", -1)) != n_tr:
            errors.append(
                f"split_metadata split_sizes.train ({ss.get('train')}) != actual ({n_tr}).",
            )
        if int(ss.get("validation", -1)) != n_va:
            errors.append(
                f"split_metadata split_sizes.validation ({ss.get('validation')}) != actual ({n_va}).",
            )
        if int(ss.get("test", -1)) != n_te:
            errors.append(
                f"split_metadata split_sizes.test ({ss.get('test')}) != actual ({n_te}).",
            )

    if int(split_meta.get("total_samples", -1)) not in (-1, n_full):
        errors.append(
            f"split_metadata total_samples ({split_meta.get('total_samples')}) != {n_full}.",
        )

    nfsm = int(split_meta.get("num_features", -1))
    if nfsm >= 0 and X.ndim == 2 and X.shape[1] != nfsm:
        errors.append(
            f"split_metadata num_features ({nfsm}) != X.shape[1] ({X.shape[1]}).",
        )

    passed = len(errors) == 0
    validation_line = "**PASSED**" if passed else "**FAILED**"

    # --- Markdown report ---
    dataset_source = schema.get("dataset_source", "(unknown)")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    report = f"""# Smart Cricket — Final Dataset Report (Phase 6.6)

Generated: `{ts}`

## Dataset source

- **Engineered features CSV (reference):** `{dataset_source}`
- **Final artifact directory:** `{final_dir}`

## Summary

| Metric | Value |
|--------|-------|
| Total samples | {n_full} |
| Number of features | {nf_schema if nf_schema >= 0 else (X.shape[1] if X.ndim == 2 else "n/a")} |
| Train / Val / Test sizes | {n_tr} / {n_va} / {n_te} |

## Class names (from `label_mapping.json`)

{", ".join(f"`{c}`" for c in class_names)}

## Class distribution — full (`y.npy`)

{_fmt_dist(dist_full if dist_full else {})}

## Class distribution — train / validation / test

### Train

{_fmt_dist(dist_train)}

### Validation

{_fmt_dist(dist_val)}

### Test

{_fmt_dist(dist_test)}

## Feature schema summary

- **Target column:** `{schema.get("target_column", "?")}`
- **num_features:** `{schema.get("num_features", "?")}`
- **Metadata columns (schema):** `{schema.get("metadata_columns", [])}`
- **Feature columns (count):** {len(schema.get("feature_columns", []))}

## Split strategy

- **Strategy:** `{split_meta.get("split_strategy", "n/a")}`
- **random_state:** `{split_meta.get("random_state", "n/a")}`
- **split_metadata `split_sizes`:**

```json
{json.dumps(ss, indent=2)}
```

## Validation status

{validation_line}

"""

    if errors:
        report += "\n### Errors\n\n"
        for e in errors:
            report += f"- {e}\n"
    if warnings:
        report += "\n### Warnings\n\n"
        for w in warnings:
            report += f"- {w}\n"

    report += """
## Notes for future phases

- Scaling and normalization should use statistics fit **only on train** (or fold train), then applied to val/test.
- Phase 7+ model training should load this report location as a provenance anchor (`final_dataset_report.md`).
- If new clips are added, re-run feature build, schema, encoder, matrix, splits, and this validator.
"""

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as f:
        f.write(report)

    print("──────── Final dataset validation (Phase 6.6) ────────")
    print(f"total samples:        {n_full}")
    print(
        f"number of features: {nf_schema if nf_schema >= 0 else (X.shape[1] if X.ndim==2 else 'n/a')}"
    )
    print(f"split sizes:         train={n_tr}  val={n_va}  test={n_te}")
    print(f"validation passed:   {passed}")
    print(f"report path:         {report_path}")
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
    if warnings:
        for w in warnings:
            print(f"  WARN: {w}")

    return 0 if passed else 1


def _write_report_minimal(report_path: Path, errors: list[str]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    body = "# Final Dataset Report\n\n**Validation FAILED** (missing artifacts).\n\n"
    for e in errors:
        body += f"- {e}\n"
    with report_path.open("w", encoding="utf-8") as f:
        f.write(body)


if __name__ == "__main__":
    raise SystemExit(main())
