"""Rule helpers that turn Phase 10 deviations into coaching issues."""

from __future__ import annotations

from typing import Any

from .feedback_schema import DetectedIssue
from .feedback_templates import COMPONENT_LABELS, FEATURE_FEEDBACK, GENERIC_COMPONENT_TIPS


ISSUE_SCORE_THRESHOLD = 75.0
MAX_ISSUES_PER_SAMPLE = 3


def severity_from_score(score: float) -> str:
    """Convert a feature/component score into a simple severity label."""
    if score < 40.0:
        return "high"
    if score < 65.0:
        return "medium"
    return "low"


def direction_text(actual: float, low: float, high: float) -> str:
    """Describe whether a value is below, above, or inside a template range."""
    if actual < low:
        return "below"
    if actual > high:
        return "above"
    return "inside"


def issue_from_deviation(
    *,
    component_name: str,
    deviation: dict[str, Any],
) -> DetectedIssue:
    """Create one feedback issue from a Phase 10 feature deviation."""
    feature_name = str(deviation["feature_name"])
    statistic = str(deviation["statistic"])
    feature_copy = FEATURE_FEEDBACK.get(feature_name)
    component_label = COMPONENT_LABELS.get(component_name, component_name.replace("_score", "").replace("_", " "))
    score = float(deviation["score"])
    actual = float(deviation["actual_value"])
    low = float(deviation["expected_low"])
    high = float(deviation["expected_high"])
    direction = direction_text(actual, low, high)
    evidence = {
        "feature_score": score,
        "actual_value": actual,
        "expected_low": low,
        "expected_high": high,
        "deviation": float(deviation["deviation"]),
    }
    if feature_copy is None:
        return DetectedIssue(
            component_name=component_name,
            feature_name=feature_name,
            statistic=statistic,
            severity=severity_from_score(score),
            issue=f"Your {component_label} measurement was {direction} the v1 template range.",
            why_it_matters=f"{component_label.title()} contributes to repeatable shot control.",
            coaching_tip=GENERIC_COMPONENT_TIPS.get(component_name, f"Improve your {component_label} with controlled repetition."),
            evidence=evidence,
        )
    return DetectedIssue(
        component_name=component_name,
        feature_name=feature_name,
        statistic=statistic,
        severity=severity_from_score(score),
        issue=feature_copy["issue"],
        why_it_matters=feature_copy["why"],
        coaching_tip=feature_copy["tip"],
        evidence=evidence,
    )


def select_detected_issues(component_scores: dict[str, Any]) -> tuple[DetectedIssue, ...]:
    """Select the most important measurable issues from component score details."""
    candidates: list[tuple[float, DetectedIssue]] = []
    for component_name, component in component_scores.items():
        for deviation in component.get("deviations", []):
            score = float(deviation["score"])
            if score >= ISSUE_SCORE_THRESHOLD:
                continue
            candidates.append(
                (
                    score,
                    issue_from_deviation(component_name=component_name, deviation=deviation),
                )
            )

    candidates.sort(key=lambda item: (item[0], -item[1].evidence["deviation"]))
    selected: list[DetectedIssue] = []
    seen_features: set[str] = set()
    for _score, issue in candidates:
        if issue.feature_name in seen_features:
            continue
        seen_features.add(issue.feature_name)
        selected.append(issue)
        if len(selected) >= MAX_ISSUES_PER_SAMPLE:
            break
    return tuple(selected)


def fallback_tip_from_weakest_component(component_scores: dict[str, Any], technique_score: float) -> str:
    """Return a generic tip when no feature-level issue crosses the threshold."""
    if technique_score >= 85.0:
        return "Maintain this movement pattern and keep the shot repeatable under match tempo."
    weakest = min(component_scores.items(), key=lambda item: float(item[1]["score"]))[0]
    return GENERIC_COMPONENT_TIPS.get(weakest, "Keep the movement controlled and repeatable.")
