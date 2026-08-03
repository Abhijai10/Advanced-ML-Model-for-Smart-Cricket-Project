"""Tests for Phase 9 shot state-machine behavior."""

from __future__ import annotations

import unittest

from segmentation.state_machine import ShotStateMachine


class ShotStateMachineTests(unittest.TestCase):
    def test_single_trigger_for_one_motion(self) -> None:
        machine = ShotStateMachine(start_threshold=0.5, active_threshold=0.3, end_threshold=0.15)
        energies = [0.0, 0.6, 0.55, 0.7, 0.8, 0.4, 0.2, 0.1, 0.08, 0.05, 0.04]
        triggers = [machine.update(i, e).prediction_triggered for i, e in enumerate(energies)]
        self.assertEqual(sum(triggers), 1)
        self.assertTrue(machine.triggered)

    def test_cooldown_prevents_repeated_trigger(self) -> None:
        machine = ShotStateMachine(start_threshold=0.5, active_threshold=0.3, end_threshold=0.15)
        energies = [0.0, 0.6, 0.6, 0.7, 0.4, 0.1, 0.1, 0.1, 0.1, 0.8, 0.9, 0.1, 0.1, 0.1, 0.1]
        triggers = [machine.update(i, e).prediction_triggered for i, e in enumerate(energies)]
        self.assertEqual(sum(triggers), 1)

    def test_force_complete_sequence_end(self) -> None:
        machine = ShotStateMachine(start_threshold=0.5, active_threshold=0.3, end_threshold=0.15)
        for i, e in enumerate([0.0, 0.6, 0.6, 0.7, 0.7]):
            machine.update(i, e)
        forced = machine.force_complete_at_sequence_end(4)
        self.assertIsNotNone(forced)
        self.assertTrue(forced.prediction_triggered)


if __name__ == "__main__":
    unittest.main()
