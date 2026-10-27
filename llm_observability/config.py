"""Configuration: model price table and retention defaults.

Prices are per 1,000 tokens, in USD, and are *illustrative defaults* for the
synthetic demo data — operators override them from environment variables or
their own price feed. Format for the env override::

    LLM_OBS_PRICES='{"model-a": {"prompt": 0.001, "completion": 0.002}}'
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelPrice:
    prompt_per_1k: float
    completion_per_1k: float


DEFAULT_PRICES: dict[str, ModelPrice] = {
    "generic-small": ModelPrice(prompt_per_1k=0.0005, completion_per_1k=0.0015),
    "generic-large": ModelPrice(prompt_per_1k=0.003, completion_per_1k=0.015),
    "generic-embedding": ModelPrice(prompt_per_1k=0.0001, completion_per_1k=0.0),
}


@dataclass(frozen=True)
class Settings:
    prices: dict[str, ModelPrice] = field(default_factory=lambda: dict(DEFAULT_PRICES))
    default_sample_rate: float = 1.0  # keep fraction of traces, [0, 1]
    error_sample_rate: float = 1.0  # error traces are always interesting
    retention_days: int = 30

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        prices = dict(DEFAULT_PRICES)
        raw = env.get("LLM_OBS_PRICES")
        if raw:
            for name, vals in json.loads(raw).items():
                prices[name] = ModelPrice(
                    prompt_per_1k=float(vals["prompt"]),
                    completion_per_1k=float(vals["completion"]),
                )
        return cls(
            prices=prices,
            default_sample_rate=float(env.get("LLM_OBS_SAMPLE_RATE", "1.0")),
            error_sample_rate=float(env.get("LLM_OBS_ERROR_SAMPLE_RATE", "1.0")),
            retention_days=int(env.get("LLM_OBS_RETENTION_DAYS", "30")),
        )
