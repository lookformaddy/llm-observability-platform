"""Trace ingestion and storage.

``TraceStore`` is an in-memory, thread-safe store — the reference backend.
A production deployment swaps it for a columnar/OLAP store behind the same
interface; ingestion semantics (validation, trace assembly, dedupe) do not
change. Spans for one trace may arrive out of order and across batches.
"""

from __future__ import annotations

import threading

from llm_observability.models import Span, Trace


class TraceStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._spans: dict[str, dict[str, Span]] = {}  # trace_id -> span_id -> Span
        self._tenants: dict[str, str] = {}  # trace_id -> tenant_id

    def ingest(self, spans: list[Span]) -> int:
        """Ingest spans; returns the number of *new* spans stored (dedupe by id)."""
        new = 0
        with self._lock:
            for span in spans:
                per_trace = self._spans.setdefault(span.trace_id, {})
                if span.span_id in per_trace:
                    continue
                per_trace[span.span_id] = span
                # Tenant is fixed by the first span seen for a trace; a later
                # span claiming a different tenant is a data bug, not a move.
                self._tenants.setdefault(span.trace_id, span.tenant_id)
                new += 1
        return new

    def get_trace(self, trace_id: str) -> Trace | None:
        with self._lock:
            per_trace = self._spans.get(trace_id)
            if not per_trace:
                return None
            spans = sorted(per_trace.values(), key=lambda s: (s.start_ms, s.span_id))
            return Trace(trace_id=trace_id, spans=spans,
                         tenant_id=self._tenants[trace_id])

    def all_traces(self) -> list[Trace]:
        with self._lock:
            ids = sorted(self._spans)
        traces = [t for t in (self.get_trace(tid) for tid in ids) if t is not None]
        return traces

    def trace_count(self) -> int:
        with self._lock:
            return len(self._spans)

    def span_count(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._spans.values())

    def drop_trace(self, trace_id: str) -> bool:
        with self._lock:
            existed = trace_id in self._spans
            self._spans.pop(trace_id, None)
            self._tenants.pop(trace_id, None)
            return existed
