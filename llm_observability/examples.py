"""Synthetic demo data — invented traces, no real user or model data.

One healthy trace (prompt + model + tool), one errored trace, and one slow
trace, across two tenants, so the demo summary exercises every subsystem.
"""

from llm_observability.models import Span, SpanKind


def synthetic_traces() -> list[Span]:
    return [
        Span("s1", "t-healthy", None, SpanKind.PROMPT, "render-prompt", 0, 50,
             tenant_id="tenant-a", attributes={"template": "support-answer"}),
        Span("s2", "t-healthy", "s1", SpanKind.MODEL, "chat-completion", 50, 850,
             tenant_id="tenant-a", model="generic-small",
             prompt_tokens=1200, completion_tokens=300, feedback_score=0.9, eval_score=0.85),
        Span("s3", "t-healthy", "s2", SpanKind.TOOL, "lookup-order", 200, 400,
             tenant_id="tenant-a"),
        Span("s4", "t-error", None, SpanKind.PROMPT, "render-prompt", 0, 40,
             tenant_id="tenant-b"),
        Span("s5", "t-error", "s4", SpanKind.MODEL, "chat-completion", 40, 140,
             tenant_id="tenant-b", model="generic-large", prompt_tokens=500,
             completion_tokens=0, status="error", error_type="timeout"),
        Span("s6", "t-slow", None, SpanKind.PROMPT, "render-prompt", 0, 60,
             tenant_id="tenant-a"),
        Span("s7", "t-slow", "s6", SpanKind.MODEL, "chat-completion", 60, 3060,
             tenant_id="tenant-a", model="generic-large",
             prompt_tokens=2000, completion_tokens=800, feedback_score=0.6),
    ]
