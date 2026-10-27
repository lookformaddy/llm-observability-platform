"""LLM observability platform: trace ingestion, cost/latency accounting,
quality signals, alerting, search, and retention for production LLM apps.

Pure standard library. The optional FastAPI service lives in
``llm_observability.service`` and degrades gracefully when FastAPI is absent.
"""

from llm_observability.models import Span, SpanKind, Trace

__all__ = ["Span", "SpanKind", "Trace"]
__version__ = "0.1.0"
