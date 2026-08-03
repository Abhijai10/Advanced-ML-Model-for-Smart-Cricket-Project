"""Configuration for Phase 10 technique scoring.

The v1 scoring system is intentionally rule-based: it compares measurable
temporal features with shot-specific template ranges instead of treating model
confidence as technique quality.
"""

from __future__ import annotations

from dataclasses import dataclass


EXPECTED_SEQUENCE_LENGTH = 60
EXPECTED_FEATURE_DIM = 32
EXPECTED_NUM_CLASSES = 4
PHASE10_VERSION = "phase_10_technique_scoring_v1"


@dataclass(frozen=True)
class FeatureScoreSpec:
    """One feature/statistic pair used by a component score."""

    feature_name: str
    statistic: str


@dataclass(frozen=True)
class ComponentScoreConfig:
    """Human-interpretable scoring component configuration."""

    name: str
    weight: float
    feature_specs: tuple[FeatureScoreSpec, ...]
    description: str


COMPONENT_CONFIGS: tuple[ComponentScoreConfig, ...] = (
    ComponentScoreConfig(
        name="head_stability_score",
        weight=0.14,
        feature_specs=(
            FeatureScoreSpec("head_over_base_offset", "abs_mean"),
            FeatureScoreSpec("head_to_lead_knee_alignment", "abs_mean"),
            FeatureScoreSpec("upper_body_balance_offset", "abs_mean"),
        ),
        description="Keeps head and upper body close to the stable base line.",
    ),
    ComponentScoreConfig(
        name="front_foot_commitment_score",
        weight=0.12,
        feature_specs=(
            FeatureScoreSpec("front_foot_commitment_signal", "final_mean"),
            FeatureScoreSpec("stance_to_swing_progress_signal", "final_mean"),
        ),
        description="Measures whether the shot develops into a committed front-foot action.",
    ),
    ComponentScoreConfig(
        name="lead_elbow_score",
        weight=0.13,
        feature_specs=(
            FeatureScoreSpec("lead_elbow_angle", "mean"),
            FeatureScoreSpec("lead_elbow_extension_signal", "final_mean"),
        ),
        description="Tracks lead-elbow shape and extension through the shot.",
    ),
    ComponentScoreConfig(
        name="knee_bend_score",
        weight=0.12,
        feature_specs=(
            FeatureScoreSpec("lead_knee_angle", "mean"),
            FeatureScoreSpec("trail_knee_angle", "mean"),
        ),
        description="Compares lower-body posture with the expected shot template.",
    ),
    ComponentScoreConfig(
        name="weight_transfer_score",
        weight=0.13,
        feature_specs=(
            FeatureScoreSpec("weight_transfer_signal", "final_mean"),
            FeatureScoreSpec("body_center_offset_x", "range"),
        ),
        description="Captures shift of body mass through the batting movement.",
    ),
    ComponentScoreConfig(
        name="follow_through_score",
        weight=0.14,
        feature_specs=(
            FeatureScoreSpec("follow_through_height_signal", "final_mean"),
            FeatureScoreSpec("follow_through_extension_signal", "final_mean"),
            FeatureScoreSpec("bat_side_wrist_height_signal", "final_mean"),
        ),
        description="Measures whether the motion finishes with the expected extension and height.",
    ),
    ComponentScoreConfig(
        name="rotation_score",
        weight=0.12,
        feature_specs=(
            FeatureScoreSpec("hip_rotation_angle", "range"),
            FeatureScoreSpec("hip_rotation_velocity", "max_abs"),
            FeatureScoreSpec("shoulder_hip_separation", "mean"),
        ),
        description="Scores rotational mechanics without depending on dead shoulder-angle features.",
    ),
    ComponentScoreConfig(
        name="balance_score",
        weight=0.10,
        feature_specs=(
            FeatureScoreSpec("stance_width", "mean"),
            FeatureScoreSpec("body_center_offset_y", "abs_mean"),
            FeatureScoreSpec("upper_body_balance_offset", "abs_mean"),
        ),
        description="Checks stable base width and centered posture during the sequence.",
    ),
)


TEMPLATE_QUANTILE_LOW = 10.0
TEMPLATE_QUANTILE_HIGH = 90.0
MIN_TEMPLATE_SAMPLES = 3
MIN_TEMPLATE_SPAN = 1e-6
OUTSIDE_RANGE_TOLERANCE_MULTIPLIER = 2.0


def component_weight_sum() -> float:
    """Return total configured component weight."""
    return sum(component.weight for component in COMPONENT_CONFIGS)
