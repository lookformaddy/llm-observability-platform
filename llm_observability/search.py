"""Trace search and filtering.

Filters compose with AND semantics; every filter is optional. Text search
matches span names and attribute values case-insensitively — it is a
debugging aid, not a replacement for structured filters.
"""

from __future__ import annotations

from dataclasses import dataclass

from llm_observability.models import Trace


@dataclass(frozen=True)
class TraceFilter:
    tenant_id: str | None = None
    model: str | None = None
    errored_only: bool = False
    min_latency_ms: int | None = None
    max_latency_ms: int | None = None
    min_feedback: float | None = None
    text: str | None = None

    def matches(self, trace: Trace) -> bool:
        if self.tenant_id is not None and trace.tenant_id != self.tenant_id:
            return False
        if self.model is not None and not any(
                s.model == self.model for s in trace.model_spans):
            return False
        if self.errored_only and not trace.errored:
            return False
        if self.min_latency_ms is not None and trace.latency_ms < self.min_latency_ms:
            return False
        if self.max_latency_ms is not None and trace.latency_ms > self.max_latency_ms:
            return False
        if self.min_feedback is not None:
            scores = [s.feedback_score for s in trace.spans
                      if s.feedback_score is not None]
            if not scores or min(scores) < self.min_feedback:
                return False
        if self.text is not None:
            needle = self.text.lower()
            haystacks = [s.name.lower() for s in trace.spans]
            haystacks += [v.lower() for s in trace.spans for v in s.attributes.values()]
            if not any(needle in h for h in haystacks):
                return False
        return True


def search(traces: list[Trace], filt: TraceFilter) -> list[Trace]:
    return [t for t in traces if filt.matches(t)]
