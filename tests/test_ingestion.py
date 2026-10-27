from llm_observability.examples import synthetic_traces
from llm_observability.ingestion import TraceStore


def test_ingest_dedupes_and_assembles_traces(store):
    assert store.trace_count() == 3
    assert store.span_count() == 7
    # Re-ingesting the same spans adds nothing.
    assert store.ingest(synthetic_traces()) == 0
    trace = store.get_trace("t-healthy")
    assert trace is not None
    assert trace.root.span_id == "s1"
    assert trace.latency_ms == 850
    assert [c.span_id for c in trace.children_of("s2")] == ["s3"]
    assert store.get_trace("missing") is None


def test_drop_trace():
    store = TraceStore()
    store.ingest(synthetic_traces())
    assert store.drop_trace("t-error") is True
    assert store.drop_trace("t-error") is False
    assert store.trace_count() == 2
