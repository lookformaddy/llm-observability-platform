"""SLO alerting rules.

A rule is a pure function over a trace window: it either fires (with a
human-readable message) or it does not. Rules are deliberately stateless —
stateful alert deduplication and paging live in the notification layer, not
in SLO evaluation, so rules stay unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass

from llm_observability.metrics import percentile, summarize
from llm_observability.models import Trace


@dataclass(frozen=True)
class Alert:
    rule_name: str
    severity: str  # "warning" | "critical"
    message: str


@dataclass(frozen=True)
class Rule:
    name: str
    severity: str = "warning"
    max_p95_ms: float | None = None
    max_error_rate: float | None = None
    min_avg_feedback: float | None = None
    min_trace_count: int = 1  # don't fire on statistically meaningless windows

    def evaluate(self, traces: list[Trace]) -> Alert | None:
        if len(traces) < self.min_trace_count:
            return None
        summary = summarize(traces)
        if self.max_p95_ms is not None and summary.p95_ms is not None \
                and summary.p95_ms > self.max_p95_ms:
            return Alert(self.name, self.severity,
                         f"p95 latency {summary.p95_ms:.0f}ms exceeds "
                         f"SLO {self.max_p95_ms:.0f}ms over {len(traces)} traces")
        if self.max_error_rate is not None and summary.error_rate > self.max_error_rate:
            return Alert(self.name, self.severity,
                         f"error rate {summary.error_rate:.1%} exceeds "
                         f"SLO {self.max_error_rate:.1%} over {len(traces)} traces")
        if self.min_avg_feedback is not None and summary.avg_feedback is not None \
                and summary.avg_feedback < self.min_avg_feedback:
            return Alert(self.name, self.severity,
                         f"avg feedback {summary.avg_feedback:.2f} below "
                         f"SLO {self.min_avg_feedback:.2f} over {len(traces)} traces")
        return None


def evaluate_all(rules: list[Rule], traces: list[Trace]) -> list[Alert]:
    return [a for rule in rules if (a := rule.evaluate(traces)) is not None]
