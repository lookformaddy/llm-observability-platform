import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from llm_observability.examples import synthetic_traces
from llm_observability.ingestion import TraceStore


@pytest.fixture()
def store():
    s = TraceStore()
    s.ingest(synthetic_traces())
    return s


@pytest.fixture()
def traces(store):
    return store.all_traces()
