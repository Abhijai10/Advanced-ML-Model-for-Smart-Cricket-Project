"""Explainable state machine for one-shot prediction gating."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ShotState(str, Enum):
    """Human-readable states from the locked Phase 9 roadmap."""

    IDLE = "idle"
    PREPARATION = "preparation"
    BACKSWING = "backswing"
    SWING = "swing"
    FOLLOW_THROUGH = "follow_through"
    COMPLETED = "completed"
    COOLDOWN = "cooldown"


@dataclass(frozen=True)
class ShotStateMachineConfig:
    """Small, conservative state-machine controls."""

    min_preparation_frames: int = 2
    min_swing_frames: int = 4
    stabilization_frames: int = 4
    cooldown_frames: int = 8


@dataclass(frozen=True)
class StateTraceRow:
    """One inspectable state-machine row for a frame."""

    frame_index: int
    energy: float
    state: str
    transition: str
    prediction_triggered: bool


class ShotStateMachine:
    """Track shot-progress states and emit at most one prediction trigger."""

    def __init__(
        self,
        *,
        start_threshold: float,
        active_threshold: float,
        end_threshold: float,
        config: ShotStateMachineConfig = ShotStateMachineConfig(),
    ) -> None:
        if not (0.0 <= end_threshold <= active_threshold <= start_threshold <= 1.0):
            raise ValueError("Expected thresholds: 0 <= end <= active <= start <= 1.")
        self.start_threshold = float(start_threshold)
        self.active_threshold = float(active_threshold)
        self.end_threshold = float(end_threshold)
        self.config = config
        self.state = ShotState.IDLE
        self.motion_start_frame: int | None = None
        self.motion_end_frame: int | None = None
        self.peak_frame: int | None = None
        self.peak_energy = 0.0
        self._preparation_frames = 0
        self._swing_frames = 0
        self._stable_frames = 0
        self._cooldown_remaining = 0
        self._triggered = False
        self.trace: list[StateTraceRow] = []

    def update(self, frame_index: int, energy: float) -> StateTraceRow:
        """Advance the state machine by one frame."""
        energy = float(energy)
        transition = ""
        prediction_triggered = False

        if energy > self.peak_energy:
            self.peak_energy = energy
            self.peak_frame = int(frame_index)

        if self.state == ShotState.IDLE:
            if energy >= self.start_threshold:
                self.state = ShotState.PREPARATION
                self.motion_start_frame = int(frame_index)
                self._preparation_frames = 1
                transition = "idle_to_preparation"

        elif self.state == ShotState.PREPARATION:
            if energy >= self.active_threshold:
                self._preparation_frames += 1
                if self._preparation_frames >= self.config.min_preparation_frames:
                    self.state = ShotState.BACKSWING
                    transition = "preparation_to_backswing"
            else:
                self.state = ShotState.IDLE
                self.motion_start_frame = None
                self._preparation_frames = 0
                transition = "preparation_to_idle"

        elif self.state == ShotState.BACKSWING:
            self._swing_frames += 1
            if energy >= self.start_threshold:
                self.state = ShotState.SWING
                transition = "backswing_to_swing"
            elif self._swing_frames >= self.config.min_swing_frames:
                self.state = ShotState.SWING
                transition = "backswing_to_swing_by_duration"

        elif self.state == ShotState.SWING:
            self._swing_frames += 1
            if self._swing_frames >= self.config.min_swing_frames and energy < self.active_threshold:
                self.state = ShotState.FOLLOW_THROUGH
                self._stable_frames = 1 if energy <= self.end_threshold else 0
                transition = "swing_to_follow_through"

        elif self.state == ShotState.FOLLOW_THROUGH:
            if energy <= self.end_threshold:
                self._stable_frames += 1
            else:
                self._stable_frames = 0
            if self._stable_frames >= self.config.stabilization_frames:
                self.state = ShotState.COMPLETED
                self.motion_end_frame = int(frame_index)
                transition = "follow_through_to_completed"
                if not self._triggered:
                    prediction_triggered = True
                    self._triggered = True

        elif self.state == ShotState.COMPLETED:
            self.state = ShotState.COOLDOWN
            self._cooldown_remaining = self.config.cooldown_frames
            transition = "completed_to_cooldown"

        elif self.state == ShotState.COOLDOWN:
            self._cooldown_remaining -= 1
            if self._cooldown_remaining <= 0 and energy <= self.active_threshold:
                self.state = ShotState.IDLE
                transition = "cooldown_to_idle"

        row = StateTraceRow(
            frame_index=int(frame_index),
            energy=energy,
            state=self.state.value,
            transition=transition,
            prediction_triggered=prediction_triggered,
        )
        self.trace.append(row)
        return row

    def force_complete_at_sequence_end(self, frame_index: int) -> StateTraceRow | None:
        """Emit one final trigger at sequence end if a shot is active but not completed."""
        if self._triggered or self.motion_start_frame is None:
            return None
        if self.state in {ShotState.PREPARATION, ShotState.BACKSWING, ShotState.SWING, ShotState.FOLLOW_THROUGH}:
            self.state = ShotState.COMPLETED
            self.motion_end_frame = int(frame_index)
            self._triggered = True
            row = StateTraceRow(
                frame_index=int(frame_index),
                energy=self.trace[-1].energy if self.trace else 0.0,
                state=self.state.value,
                transition="sequence_end_to_completed",
                prediction_triggered=True,
            )
            self.trace.append(row)
            return row
        return None

    @property
    def triggered(self) -> bool:
        return self._triggered
