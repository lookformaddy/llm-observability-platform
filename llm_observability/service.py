"""Optional FastAPI service over the stdlib core.

Importing this module without FastAPI installed raises nothing: ``app``
is ``None`` and ``create_app()`` raises a clear RuntimeError. This keeps the
core importable (and testable) in minimal environments.
"""

from __future__ import annotations

try:
    from fastapi import Body, FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError:  # pragma: no cover - exercised by the skip test
    FastAPI = None  # type: ignore[assignment]

from llm_observability.accounting import trace_cost
from llm_observability.config import Settings
from llm_observability.ingestion import TraceStore
from llm_observability.metrics import summarize
from llm_observability.models import Span, SpanKind
from llm_observability.search import TraceFilter, search

app = None

# Module level (not nested in create_app): FastAPI/pydantic must resolve the
# model at route-registration time, and a function-local class breaks that.
if FastAPI is not None:
    class SpanIn(BaseModel):
        span_id: str
        trace_id: str
        parent_id: str | None = None
        kind: SpanKind = SpanKind.OTHER
        name: str
        start_ms: int
        end_ms: int
        tenant_id: str = "default"
        model: str | None = None
        prompt_tokens: int = 0
        completion_tokens: int = 0
        status: str = "ok"
        feedback_score: float | None = None
        eval_score: float | None = None


def create_app(store: TraceStore | None = None, settings: Settings | None = None):
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed; install requirements.txt to run the service")
    store = store or TraceStore()
    settings = settings or Settings()
    api = FastAPI(title="LLM Observability Platform")

    @api.post("/spans", status_code=202)
    def ingest_spans(spans: list[SpanIn] = Body(...)):
        parsed = [Span(**s.model_dump()) for s in spans]
        return {"ingested_new": store.ingest(parsed)}

    @api.get("/traces/{trace_id}")
    def get_trace(trace_id: str):
        trace = store.get_trace(trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="trace not found")
        cost = trace_cost(trace, settings)
        return {"trace_id": trace.trace_id, "tenant_id": trace.tenant_id,
                "latency_ms": trace.latency_ms, "errored": trace.errored,
                "cost_usd": cost.cost_usd, "total_tokens": cost.prompt_tokens + cost.completion_tokens,
                "spans": [{"span_id": s.span_id, "name": s.name, "kind": s.kind.value,
                           "latency_ms": s.latency_ms, "status": s.status} for s in trace.spans]}

    @api.get("/summary")
    def summary(tenant_id: str | None = None, errored_only: bool = False):
        traces = search(store.all_traces(), TraceFilter(tenant_id=tenant_id, errored_only=errored_only))
        costs = [trace_cost(t, settings).cost_usd for t in traces]
        s = summarize(traces, costs)
        return {"trace_count": s.trace_count, "error_count": s.error_count,
                "error_rate": s.error_rate, "p50_ms": s.p50_ms, "p95_ms": s.p95_ms,
                "p99_ms": s.p99_ms, "avg_feedback": s.avg_feedback,
                "avg_eval": s.avg_eval, "total_cost_usd": s.total_cost_usd}

    return api


if FastAPI is not None:  # pragma: no cover
    app = create_app()
