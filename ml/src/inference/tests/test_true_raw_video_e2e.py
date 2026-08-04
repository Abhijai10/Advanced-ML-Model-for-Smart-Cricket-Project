"""True raw-video E2E harness for Phase 12.

This test intentionally does not mock MediaPipe, preprocessing, checkpoint
inference, segmentation, scoring, or feedback. It is skipped until a legally
usable cricket batting clip is added at the documented fixture path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from inference.raw_video_pipeline import analyze_raw_video


FIXTURE = Path("ml/data/e2e/raw_batting_fixture.mp4")


@pytest.mark.real_e2e
def test_actual_batting_video_through_unmocked_phase12_pipeline() -> None:
    if not FIXTURE.is_file():
        pytest.skip(
            "Missing legally usable raw batting fixture at "
            "ml/data/e2e/raw_batting_fixture.mp4. Add a consented clip before "
            "claiming Phase 12 true E2E validation."
        )

    result = analyze_raw_video(FIXTURE)

    assert result["debug_metadata"]["pipeline_mode"] == "raw_video_upload"
    assert result["source_metadata"]["frames_after_resampling"] == 60
    assert result["predicted_shot"] in {"cover_drive", "defensive_shot", "pull_shot", "sweep_shot"}
    assert 0.0 <= result["shot_confidence"] <= 1.0
    assert 0.0 <= result["technique_match_score"] <= 100.0
    assert result["segmentation"]["trigger_count"] >= 0
    assert result["coaching_tips"]
