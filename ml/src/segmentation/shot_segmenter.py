"""Shot segmentation and single-prediction trigger generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Sequence

import numpy as np

from .motion_energy import MotionEnergyConfig, MotionEnergySignal, compute_motion_energy_signal
from .state_machine import ShotStateMachine, ShotStateMachineConfig


@dataclass(frozen=True)
class ShotSegment:
    """One detected batting-motion segment."""

    start_frame: int
    end_frame: int
    peak_frame: int
    prediction_trigger_frame: int
    completed: bool
    completion_reason: str
    trigger_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SegmentationResult:
    """Full segmentation result for one sequence."""

    segment: ShotSegment | None
    motion_signal: MotionEnergySignal
    state_trace: list[dict[str, Any]]

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "segment": self.segment.to_dict() if self.segment is not None else None,
            "num_trace_rows": len(self.state_trace),
            "max_energy": float(self.motion_signal.smoothed_energy.max()),
            "mean_energy": float(self.motion_signal.smoothed_energy.mean()),
            "thresholds": {
                "start_threshold": self.motion_signal.start_threshold,
                "active_threshold": self.motion_signal.active_threshold,
                "end_threshold": self.motion_signal.end_threshold,
            },
        }


class ShotSegmenter:
    """Segment one temporal feature sequence and emit one prediction trigger."""

    def __init__(
        self,
        *,
        energy_config: MotionEnergyConfig = MotionEnergyConfig(),
        state_config: ShotStateMachineConfig = ShotStateMachineConfig(),
        force_complete_at_sequence_end: bool = True,
    ) -> None:
        self.energy_config = energy_config
        self.state_config = state_config
        self.force_complete_at_sequence_end = force_complete_at_sequence_end

    def segment_sequence(
        self,
        sequence: np.ndarray,
        feature_columns: Sequence[str],
    ) -> SegmentationResult:
        """Return the detected segment and full state trace for one [T,F] sequence."""
        signal = compute_motion_energy_signal(sequence, feature_columns, self.energy_config)
        machine = ShotStateMachine(
            start_threshold=signal.start_threshold,
            active_threshold=signal.active_threshold,
            end_threshold=signal.end_threshold,
            config=self.state_config,
        )
        for frame_index, energy in enumerate(signal.smoothed_energy):
            machine.update(frame_index, float(energy))

        completion_reason = "state_machine_completed"
        if self.force_complete_at_sequence_end and not machine.triggered:
            forced = machine.force_complete_at_sequence_end(len(signal.smoothed_energy) - 1)
            if forced is not None:
                completion_reason = "sequence_end_completion"

        trigger_rows = [row for row in machine.trace if row.prediction_triggered]
        segment: ShotSegment | None = None
        if machine.motion_start_frame is not None and trigger_rows:
            trigger_frame = trigger_rows[-1].frame_index
            segment = ShotSegment(
                start_frame=int(machine.motion_start_frame),
                end_frame=int(machine.motion_end_frame if machine.motion_end_frame is not None else trigger_frame),
                peak_frame=int(machine.peak_frame if machine.peak_frame is not None else trigger_frame),
                prediction_trigger_frame=int(trigger_frame),
                completed=True,
                completion_reason=completion_reason,
                trigger_count=len(trigger_rows),
            )

        return SegmentationResult(
            segment=segment,
            motion_signal=signal,
            state_trace=[asdict(row) for row in machine.trace],
        )
