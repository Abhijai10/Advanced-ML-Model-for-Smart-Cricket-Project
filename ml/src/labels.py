"""
Central label definitions for cricket batting analysis.

Import this module anywhere labels are needed to keep naming consistent.
"""

SHOT_LABELS = [
    "cover_drive",
    "straight_drive",
    "pull_shot",
    "defensive_shot",
]

QUALITY_LABELS = [
    "good",
    "average",
    "bad",
]

# Placeholder list for future fine-grained coaching errors.
# These are not mandatory in the current phase.
FUTURE_MISTAKE_LABELS = [
    "poor_head_alignment",
    "low_forward_lean",
    "elbow_collapse",
    "unstable_balance",
    "weak_follow_through",
]
