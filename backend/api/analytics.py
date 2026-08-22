"""Analytics adapters that transform stored analysis sessions for frontend charts."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from .persistence import (
    PersistenceResult,
    list_analysis_feedback_for_user,
    list_analysis_sessions_for_user,
)


SUPPORTED_SHOTS = ("cover_drive", "defensive_shot", "pull_shot", "sweep_shot")
TECHNIQUE_QUALITY_THRESHOLD = 75.0


def _feedback_accuracy(
    feedback_rows: list[dict[str, Any]],
) -> tuple[float | None, int, dict[str, float], dict[str, bool]]:
    """Use explicit user verdicts only; model scores are not accuracy labels."""
    correct = total = 0
    by_shot: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    by_session: dict[str, bool] = {}
    for row in feedback_rows:
        verdict = row.get("prediction_was_correct")
        if verdict not in {"correct", "incorrect"}:
            continue
        is_correct = verdict == "correct"
        correct += int(is_correct)
        total += 1
        session_id = row.get("analysis_session_id")
        if isinstance(session_id, str) and session_id:
            by_session[session_id] = is_correct
        shot = row.get("predicted_shot")
        if shot in SUPPORTED_SHOTS:
            by_shot[str(shot)][0] += int(is_correct)
            by_shot[str(shot)][1] += 1
    class_accuracy = {
        shot: round(100 * counts[0] / counts[1], 1)
        for shot, counts in by_shot.items()
        if counts[1]
    }
    return (round(100 * correct / total, 1) if total else None, total, class_accuracy, by_session)


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return number


def _day_key(created_at: str | None) -> str | None:
    if not created_at:
        return None
    try:
        return datetime.fromisoformat(str(created_at).replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        raw = str(created_at)
        return raw[:10] if len(raw) >= 10 else None


def _feedback_text(row: dict[str, Any]) -> str | None:
    tips = row.get("coaching_tips")
    if isinstance(tips, list) and tips:
        return " ".join(str(tip) for tip in tips if tip)
    spoken = row.get("spoken_feedback")
    if isinstance(spoken, str) and spoken.strip():
        return spoken.strip()
    full = row.get("full_result")
    if isinstance(full, dict):
        detailed = full.get("detailed_feedback")
        if isinstance(detailed, str) and detailed.strip():
            return detailed.strip()
    return None


def _audio_metadata(row: dict[str, Any]) -> dict[str, Any] | None:
    full = row.get("full_result")
    if not isinstance(full, dict):
        return None
    voice = full.get("voice_output")
    return voice if isinstance(voice, dict) else None


def _landmarks(row: dict[str, Any]) -> list[dict[str, float]]:
    full = row.get("full_result")
    if not isinstance(full, dict):
        return []
    landmarks = full.get("landmarks")
    if not isinstance(landmarks, list):
        return []
    cleaned: list[dict[str, float]] = []
    for item in landmarks:
        if not isinstance(item, dict):
            continue
        try:
            cleaned.append(
                {
                    "x": float(item["x"]),
                    "y": float(item["y"]),
                    "visibility": float(item.get("visibility") or 0.0),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return cleaned


def aggregate_analytics(rows: list[dict[str, Any]], feedback_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build frontend-compatible analytics from trusted analysis_session rows."""
    distribution = {shot: 0 for shot in SUPPORTED_SHOTS}
    technique_sums: dict[str, float] = defaultdict(float)
    technique_counts: dict[str, int] = defaultdict(int)
    by_day: dict[str, int] = defaultdict(int)
    overall_accuracy, feedback_count, class_accuracy, feedback_by_session = _feedback_accuracy(feedback_rows)
    history: list[dict[str, Any]] = []

    for row in rows:
        shot = row.get("predicted_shot")
        if shot in distribution:
            distribution[shot] += 1
            score = _safe_float(row.get("technique_match_score"))
            if score is not None:
                technique_sums[str(shot)] += score
                technique_counts[str(shot)] += 1
        day = _day_key(row.get("created_at") if isinstance(row.get("created_at"), str) else None)
        if day:
            by_day[day] += 1
        session_id = row.get("id")
        history.append(
            {
                "id": session_id,
                "created_at": row.get("created_at"),
                "predicted_shot": shot,
                "confidence": _safe_float(row.get("shot_confidence")),
                "technique_match_score": _safe_float(row.get("technique_match_score")),
                "duration_seconds": _safe_float(row.get("shot_duration_seconds")),
                "accuracy": feedback_by_session.get(session_id) if isinstance(session_id, str) else None,
                "feedback": _feedback_text(row),
            }
        )

    total_shots = sum(distribution.values())
    session_count = len(by_day)
    shots_per_session = round(total_shots / session_count, 2) if session_count else None
    shots_over_time = [
        {"date": day, "count": by_day[day]}
        for day in sorted(by_day.keys())
    ]

    technique_quality: dict[str, float] = {}
    for shot in SUPPORTED_SHOTS:
        count = technique_counts.get(shot, 0)
        if count:
            technique_quality[shot] = round(technique_sums[shot] / count, 1)

    current_model_output = None
    if rows:
        latest = rows[0]
        confidence = _safe_float(latest.get("shot_confidence"))
        technique = _safe_float(latest.get("technique_match_score"))
        current_model_output = {
            "predicted_shot": latest.get("predicted_shot"),
            "confidence": confidence,
            "technique_match_score": technique,
            "timestamp": latest.get("created_at"),
            "feedback": _feedback_text(latest),
            "audio": _audio_metadata(latest),
            "landmarks": _landmarks(latest),
            "analysis_session_id": latest.get("id"),
        }

    return {
        "summary": {
            "total_sessions": session_count,
            "total_shots": total_shots,
            "overall_accuracy": overall_accuracy,
            "accuracy_feedback_count": feedback_count,
            "technique_quality": technique_quality,
        },
        "class_accuracy": {"values": class_accuracy, "source": "explicit_user_feedback"},
        "session_history": {"sessions": history, "shots_over_time": shots_over_time},
        "shot_distribution": distribution,
        "shot_frequency": {
            "total_shots": total_shots,
            "shots_per_session": shots_per_session,
            "session_count": session_count,
            "shots_over_time": shots_over_time,
        },
        "technique_quality": technique_quality,
        "current_model_output": current_model_output,
    }


def build_user_analytics(*, user_id: str, limit: int = 200) -> tuple[PersistenceResult, dict[str, Any] | None]:
    """Load a user's analysis history and return aggregated analytics."""
    lookup = list_analysis_sessions_for_user(user_id=user_id, limit=limit)
    if not lookup.stored:
        return lookup, None
    feedback = list_analysis_feedback_for_user(user_id=user_id, limit=max(limit * 2, 200))
    if not feedback.stored:
        return feedback, None
    rows = lookup.record if isinstance(lookup.record, list) else []
    feedback_rows = feedback.record if isinstance(feedback.record, list) else []
    return lookup, aggregate_analytics(rows, feedback_rows)


def technique_quality_from_live_results(results: list[dict[str, Any]]) -> dict[str, float]:
    """Average technique_match_score by predicted shot for an in-progress live session."""
    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for result in results:
        shot = result.get("predicted_shot")
        score = _safe_float(result.get("technique_match_score"))
        if shot not in SUPPORTED_SHOTS or score is None:
            continue
        sums[str(shot)] += score
        counts[str(shot)] += 1
    return {shot: round(sums[shot] / counts[shot], 1) for shot in SUPPORTED_SHOTS if counts.get(shot)}
