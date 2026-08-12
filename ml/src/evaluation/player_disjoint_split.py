"""Create deterministic train/validation/test manifests with no player overlap."""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SPLITS = ("train", "validation", "test")
GROUP_FIELDS = ("player_id", "person_id", "participant_id", "group_id")
LABEL_FIELDS = ("shot_label", "label", "class_name", "true_label")


def load_manifest(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"manifest not found: {p}")
    if p.suffix.lower() == ".csv":
        with p.open(newline="", encoding="utf-8") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if p.suffix.lower() == ".jsonl":
        rows = []
        with p.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"{p}:{line_no} must contain a JSON object.")
                rows.append(row)
        return rows
    if p.suffix.lower() == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("samples"), list):
            data = data["samples"]
        if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
            raise ValueError("JSON manifest must be a list of objects or an object with samples.")
        return list(data)
    raise ValueError(f"unsupported manifest extension: {p.suffix}")


def write_manifest(path: str | Path, rows: list[dict[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix.lower() == ".csv":
        fieldnames: list[str] = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
        with p.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return
    if p.suffix.lower() == ".jsonl":
        with p.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
        return
    if p.suffix.lower() == ".json":
        p.write_text(json.dumps({"samples": rows}, indent=2, sort_keys=True), encoding="utf-8")
        return
    raise ValueError(f"unsupported output extension: {p.suffix}")


def infer_field(rows: list[dict[str, Any]], candidates: tuple[str, ...], name: str) -> str:
    for field in candidates:
        if any(str(row.get(field, "")).strip() for row in rows):
            return field
    raise ValueError(f"manifest is missing {name} metadata. Add one of: {', '.join(candidates)}.")


def validate_ratios(train_ratio: float, validation_ratio: float, test_ratio: float) -> None:
    if min(train_ratio, validation_ratio, test_ratio) < 0:
        raise ValueError("split ratios must be non-negative.")
    if abs((train_ratio + validation_ratio + test_ratio) - 1.0) > 1e-6:
        raise ValueError("split ratios must sum to 1.0.")


def _group_rows(rows: list[dict[str, Any]], group_field: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    missing: list[int] = []
    for row_index, row in enumerate(rows, start=1):
        group = str(row.get(group_field, "")).strip()
        if not group:
            missing.append(row_index)
        else:
            grouped[group].append(row)
    if missing:
        preview = ", ".join(str(i) for i in missing[:10])
        raise ValueError(f"{group_field} is empty for row(s): {preview}. Player/group IDs are required.")
    return dict(grouped)


def create_player_disjoint_split(
    rows: list[dict[str, Any]],
    *,
    group_field: str,
    label_field: str,
    seed: int = 42,
    train_ratio: float = 0.7,
    validation_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not rows:
        raise ValueError("manifest has no rows.")
    validate_ratios(train_ratio, validation_ratio, test_ratio)
    grouped = _group_rows(rows, group_field)

    group_names = list(grouped)
    random.Random(seed).shuffle(group_names)
    group_names.sort(key=lambda group: len(grouped[group]), reverse=True)
    targets = {
        "train": len(rows) * train_ratio,
        "validation": len(rows) * validation_ratio,
        "test": len(rows) * test_ratio,
    }
    counts = {split: 0 for split in SPLITS}
    assignments: dict[str, str] = {}
    for group in group_names:
        split = max(SPLITS, key=lambda name: targets[name] - counts[name])
        assignments[group] = split
        counts[split] += len(grouped[group])

    out_rows = []
    for row in rows:
        out = dict(row)
        out["split"] = assignments[str(row[group_field]).strip()]
        out_rows.append(out)
    return out_rows, summarize_split(out_rows, group_field=group_field, label_field=label_field, seed=seed, ratios=targets)


def summarize_split(
    rows: list[dict[str, Any]],
    *,
    group_field: str,
    label_field: str,
    seed: int,
    ratios: dict[str, float],
) -> dict[str, Any]:
    groups = {split: set() for split in SPLITS}
    labels = {split: Counter() for split in SPLITS}
    sample_counts = {split: 0 for split in SPLITS}
    for row in rows:
        split = str(row.get("split", "")).strip()
        if split not in SPLITS:
            raise ValueError(f"invalid split value: {split!r}")
        groups[split].add(str(row.get(group_field, "")).strip())
        label = str(row.get(label_field, "")).strip()
        if label:
            labels[split][label] += 1
        sample_counts[split] += 1
    overlap = {}
    for index, left in enumerate(SPLITS):
        for right in SPLITS[index + 1 :]:
            overlap[f"{left}_vs_{right}"] = sorted(groups[left] & groups[right])
    return {
        "strategy": "player_disjoint_group_split",
        "seed": seed,
        "target_sample_counts": ratios,
        "group_field": group_field,
        "label_field": label_field,
        "total_samples": len(rows),
        "total_groups": len(set().union(*groups.values())),
        "split_sample_counts": sample_counts,
        "split_group_counts": {split: len(value) for split, value in groups.items()},
        "split_label_counts": {split: dict(sorted(value.items())) for split, value in labels.items()},
        "group_overlap": overlap,
        "player_disjoint": all(not value for value in overlap.values()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--group-field")
    parser.add_argument("--label-field")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--validation-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    args = parser.parse_args(argv)
    try:
        rows = load_manifest(args.input)
        group_field = args.group_field or infer_field(rows, GROUP_FIELDS, "player/group")
        label_field = args.label_field or infer_field(rows, LABEL_FIELDS, "label")
        out_rows, summary = create_player_disjoint_split(
            rows,
            group_field=group_field,
            label_field=label_field,
            seed=args.seed,
            train_ratio=args.train_ratio,
            validation_ratio=args.validation_ratio,
            test_ratio=args.test_ratio,
        )
        write_manifest(args.output, out_rows)
        Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary).write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote player-disjoint manifest: {args.output}")
    print(f"Wrote split summary: {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
