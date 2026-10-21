"""Observability on the standard library: JSON logs, Prometheus metrics, simple spans.

Rules (docs/06-operations/observability.md):
- never log the job description or a quote from it; log lengths, counts and ids
- every log line and span carries the request id, so a support ticket can be traced
- metrics answer the SLO questions: availability, latency, and how much goes to review
"""

from __future__ import annotations

import json
import sys
import threading
import time
import uuid
from contextlib import contextmanager

LATENCY_BUCKETS_MS = (5, 10, 25, 50, 100, 250, 500, 1000, 2500)


def log(event: str, **fields) -> None:
    row = {"ts": round(time.time(), 3), "event": event, **fields}
    sys.stderr.write(json.dumps(row, ensure_ascii=False) + "\n")


class Metrics:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.counters: dict[tuple[str, tuple], float] = {}
        self.hist: dict[tuple[str, tuple], list[float]] = {}

    def inc(self, name: str, value: float = 1.0, **labels) -> None:
        key = (name, tuple(sorted(labels.items())))
        with self.lock:
            self.counters[key] = self.counters.get(key, 0.0) + value

    def observe(self, name: str, value: float, **labels) -> None:
        key = (name, tuple(sorted(labels.items())))
        with self.lock:
            self.hist.setdefault(key, []).append(value)

    def render(self) -> str:
        def fmt(labels: tuple, extra: dict | None = None) -> str:
            items = list(labels) + list((extra or {}).items())
            return "{" + ",".join(f'{k}="{v}"' for k, v in items) + "}" if items else ""

        out = []
        with self.lock:
            for (name, labels), v in sorted(self.counters.items()):
                out.append(f"{name}{fmt(labels)} {v:g}")
            for (name, labels), values in sorted(self.hist.items()):
                for b in LATENCY_BUCKETS_MS:
                    out.append(f"{name}_bucket{fmt(labels, {'le': b})} {sum(v <= b for v in values)}")
                out.append(f"{name}_bucket{fmt(labels, {'le': '+Inf'})} {len(values)}")
                out.append(f"{name}_sum{fmt(labels)} {sum(values):.3f}")
                out.append(f"{name}_count{fmt(labels)} {len(values)}")
        return "\n".join(out) + "\n"


METRICS = Metrics()


def new_id() -> str:
    return uuid.uuid4().hex[:16]


@contextmanager
def span(name: str, trace_id: str, **attrs):
    """A timed unit of work. Emitted as a log line; an OpenTelemetry exporter would send it instead."""
    span_id = new_id()
    t0 = time.perf_counter()
    status = "ok"
    try:
        yield span_id
    except Exception:
        status = "error"
        raise
    finally:
        log("span", name=name, trace_id=trace_id, span_id=span_id, status=status,
            duration_ms=round((time.perf_counter() - t0) * 1000, 2), **attrs)
