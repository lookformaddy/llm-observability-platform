from llm_observability.accounting import Attribution, trace_cost
from llm_observability.config import Settings


def test_trace_cost_uses_price_table(traces):
    healthy = next(t for t in traces if t.trace_id == "t-healthy")
    cost = trace_cost(healthy, Settings())
    # generic-small: 1200/1000*0.0005 + 300/1000*0.0015 = 0.00105
    assert cost.cost_usd == 0.00105
    assert cost.prompt_tokens == 1200 and cost.latency_ms == 850
    assert cost.unpriced_models == ()


def test_unknown_model_costs_zero_but_is_flagged(traces):
    from llm_observability.models import Span, SpanKind
    from llm_observability.ingestion import TraceStore
    store = TraceStore()
    store.ingest([Span("x", "t-u", None, SpanKind.MODEL, "call", 0, 10,
                       model="mystery-model", prompt_tokens=100)])
    cost = trace_cost(store.get_trace("t-u"), Settings())
    assert cost.cost_usd == 0.0 and cost.unpriced_models == ("mystery-model",)


def test_attribution_groups_by_tenant_model(traces):
    attr = Attribution.from_traces(traces, Settings())
    bucket = attr.by_tenant_model[("tenant-a", "generic-large")]
    assert bucket["calls"] == 1 and bucket["prompt_tokens"] == 2000
    assert ("tenant-b", "generic-large") in attr.by_tenant_model
