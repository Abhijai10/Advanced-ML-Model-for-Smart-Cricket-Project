"""Unit coverage for MediaPipe reliability controls without native initialization."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.api.config import APISettings, validate_runtime_settings
from ml.src.preprocessing.extract_pose import resolve_mediapipe_delegate


class MediaPipeConfigurationTests(unittest.TestCase):
    def test_delegate_values_resolve_without_initializing_native_runtime(self) -> None:
        with patch("ml.src.preprocessing.extract_pose.platform.system", return_value="Linux"):
            self.assertIsNone(resolve_mediapipe_delegate("auto"))
        with patch("ml.src.preprocessing.extract_pose.platform.system", return_value="Darwin"):
            self.assertEqual(resolve_mediapipe_delegate("auto").name, "CPU")
        self.assertEqual(resolve_mediapipe_delegate("cpu").name, "CPU")
        self.assertEqual(resolve_mediapipe_delegate("gpu").name, "GPU")

    def test_invalid_delegate_is_rejected_by_runtime_configuration(self) -> None:
        settings = APISettings(mediapipe_delegate="metal")
        codes = {issue.code for issue in validate_runtime_settings(settings)}
        self.assertIn("invalid_mediapipe_delegate", codes)

    def test_invalid_delegate_fails_clearly_at_pose_configuration_boundary(self) -> None:
        with self.assertRaisesRegex(ValueError, "auto, cpu, or gpu"):
            resolve_mediapipe_delegate("metal")
