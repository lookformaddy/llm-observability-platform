"""Demo entry point: ingest synthetic traces and print a summary.

Usage: python -m llm_observability  (from the project root)
"""

from llm_observability.accounting import Attribution, trace_cost
from llm_observability.alerting import Rule, evaluate_all
from llm_observability.config import Settings
from llm_observability.examples import synthetic_traces
from llm_observability.ingestion import TraceStore
from llm_observability.metrics import summarize


def main() -> None:
    settings = Settings()
    store = TraceStore()
    store.ingest(synthetic_traces())
    traces = store.all_traces()
    costs = [trace_cost(t, settings).cost_usd for t in traces]
    s = summarize(traces, costs)
    print(f"traces={s.trace_count} errors={s.error_count} ({s.error_rate:.0%}) "
          f"p50={s.p50_ms}ms p95={s.p95_ms}ms total_cost=${s.total_cost_usd:.4f}")
    for (tenant, model), bucket in sorted(Attribution.from_traces(traces, settings).by_tenant_model.items()):
        print(f"  {tenant}/{model}: {bucket['calls']} calls, ${bucket['cost_usd']:.4f}")
    for alert in evaluate_all([Rule("p95-slo", max_p95_ms=2000, max_error_rate=0.1)], traces):
        print(f"ALERT [{alert.severity}] {alert.rule_name}: {alert.message}")


if __name__ == "__main__":
    main()
