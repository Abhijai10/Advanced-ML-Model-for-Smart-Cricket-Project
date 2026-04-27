"""
Simple schema definitions for shot and quality labels.
"""

from typing import Literal, Optional

from pydantic import BaseModel

from .labels import FUTURE_MISTAKE_LABELS, QUALITY_LABELS, SHOT_LABELS


# Explicit literals for strict validation in APIs/training metadata.
ShotLabel = Literal["cover_drive", "straight_drive", "pull_shot", "defensive_shot"]
QualityLabel = Literal["good", "average", "bad"]


class BattingLabelSchema(BaseModel):
    shot_label: ShotLabel
    quality_label: QualityLabel
    # Optional placeholder for future detailed coaching error tags.
    mistake_label: Optional[str] = None


SUPPORTED_LABELS = {
    "shot_label": SHOT_LABELS,
    "quality_label": QUALITY_LABELS,
    "future_mistake_labels": FUTURE_MISTAKE_LABELS,
}
