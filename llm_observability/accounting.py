"""Per-request cost, latency, and token accounting.

Cost is computed only for model spans with a known price entry; unknown
models contribute tokens and latency but zero cost, and are reported as
``unpriced_models`` so operators notice the gap instead of silently
under-reporting spend.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from llm_observability.config import ModelPrice, Settings
from llm_observability.models import SpanKind, Trace


@dataclass(frozen=True)
class TraceCost:
    trace_id: str
    tenant_id: str
    cost_usd: float
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    unpriced_models: tuple[str, ...] = ()


def span_cost(span, prices: dict[str, ModelPrice]) -> float:
    if span.model is None or span.model not in prices:
        return 0.0
    price = prices[span.model]
    return (span.prompt_tokens / 1000 * price.prompt_per_1k
            + span.completion_tokens / 1000 * price.completion_per_1k)


def trace_cost(trace: Trace, settings: Settings | None = None) -> TraceCost:
    settings = settings or Settings()
    cost = 0.0
    prompt = completion = 0
    unpriced: set[str] = set()
    for span in trace.model_spans:
        prompt += span.prompt_tokens
        completion += span.completion_tokens
        if span.model is None or span.model not in settings.prices:
            if span.model:
                unpriced.add(span.model)
        else:
            cost += span_cost(span, settings.prices)
    return TraceCost(
        trace_id=trace.trace_id, tenant_id=trace.tenant_id,
        cost_usd=round(cost, 6), prompt_tokens=prompt,
        completion_tokens=completion, latency_ms=trace.latency_ms,
        unpriced_models=tuple(sorted(unpriced)),
    )


@dataclass
class Attribution:
    """Aggregated cost/tokens keyed by (tenant, model)."""

    by_tenant_model: dict[tuple[str, str], dict[str, float | int]] = field(default_factory=dict)

    def add_trace(self, trace: Trace, settings: Settings | None = None) -> None:
        settings = settings or Settings()
        for span in trace.model_spans:
            if span.kind is not SpanKind.MODEL:
                continue
            key = (trace.tenant_id, span.model or "unknown")
            bucket = self.by_tenant_model.setdefault(
                key, {"cost_usd": 0.0, "prompt_tokens": 0, "completion_tokens": 0, "calls": 0})
            bucket["cost_usd"] = round(float(bucket["cost_usd"]) + span_cost(span, settings.prices), 6)
            bucket["prompt_tokens"] = int(bucket["prompt_tokens"]) + span.prompt_tokens
            bucket["completion_tokens"] = int(bucket["completion_tokens"]) + span.completion_tokens
            bucket["calls"] = int(bucket["calls"]) + 1

    @classmethod
    def from_traces(cls, traces: list[Trace], settings: Settings | None = None) -> "Attribution":
        attr = cls()
        for trace in traces:
            attr.add_trace(trace, settings)
        return attr
