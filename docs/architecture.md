# Architecture

## Data model

```
Trace (trace_id, tenant_id)
 └─ Span (span_id, parent_id, kind, name, start_ms, end_ms,
          tenant_id, model, prompt_tokens, completion_tokens,
          status, error_type, feedback_score, eval_score, attributes)
```

- A trace is one end-to-end request. Spans form a tree via `parent_id`.
  Trace latency is the full span envelope (max end − min start), not the
  root span's own duration — the root (e.g. a prompt render) typically
  ends long before its model/tool descendants finish.
- Timestamps are epoch milliseconds (int) so arithmetic is exact and
  deterministic; conversion to wall-clock happens only at the API boundary.
- `kind` distinguishes prompt renders, model calls, tool calls, and
  retrieval steps. Only model spans carry tokens and cost.
- Tenant is fixed by the first span seen for a trace; a later span claiming
  a different tenant is treated as a data bug, not a tenant move — silently
  re-homing traces would corrupt cost attribution.

```
                    ┌─────────────────────────┐
  POST /spans ────► │  TraceStore (ingestion) │
                    └────────┬────────────────┘
        ┌──────────┬─────────┼──────────┬──────────┐
        ▼          ▼         ▼          ▼          ▼
  accounting  metrics   alerting   search   retention
  cost/token  p50/p95/  SLO rules  filters   hash sampling
  attribution p99,error                       + age prune
              rates
```

## Module responsibilities

| Module | Responsibility | Depends on |
|---|---|---|
| `models` | Span/Trace dataclasses + validation | stdlib |
| `config` | Price table, env-driven settings | stdlib |
| `ingestion` | Thread-safe store, dedupe, trace assembly | models |
| `accounting` | Span/trace cost, (tenant, model) attribution | config, models |
| `metrics` | Percentiles, error rates, feedback/eval means | models |
| `alerting` | Stateless SLO rules → alerts | metrics |
| `retention` | Deterministic sampling, age pruning | models |
| `search` | Composable AND filters | models |
| `service` | FastAPI adapter (optional) | all of the above |
| `examples` | Synthetic demo traces | models |

## Key design decisions

1. **Immutability.** Spans are frozen dataclasses. Billing-relevant records
   must not change after ingestion.
2. **Nearest-rank percentiles.** Reproducible from the same trace set;
   interpolation would make SLO alerts depend on an arbitrary choice.
3. **Deterministic sampling.** `sha256(trace_id) mod 100` decides the
   bucket, so replay and re-ingestion agree. Error traces bypass the
   default rate — bugs are the traces you most need.
4. **Stateless rules.** Alert evaluation is a pure function over a trace
   window. Dedupe, suppression windows, and paging live downstream.
5. **Explicit store swap point.** The in-memory store is the reference
   backend; a production store (columnar/OLAP) implements the same
   interface. Nothing else in the codebase knows which backend is in use.

## What production would add (out of scope, deliberately)

- Durable, partitioned storage (e.g. ClickHouse) + a retention job that
  calls `prune_older_than` on a schedule.
- Streaming ingestion (Kafka/Kinesis) with backpressure and schema
  validation at the edge.
- Authentication/authorization per tenant, and PII redaction on span
  attributes before storage.
- A dashboard UI and a notification pipeline (Slack/PagerDuty) consuming
  `Alert` objects, with dedupe and escalation.
- Distributed tracing propagation (traceparent headers) so spans from
  multiple services join the same trace.
- Cost forecasting and anomaly detection on top of the attribution series.

## Failure modes considered

- **Out-of-order / partial spans:** assembly is order-independent; traces
  without a root still report a latency.
- **Unknown model prices:** cost zero + explicit `unpriced_models` flag,
  never silent under-reporting.
- **Empty windows:** summaries return `None` percentiles and 0.0 error
  rate; rules refuse to fire below `min_trace_count`.
- **Clock skew:** negative durations are rejected at the model boundary
  (`end_ms < start_ms` raises), so bad clients fail loudly at ingest.
```

## Diagram description

```
Client app ── spans ──> [Ingest API] ──> [TraceStore]
                                              │
        ┌──────────┬────────┬────────┬────────┼─────────┐
        ▼          ▼        ▼        ▼        ▼         ▼
     Cost      Quality   Alerts   Search   Sampling  Attribution
   accounting  metrics  alerting  filters  retention  by tenant/model
```

Trace search reads the same store as alerting and accounting, so every
view of the system agrees on the same trace set.
