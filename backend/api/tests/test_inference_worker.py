"""Process-isolated inference worker regression tests."""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path

from backend.api.inference_worker import (
    InferenceWorkerFailedError,
    InferenceWorkerTimeoutError,
    active_worker_pids,
    run_raw_video_in_process,
)


def _success_worker(path: Path) -> dict:
    return {"ok": True, "name": path.name, "bytes": len(path.read_bytes())}


def _sleep_worker(path: Path) -> dict:
    time.sleep(10)
    return {"ok": True}


def _crash_worker(path: Path) -> dict:
    os._exit(7)


def _exception_worker(path: Path) -> dict:
    raise RuntimeError("controlled failure")


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class InferenceWorkerTests(unittest.TestCase):
    def _fixture(self) -> Path:
        tmp = tempfile.NamedTemporaryFile(prefix="smart-cricket-worker-", suffix=".mp4", delete=False)
        tmp.write(b"video")
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return Path(tmp.name)

    def test_worker_returns_structured_success(self) -> None:
        path = self._fixture()
        result = run_raw_video_in_process(path, timeout_seconds=5, worker=_success_worker)
        self.assertEqual(result["ok"], True)
        self.assertEqual(result["bytes"], 5)
        self.assertEqual(active_worker_pids(), ())

    def test_timeout_terminates_process_and_releases_tracking(self) -> None:
        path = self._fixture()
        with self.assertRaises(InferenceWorkerTimeoutError) as ctx:
            run_raw_video_in_process(path, timeout_seconds=1, worker=_sleep_worker)
        self.assertIsNotNone(ctx.exception.worker_pid)
        if ctx.exception.worker_pid:
            self.assertFalse(_pid_alive(ctx.exception.worker_pid))
        self.assertEqual(active_worker_pids(), ())

    def test_crash_returns_worker_failure(self) -> None:
        path = self._fixture()
        with self.assertRaises(InferenceWorkerFailedError) as ctx:
            run_raw_video_in_process(path, timeout_seconds=5, worker=_crash_worker)
        self.assertIn("worker_exit_7", ctx.exception.detail_code)
        self.assertEqual(active_worker_pids(), ())

    def test_exception_returns_worker_failure_without_traceback(self) -> None:
        path = self._fixture()
        with self.assertRaises(InferenceWorkerFailedError) as ctx:
            run_raw_video_in_process(path, timeout_seconds=5, worker=_exception_worker)
        self.assertEqual(ctx.exception.detail_code, "raw_video_analysis_failed")
        self.assertIn("controlled failure", str(ctx.exception))
        self.assertNotIn("Traceback", str(ctx.exception))
        self.assertEqual(active_worker_pids(), ())

    def test_repeated_timeouts_do_not_accumulate_workers(self) -> None:
        path = self._fixture()
        for _ in range(3):
            with self.assertRaises(InferenceWorkerTimeoutError):
                run_raw_video_in_process(path, timeout_seconds=1, worker=_sleep_worker)
            self.assertEqual(active_worker_pids(), ())

    def test_success_after_timeout_recovers_capacity(self) -> None:
        path = self._fixture()
        with self.assertRaises(InferenceWorkerTimeoutError):
            run_raw_video_in_process(path, timeout_seconds=1, worker=_sleep_worker)
        result = run_raw_video_in_process(path, timeout_seconds=5, worker=_success_worker)
        self.assertEqual(result["ok"], True)


if __name__ == "__main__":
    unittest.main()
