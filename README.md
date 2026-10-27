# LLM Observability Platform

Production LLM applications fail in ways traditional APM cannot see: a prompt
change silently doubles cost, a slow tool call hides inside a fast-looking
response, quality degrades before any user complains. This project is a
clean-room, dependency-light observability platform for LLM apps — trace
ingestion, per-request cost/latency/token accounting, quality signals,
SLO alerting, trace search, cost attribution, and retention/sampling
policies — organized like a real enterprise codebase.

> **Clean-room note:** all code is original and all demo data is synthetic
> (see `llm_observability/examples.py`). No employer code, data, internal
> architecture, or proprietary designs are used.

## What it demonstrates

- **Trace ingestion** — spans for prompts, model calls, tool calls, and
  retrieval, assembled into traces even when spans arrive out of order;
  duplicate span ids are deduplicated.
- **Cost / latency / token accounting** — per-request cost from a
  configurable per-model price table; unpriced models cost zero *and* are
  flagged, so spend is never silently under-reported.
- **Quality signals** — nearest-rank latency percentiles (p50/p95/p99),
  error rates, user feedback and offline eval score averages.
- **SLO alerting** — stateless, testable rules (p95 latency, error rate,
  feedback floor) with a minimum-trace-count guard against noisy windows.
- **Trace search / filter** — tenant, model, error-only, latency bounds,
  feedback floor, and free-text search over span names and attributes.
- **Cost attribution** — spend, tokens, and call counts grouped by
  (tenant, model).
- **Retention / sampling** — deterministic hash-based sampling (same trace,
  same decision, every replay) with error traces kept preferentially, plus
  age-based pruning.

## Architecture overview

```
client apps ──POST /spans──> FastAPI service (llm_observability/service.py)
                                  │
                                  ▼
                        TraceStore (thread-safe, in-memory)
                                  │
        ┌─────────────┬───────────┼──────────────┬──────────────┐
   accounting.py  metrics.py  alerting.py  search.py   retention.py
   (cost/token)   (p50/p95/   (SLO rules)  (filters)   (sampling/
                   p99, error                              pruning)
                   rates)
```

The store is the only stateful component and the intended swap point: a
production deployment replaces the in-memory store with a columnar/OLAP
backend behind the same interface; ingestion semantics do not change.
See `docs/architecture.md` for the full design, including the data model,
the sampling rationale, and what a production deployment would add.

## How to run it

Core library — no third-party dependencies:

```bash
python -m llm_observability          # synthetic demo: ingest + summary + alerts
```

Tests (pytest only):

```bash
python -m venv /tmp/venv-llm-obs && source /tmp/venv-llm-obs/bin/activate
pip install -r requirements.txt      # pytest; fastapi is optional
python -m pytest -q
```

Optional API service:

```bash
pip install -r requirements.txt      # includes fastapi + uvicorn
uvicorn llm_observability.service:app --port 8000
# POST /spans, GET /traces/{trace_id}, GET /summary
```

Configuration via environment (see `.env.example`):
`LLM_OBS_PRICES` (JSON price overrides), `LLM_OBS_SAMPLE_RATE`,
`LLM_OBS_ERROR_SAMPLE_RATE`, `LLM_OBS_RETENTION_DAYS`.

## Design decisions and trade-offs

1. **Pure-stdlib core, FastAPI optional.** The observability logic must be
   testable anywhere, including minimal CI images; the HTTP layer is a thin
   adapter that degrades gracefully when FastAPI is absent.
2. **Immutable spans.** Ingestion never mutates a span, so a stored trace is
   a faithful record of what the client sent — important for billing disputes.
3. **Nearest-rank percentiles.** Deterministic and reproducible from the
   same trace set; interpolation choices would make SLO alerts
   non-reproducible.
4. **Deterministic hash sampling, not random.** Random sampling makes
   retention non-reproducible and tests flaky; hash bucketing keeps the same
   decision across replays.
5. **Stateless alert rules.** Deduplication and paging belong in the
   notification layer, not in SLO evaluation, keeping rules unit-testable.
6. **In-memory store as the reference backend.** Correctness and clarity
   first; the swap point is explicit and documented rather than hidden
   behind a half-built persistence layer.
7. **Unpriced models flagged, not hidden.** A zero cost with no warning
   would silently under-report spend — the worse failure mode.

## CI note

The GitHub Actions workflow is shipped as `docs/github-actions-ci.yml`,
**not** `.github/workflows/ci.yml`: the GitHub integration used for
publishing rejects files under `.github/workflows/` (it lacks the Workflows
permission). To activate CI, move that file to `.github/workflows/ci.yml`
in the repository after publishing.

## Project layout

```
llm_observability/   core package (models, config, ingestion, accounting,
                     metrics, alerting, retention, search, service, examples)
tests/               pytest suite for the core logic and the API layer
docs/architecture.md full design document
docs/github-actions-ci.yml  CI definition (see CI note above)
examples/            (see llm_observability/examples.py for synthetic data)
```

## Limitations (honest scope)

In-memory storage does not survive restarts and does not scale past one
process; there is no auth, no streaming ingestion, and no dashboard UI.
Each is a documented next step in `docs/architecture.md`, not a hidden gap.
