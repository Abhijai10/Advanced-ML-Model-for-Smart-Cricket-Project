from __future__ import annotations

import json

import pytest

from ml.src.evaluation.player_disjoint_split import (
    create_player_disjoint_split,
    infer_field,
    load_manifest,
    write_manifest,
)


def _rows() -> list[dict[str, str]]:
    rows = []
    for player in range(1, 7):
        for shot in ("cover_drive", "pull_shot"):
            rows.append({"sample_id": f"p{player}-{shot}", "player_id": f"player-{player}", "shot_label": shot})
    return rows


def test_player_disjoint_split_has_no_overlap() -> None:
    rows, summary = create_player_disjoint_split(
        _rows(),
        group_field="player_id",
        label_field="shot_label",
        seed=7,
        train_ratio=0.5,
        validation_ratio=0.25,
        test_ratio=0.25,
    )

    groups = {split: {row["player_id"] for row in rows if row["split"] == split} for split in ("train", "validation", "test")}

    assert groups["train"].isdisjoint(groups["validation"])
    assert groups["train"].isdisjoint(groups["test"])
    assert groups["validation"].isdisjoint(groups["test"])
    assert summary["player_disjoint"] is True
    assert sum(summary["split_sample_counts"].values()) == 12


def test_missing_player_id_fails_clearly() -> None:
    rows = _rows()
    rows[0]["player_id"] = ""

    with pytest.raises(ValueError, match="Player/group IDs are required"):
        create_player_disjoint_split(rows, group_field="player_id", label_field="shot_label")


def test_manifest_csv_round_trip(tmp_path) -> None:
    input_path = tmp_path / "manifest.csv"
    output_path = tmp_path / "manifest_with_split.csv"

    write_manifest(input_path, _rows())
    rows = load_manifest(input_path)
    group_field = infer_field(rows, ("player_id",), "player/group")
    out_rows, summary = create_player_disjoint_split(rows, group_field=group_field, label_field="shot_label")
    write_manifest(output_path, out_rows)

    reloaded = load_manifest(output_path)
    assert {row["split"] for row in reloaded} <= {"train", "validation", "test"}
    assert json.dumps(summary)
