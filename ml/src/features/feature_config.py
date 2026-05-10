"""Centralized feature blueprint for Smart Cricket Phase 5.2.

This module defines:
- Finalized feature groups
- Group/feature count constants
- Feature index and group lookup maps
- MediaPipe pose landmark index constants
- Validation helpers for configuration integrity
"""

JOINT_ANGLE_FEATURES = [
    "lead_elbow_angle_mean",
    "lead_elbow_angle_min",
    "trail_elbow_angle_mean",
    "lead_knee_angle_mean",
    "lead_knee_angle_min",
    "trail_knee_angle_mean",
    "shoulder_rotation_angle_mean",
    "hip_rotation_angle_mean",
]

POSTURE_FEATURES = [
    "trunk_lean_mean",
    "trunk_lean_max",
    "head_stability",
    "head_over_base_offset",
    "shoulder_hip_separation_mean",
    "stance_width_mean",
    "body_center_shift_x",
    "body_center_shift_y",
]

MOTION_FEATURES = [
    "lead_wrist_velocity_mean",
    "lead_wrist_velocity_max",
    "trail_wrist_velocity_mean",
    "trail_wrist_velocity_max",
    "body_center_velocity_mean",
    "body_center_velocity_max",
    "shoulder_rotation_velocity_mean",
    "motion_energy_total",
]

SHOT_SPECIFIC_FEATURES = [
    "front_foot_commitment",
    "back_foot_loading",
    "follow_through_height",
    "follow_through_extension",
    "lead_elbow_extension_change",
    "lead_knee_flexion_change",
    "head_to_lead_knee_alignment",
    "weight_transfer_score",
]

ALL_FEATURES = (
    JOINT_ANGLE_FEATURES
    + POSTURE_FEATURES
    + MOTION_FEATURES
    + SHOT_SPECIFIC_FEATURES
)

NUM_JOINT_ANGLE_FEATURES = len(JOINT_ANGLE_FEATURES)
NUM_POSTURE_FEATURES = len(POSTURE_FEATURES)
NUM_MOTION_FEATURES = len(MOTION_FEATURES)
NUM_SHOT_SPECIFIC_FEATURES = len(SHOT_SPECIFIC_FEATURES)
NUM_TOTAL_FEATURES = len(ALL_FEATURES)

FEATURE_INDEX_MAP = {feature_name: idx for idx, feature_name in enumerate(ALL_FEATURES)}

FEATURE_GROUP_MAP = {}
for feature_name in JOINT_ANGLE_FEATURES:
    FEATURE_GROUP_MAP[feature_name] = "joint_angle"
for feature_name in POSTURE_FEATURES:
    FEATURE_GROUP_MAP[feature_name] = "posture"
for feature_name in MOTION_FEATURES:
    FEATURE_GROUP_MAP[feature_name] = "motion"
for feature_name in SHOT_SPECIFIC_FEATURES:
    FEATURE_GROUP_MAP[feature_name] = "shot_specific"

# MediaPipe pose landmark indices used by Smart Cricket features.
NOSE = 0
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_ELBOW = 13
RIGHT_ELBOW = 14
LEFT_WRIST = 15
RIGHT_WRIST = 16
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28

LANDMARK_INDEX_MAP = {
    "nose": NOSE,
    "left_shoulder": LEFT_SHOULDER,
    "right_shoulder": RIGHT_SHOULDER,
    "left_elbow": LEFT_ELBOW,
    "right_elbow": RIGHT_ELBOW,
    "left_wrist": LEFT_WRIST,
    "right_wrist": RIGHT_WRIST,
    "left_hip": LEFT_HIP,
    "right_hip": RIGHT_HIP,
    "left_knee": LEFT_KNEE,
    "right_knee": RIGHT_KNEE,
    "left_ankle": LEFT_ANKLE,
    "right_ankle": RIGHT_ANKLE,
}


def get_feature_index(feature_name: str) -> int:
    """Return feature index in ALL_FEATURES."""
    if feature_name not in FEATURE_INDEX_MAP:
        raise KeyError(f"Unknown feature name: {feature_name}")
    return FEATURE_INDEX_MAP[feature_name]


def get_feature_group(feature_name: str) -> str:
    """Return feature group name for a feature."""
    if feature_name not in FEATURE_GROUP_MAP:
        raise KeyError(f"Unknown feature name: {feature_name}")
    return FEATURE_GROUP_MAP[feature_name]


def validate_feature_config() -> bool:
    """Validate feature config integrity for Phase 5.2 blueprint."""
    expected_total = 32
    if NUM_TOTAL_FEATURES != expected_total:
        return False

    if len(set(ALL_FEATURES)) != NUM_TOTAL_FEATURES:
        return False

    if len(FEATURE_INDEX_MAP) != NUM_TOTAL_FEATURES:
        return False
    for feature_name in ALL_FEATURES:
        if feature_name not in FEATURE_INDEX_MAP:
            return False

    if len(FEATURE_GROUP_MAP) != NUM_TOTAL_FEATURES:
        return False
    for feature_name in ALL_FEATURES:
        if feature_name not in FEATURE_GROUP_MAP:
            return False

    group_counts = {
        "joint_angle": 0,
        "posture": 0,
        "motion": 0,
        "shot_specific": 0,
    }
    for feature_name in ALL_FEATURES:
        group_name = FEATURE_GROUP_MAP[feature_name]
        if group_name not in group_counts:
            return False
        group_counts[group_name] += 1

    if group_counts["joint_angle"] != 8:
        return False
    if group_counts["posture"] != 8:
        return False
    if group_counts["motion"] != 8:
        return False
    if group_counts["shot_specific"] != 8:
        return False

    return True


if __name__ == "__main__":
    print(f"Total feature count: {NUM_TOTAL_FEATURES}")
    print(
        "Group counts: "
        f"joint_angle={NUM_JOINT_ANGLE_FEATURES}, "
        f"posture={NUM_POSTURE_FEATURES}, "
        f"motion={NUM_MOTION_FEATURES}, "
        f"shot_specific={NUM_SHOT_SPECIFIC_FEATURES}"
    )

    if validate_feature_config():
        print("Validation successful: feature configuration is valid.")
    else:
        print("Validation failed: feature configuration is invalid.")
