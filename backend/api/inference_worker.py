"""Process-isolated raw video inference execution."""

from __future__ import annotations

import multiprocessing as mp
import os
import queue
import signal
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

WorkerCallable = Callable[[Path], dict[str, Any]]

_ACTIVE_WORKERS: set[int] = set()
_ACTIVE_WORKERS_LOCK = threading.Lock()


@dataclass(frozen=True)
class WorkerEnvelope:
    """Safe process result envelope."""

    status: str
    result: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    timing: dict[str, Any] | None = None
    worker_pid: int | None = None


class InferenceWorkerFailedError(RuntimeError):
    """Raised when the isolated worker cannot produce a usable result."""

    error_code = "inference_worker_failed"

    def __init__(self, message: str, *, worker_pid: int | None = None, detail_code: str | None = None) -> None:
        super().__init__(message)
        self.worker_pid = worker_pid
        self.detail_code = detail_code or self.error_code


class InferenceWorkerTimeoutError(TimeoutError):
    """Raised when the isolated worker exceeds its hard execution timeout."""

    error_code = "analysis_timeout"

    def __init__(self, message: str, *, worker_pid: int | None = None) -> None:
        super().__init__(message)
        self.worker_pid = worker_pid


def _record_worker(pid: int) -> None:
    with _ACTIVE_WORKERS_LOCK:
        _ACTIVE_WORKERS.add(pid)


def _forget_worker(pid: int | None) -> None:
    if pid is None:
        return
    with _ACTIVE_WORKERS_LOCK:
        _ACTIVE_WORKERS.discard(pid)


def active_worker_pids() -> tuple[int, ...]:
    """Return tracked worker PIDs for tests and diagnostics."""

    with _ACTIVE_WORKERS_LOCK:
        return tuple(sorted(_ACTIVE_WORKERS))


def terminate_active_workers(timeout_seconds: float = 2.0) -> None:
    """Best-effort cleanup for shutdown hooks."""

    with _ACTIVE_WORKERS_LOCK:
        pids = tuple(_ACTIVE_WORKERS)
    deadline = time.monotonic() + timeout_seconds
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            _forget_worker(pid)
        except OSError:
            continue
    while time.monotonic() < deadline:
        remaining = []
        for pid in pids:
            if _pid_alive(pid):
                remaining.append(pid)
            else:
                _forget_worker(pid)
        if not remaining:
            return
        time.sleep(0.05)
    for pid in pids:
        if not _pid_alive(pid):
            _forget_worker(pid)
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            continue
        finally:
            _forget_worker(pid)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _worker_entry(input_path: str, result_queue: mp.Queue, worker: WorkerCallable | None) -> None:
    started = time.perf_counter()
    worker_pid = os.getpid()
    try:
        if worker is None:
            # Keep test/control workers lightweight and import the ML stack only
            # inside the production inference child.
            from ml.src.inference.raw_video_pipeline import analyze_raw_video

            worker = analyze_raw_video
        result = worker(Path(input_path))
        envelope = WorkerEnvelope(
            status="success",
            result=result,
            timing={"duration_seconds": round(time.perf_counter() - started, 3)},
            worker_pid=worker_pid,
        )
    except Exception as exc:
        error_code = getattr(exc, "error_code", "inference_failed")
        envelope = WorkerEnvelope(
            status="error",
            error_code=error_code,
            error_message=f"{type(exc).__name__}: {exc}",
            timing={"duration_seconds": round(time.perf_counter() - started, 3)},
            worker_pid=worker_pid,
        )
    result_queue.put(envelope.__dict__)


def run_raw_video_in_process(
    input_path: Path,
    *,
    timeout_seconds: int,
    worker: WorkerCallable | None = None,
) -> dict[str, Any]:
    """Run raw-video inference in a spawned child process with hard timeout."""

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive.")

    context = mp.get_context("spawn")
    result_queue: mp.Queue = context.Queue(maxsize=1)
    process = context.Process(target=_worker_entry, args=(str(input_path), result_queue, worker), daemon=False)
    process.start()
    _record_worker(process.pid or -1)
    try:
        process.join(timeout_seconds)
        if process.is_alive():
            process.terminate()
            process.join(2)
            if process.is_alive():
                process.kill()
                process.join(2)
            raise InferenceWorkerTimeoutError(
                "Analysis took too long and was stopped. Try a shorter, clearer clip.",
                worker_pid=process.pid,
            )
        try:
            envelope = result_queue.get_nowait()
        except queue.Empty as exc:
            raise InferenceWorkerFailedError(
                "Inference worker exited without returning a result.",
                worker_pid=process.pid,
                detail_code=("mediapipe_init_failed" if process.exitcode in {-6, 134} else f"worker_exit_{process.exitcode}"),
            ) from exc
        if not isinstance(envelope, dict) or envelope.get("status") not in {"success", "error"}:
            raise InferenceWorkerFailedError("Inference worker returned an invalid result envelope.", worker_pid=process.pid)
        if envelope["status"] == "success" and isinstance(envelope.get("result"), dict):
            return envelope["result"]
        raise InferenceWorkerFailedError(
            str(envelope.get("error_message") or "Inference worker failed."),
            worker_pid=process.pid,
            detail_code=str(envelope.get("error_code") or "inference_worker_failed"),
        )
    finally:
        _forget_worker(process.pid)
        result_queue.close()
        result_queue.join_thread()
