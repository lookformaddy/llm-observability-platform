from llm_observability.retention import prune_older_than, sample, should_keep
from llm_observability.search import TraceFilter, search


def test_search_filters(traces):
    assert len(search(traces, TraceFilter(tenant_id="tenant-b"))) == 1
    assert len(search(traces, TraceFilter(errored_only=True))) == 1
    assert len(search(traces, TraceFilter(model="generic-small"))) == 1
    assert len(search(traces, TraceFilter(min_latency_ms=1000))) == 1
    assert len(search(traces, TraceFilter(text="lookup"))) == 1
    assert len(search(traces, TraceFilter(min_feedback=0.8))) == 1
    assert search(traces, TraceFilter(tenant_id="nobody")) == []


def test_sampling_is_deterministic_and_keeps_errors(traces):
    first = sample(traces, 0.5)
    assert sample(traces, 0.5) == first  # same decision on replay
    errored = next(t for t in traces if t.errored)
    assert should_keep(errored, 0.0, error_rate=1.0) is True
    assert should_keep(errored, 0.0, error_rate=0.0) is False
    assert sample(traces, 1.0) == traces and sample(traces, 0.0, error_rate=0.0) == []


def test_prune_by_age(traces):
    kept, pruned = prune_older_than(traces, cutoff_ms=1000)
    # newest ends: healthy 850, error 140, slow 3060 -> only slow survives
    assert [t.trace_id for t in kept] == ["t-slow"]
    assert len(pruned) == 2
