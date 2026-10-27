"""Quality signals: latency percentiles, error rates, feedback/eval means.

Percentiles use the nearest-rank method so results are deterministic and
independent of interpolation choices — important when an SLO alert must be
reproducible from the same trace set.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from llm_observability.models import Trace


def percentile(values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile; pct in (0, 100]. Returns None for empty input."""
    if not values or not 0 < pct <= 100:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


@dataclass(frozen=True)
class QualitySummary:
    trace_count: int
    error_count: int
    error_rate: float
    p50_ms: float | None
    p95_ms: float | None
    p99_ms: float | None
    avg_feedback: float | None
    avg_eval: float | None
    total_cost_usd: float


def summarize(traces: list[Trace], costs: list[float] | None = None) -> QualitySummary:
    latencies = [float(t.latency_ms) for t in traces]
    errors = sum(1 for t in traces if t.errored)
    feedback = [s.feedback_score for t in traces for s in t.spans
                if s.feedback_score is not None]
    evals = [s.eval_score for t in traces for s in t.spans if s.eval_score is not None]
    mean = lambda xs: (sum(xs) / len(xs)) if xs else None
    return QualitySummary(
        trace_count=len(traces),
        error_count=errors,
        error_rate=(errors / len(traces)) if traces else 0.0,
        p50_ms=percentile(latencies, 50),
        p95_ms=percentile(latencies, 95),
        p99_ms=percentile(latencies, 99),
        avg_feedback=mean(feedback),
        avg_eval=mean(evals),
        total_cost_usd=round(sum(costs or []), 6),
    )


def group_latencies(traces: list[Trace]) -> dict[str, list[float]]:
    """Latency series keyed by tenant, for per-tenant SLO evaluation."""
    out: dict[str, list[float]] = {}
    for trace in traces:
        out.setdefault(trace.tenant_id, []).append(float(trace.latency_ms))
    return out
