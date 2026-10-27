import pytest

from llm_observability.models import Span, SpanKind


def _span(**kw):
    base = dict(span_id="a", trace_id="t", parent_id=None, kind=SpanKind.MODEL,
                name="call", start_ms=0, end_ms=100)
    base.update(kw)
    return Span(**base)


def test_latency_and_tokens():
    s = _span(prompt_tokens=10, completion_tokens=5)
    assert s.latency_ms == 100 and s.total_tokens == 15 and s.is_root


@pytest.mark.parametrize("kw", [
    dict(end_ms=-1), dict(prompt_tokens=-1), dict(status="weird"),
    dict(feedback_score=1.5), dict(eval_score=-0.1),
])
def test_validation_rejects_bad_spans(kw):
    with pytest.raises(ValueError):
        _span(**kw)
