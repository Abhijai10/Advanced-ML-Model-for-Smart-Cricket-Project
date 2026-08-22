"""Unit tests for truthful frontend analytics adapters."""

from backend.api.analytics import aggregate_analytics


def test_analytics_uses_only_explicit_feedback_for_accuracy() -> None:
    payload = aggregate_analytics(
        [
            {
                "id": "session-a",
                "predicted_shot": "cover_drive",
                "shot_confidence": 0.98,
                "technique_match_score": 86,
                "created_at": "2026-08-23T09:00:00Z",
            },
            {
                "id": "session-b",
                "predicted_shot": "pull_shot",
                "shot_confidence": 0.88,
                "technique_match_score": 61,
                "created_at": "2026-08-23T10:00:00Z",
            },
        ],
        [
            {"analysis_session_id": "session-a", "predicted_shot": "cover_drive", "prediction_was_correct": "correct"},
            {"analysis_session_id": "session-b", "predicted_shot": "pull_shot", "prediction_was_correct": "unsure"},
        ],
    )

    assert payload["summary"]["overall_accuracy"] == 100.0
    assert payload["summary"]["accuracy_feedback_count"] == 1
    assert payload["class_accuracy"] == {"values": {"cover_drive": 100.0}, "source": "explicit_user_feedback"}
    assert payload["shot_distribution"] == {
        "cover_drive": 1,
        "defensive_shot": 0,
        "pull_shot": 1,
        "sweep_shot": 0,
    }
    assert payload["session_history"]["sessions"][1]["accuracy"] is None
