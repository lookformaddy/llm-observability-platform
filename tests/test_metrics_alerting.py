from llm_observability.alerting import Rule, evaluate_all
from llm_observability.metrics import group_latencies, percentile, summarize


def test_percentile_nearest_rank():
    assert percentile([10, 20, 30, 40], 50) == 20
    assert percentile([10, 20, 30, 40], 100) == 40
    assert percentile([], 50) is None
    assert percentile([1], 0) is None


def test_summary(traces):
    s = summarize(traces)
    assert s.trace_count == 3 and s.error_count == 1
    assert s.error_rate == 1 / 3
    assert s.p50_ms == 850 and s.p95_ms == 3060
    assert s.avg_feedback == (0.9 + 0.6) / 2
    assert s.avg_eval == 0.85


def test_group_latencies(traces):
    groups = group_latencies(traces)
    assert sorted(groups["tenant-a"]) == [850, 3060]
    assert groups["tenant-b"] == [140]


def test_alerts_fire_and_respect_min_count(traces):
    rules = [Rule("p95", max_p95_ms=1000), Rule("errors", max_error_rate=0.1),
             Rule("feedback", min_avg_feedback=0.8), Rule("quiet", max_p95_ms=1, min_trace_count=99)]
    fired = {a.rule_name for a in evaluate_all(rules, traces)}
    assert fired == {"p95", "errors", "feedback"}
    assert Rule("p95", max_p95_ms=99999).evaluate(traces) is None
    assert summarize([]).error_rate == 0.0
