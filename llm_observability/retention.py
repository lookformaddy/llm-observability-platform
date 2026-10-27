"""Retention and sampling policies.

Sampling is deterministic: a trace is kept iff ``hash(trace_id) mod 100``
falls below ``rate * 100``. The same trace always gets the same decision,
so re-ingestion and replay agree — random sampling would make retention
non-reproducible and tests flaky.

Retention pruning is age-based: traces whose newest span ends before
``cutoff_ms`` are dropped. Error traces bypass the default sample rate
(bugs are the traces you most need) unless the caller says otherwise.
"""

from __future__ import annotations

import hashlib

from llm_observability.models import Trace


def _bucket(trace_id: str) -> int:
    digest = hashlib.sha256(trace_id.encode()).hexdigest()
    return int(digest, 16) % 100


def should_keep(trace: Trace, default_rate: float, error_rate: float = 1.0) -> bool:
    rate = error_rate if trace.errored else default_rate
    if rate >= 1.0:
        return True
    if rate <= 0.0:
        return False
    return _bucket(trace.trace_id) < rate * 100


def sample(traces: list[Trace], default_rate: float, error_rate: float = 1.0) -> list[Trace]:
    return [t for t in traces if should_keep(t, default_rate, error_rate)]


def prune_older_than(traces: list[Trace], cutoff_ms: int) -> tuple[list[Trace], list[Trace]]:
    """Split traces into (kept, pruned) by newest span end time."""
    kept, pruned = [], []
    for trace in traces:
        newest = max((s.end_ms for s in trace.spans), default=0)
        (pruned if newest < cutoff_ms else kept).append(trace)
    return kept, pruned
