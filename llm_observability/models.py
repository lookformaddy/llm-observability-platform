"""Core domain models.

A *trace* is one end-to-end request through an LLM-powered application.
A *span* is one timed unit of work inside a trace: a prompt render, a model
call, a tool call, or a retrieval step. Spans form a tree via ``parent_id``.

All timestamps are epoch milliseconds (int) so arithmetic stays exact and
deterministic; wall-clock conversion happens only at the API boundary.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class SpanKind(str, enum.Enum):
    PROMPT = "prompt"
    MODEL = "model"
    TOOL = "tool"
    RETRIEVAL = "retrieval"
    OTHER = "other"


@dataclass(frozen=True)
class Span:
    """One timed operation inside a trace. Immutable: ingestion never mutates."""

    span_id: str
    trace_id: str
    parent_id: str | None
    kind: SpanKind
    name: str
    start_ms: int
    end_ms: int
    tenant_id: str = "default"
    model: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    status: str = "ok"  # "ok" | "error"
    error_type: str | None = None
    feedback_score: float | None = None  # user feedback, 0.0-1.0, root span only
    eval_score: float | None = None  # offline eval score, 0.0-1.0
    attributes: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.end_ms < self.start_ms:
            raise ValueError(f"span {self.span_id}: end_ms < start_ms")
        for tok, label in ((self.prompt_tokens, "prompt_tokens"),
                           (self.completion_tokens, "completion_tokens")):
            if tok < 0:
                raise ValueError(f"span {self.span_id}: {label} must be >= 0")
        if self.status not in ("ok", "error"):
            raise ValueError(f"span {self.span_id}: unknown status {self.status!r}")
        for score, label in ((self.feedback_score, "feedback_score"),
                             (self.eval_score, "eval_score")):
            if score is not None and not 0.0 <= score <= 1.0:
                raise ValueError(f"span {self.span_id}: {label} must be in [0, 1]")

    @property
    def latency_ms(self) -> int:
        return self.end_ms - self.start_ms

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def is_root(self) -> bool:
        return self.parent_id is None


@dataclass
class Trace:
    """A complete trace: root span plus its descendants, derived on ingest."""

    trace_id: str
    spans: list[Span]
    tenant_id: str

    @property
    def root(self) -> Span | None:
        for span in self.spans:
            if span.is_root:
                return span
        return None

    @property
    def latency_ms(self) -> int:
        # End-to-end latency is the full span envelope, NOT the root span's
        # own duration: the root (e.g. a prompt render) typically ends long
        # before its model/tool descendants finish.
        if not self.spans:
            return 0
        return max(s.end_ms for s in self.spans) - min(s.start_ms for s in self.spans)

    @property
    def errored(self) -> bool:
        return any(s.status == "error" for s in self.spans)

    @property
    def model_spans(self) -> list[Span]:
        return [s for s in self.spans if s.kind == SpanKind.MODEL]

    @property
    def total_tokens(self) -> int:
        return sum(s.total_tokens for s in self.model_spans)

    def children_of(self, span_id: str) -> list[Span]:
        return [s for s in self.spans if s.parent_id == span_id]
