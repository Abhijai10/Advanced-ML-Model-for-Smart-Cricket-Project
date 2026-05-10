"""Phase 5.2 verification script for feature ordering and integrity."""

from feature_config import (
    ALL_FEATURES,
    FEATURE_GROUP_MAP,
    FEATURE_INDEX_MAP,
    NUM_TOTAL_FEATURES,
)


def main() -> None:
    print("Feature list (index | group | name):")
    for idx, feature_name in enumerate(ALL_FEATURES):
        group_name = FEATURE_GROUP_MAP[feature_name]
        print(f"{idx:2d} | {group_name:12s} | {feature_name}")

    if NUM_TOTAL_FEATURES != 32:
        raise ValueError(
            f"Verification failed: expected 32 total features, got {NUM_TOTAL_FEATURES}."
        )

    if ALL_FEATURES[0] != "lead_elbow_angle_mean":
        raise ValueError(
            "Verification failed: first feature must be 'lead_elbow_angle_mean'."
        )

    if ALL_FEATURES[-1] != "weight_transfer_score":
        raise ValueError(
            "Verification failed: last feature must be 'weight_transfer_score'."
        )

    unique_indices = set(FEATURE_INDEX_MAP.values())
    if len(unique_indices) != NUM_TOTAL_FEATURES:
        raise ValueError("Verification failed: feature indices are not unique.")

    print("\nSuccess: Phase 5.2 feature configuration ordering is correct.")


if __name__ == "__main__":
    main()
