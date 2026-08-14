"""Small observability primitives for Smart Cricket."""

from __future__ import annotations

import hashlib
import logging
import threading
from collections import defaultdict
from typing import Any

from .config import SETTINGS


logger = logging.getLogger("smart_cricket.api")


class MetricsRegistry:
    """In-process metrics registry with Prometheus-compatible rendering."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._observations: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = defaultdict(list)

    def increment(self, name: str, value: float = 1.0, **labels: object) -> None:
        with self._lock:
            self._counters[(name, _labels(labels))] += value

    def observe(self, name: str, value: float, **labels: object) -> None:
        with self._lock:
            self._observations[(name, _labels(labels))].append(float(value))

    def render_prometheus(self) -> str:
        lines: list[str] = []
        with self._lock:
            counters = dict(self._counters)
            observations = {key: list(values) for key, values in self._observations.items()}
        for (name, labels), value in sorted(counters.items()):
            lines.append(f"{name}_total{_format_labels(labels)} {value:g}")
        for (name, labels), values in sorted(observations.items()):
            if not values:
                continue
            lines.append(f"{name}_seconds_count{_format_labels(labels)} {len(values)}")
            lines.append(f"{name}_seconds_sum{_format_labels(labels)} {sum(values):.6f}")
        return "\n".join(lines) + "\n"

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._observations.clear()


def _labels(labels: dict[str, object]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(key), str(value)) for key, value in labels.items()))


def _format_labels(labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    body = ",".join(f'{key}="{value.replace(chr(34), "")}"' for key, value in labels)
    return "{" + body + "}"


METRICS = MetricsRegistry()


def pseudonymous_user_id(user_id: str | None) -> str | None:
    if not user_id:
        return None
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:16]


def initialize_sentry() -> bool:
    """Initialize Sentry only when configured and installed."""

    if not SETTINGS.sentry_dsn:
        return False
    try:
        import sentry_sdk  # type: ignore[import-not-found]
    except Exception:
        logger.warning("observability_unavailable", extra={"event": "sentry_sdk_missing"})
        return False

    def before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
        request = event.get("request")
        if isinstance(request, dict):
            headers = request.get("headers")
            if isinstance(headers, dict):
                for key in list(headers):
                    if key.lower() in {"authorization", "cookie", "x-api-key", "apikey"}:
                        headers[key] = "[redacted]"
        return event

    sentry_sdk.init(dsn=SETTINGS.sentry_dsn, before_send=before_send, traces_sample_rate=0.0, send_default_pii=False)
    return True
