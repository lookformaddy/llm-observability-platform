import pytest

fastapi = pytest.importorskip("fastapi", reason="FastAPI not installed; core tests still run")
from fastapi.testclient import TestClient

from llm_observability.examples import synthetic_traces
from llm_observability.ingestion import TraceStore
from llm_observability.service import create_app


def _client():
    store = TraceStore()
    store.ingest(synthetic_traces())
    return TestClient(create_app(store))


def test_ingest_and_get_trace():
    client = _client()
    resp = client.post("/spans", json=[{
        "span_id": "n1", "trace_id": "t-new", "kind": "model", "name": "call",
        "start_ms": 0, "end_ms": 50, "model": "generic-small",
        "prompt_tokens": 100, "completion_tokens": 50}])
    assert resp.status_code == 202 and resp.json()["ingested_new"] == 1
    got = client.get("/traces/t-new")
    assert got.status_code == 200 and got.json()["total_tokens"] == 150
    assert client.get("/traces/nope").status_code == 404


def test_summary_endpoint():
    client = _client()
    data = client.get("/summary").json()
    assert data["trace_count"] == 3 and data["error_count"] == 1
    assert client.get("/summary", params={"tenant_id": "tenant-b"}).json()["trace_count"] == 1
