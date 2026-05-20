from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import anthropic

logger = logging.getLogger("idea_enhancer")

DEFAULT_MODEL = "claude-opus-4-7"

# Cost per million tokens (approximate, as of 2025 pricing)
_MODEL_COSTS: dict[str, dict[str, float]] = {
    "claude-opus-4-7": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-3-5-20241022": {"input": 0.80, "output": 4.0},
}

WEB_SEARCH_TOOL: dict[str, Any] = {
    "type": "web_search_20260209",
    "name": "web_search",
}

# ── Token / cost tracking ──────────────────────────────────────────


@dataclass
class UsageStats:
    """Accumulates token usage and estimated cost across calls."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_cache_creation_tokens: int = 0
    call_count: int = 0
    model_costs: dict[str, dict[str, int]] = field(default_factory=dict)

    def record(self, message: Any, model: str) -> None:
        usage = getattr(message, "usage", None)
        if usage is None:
            return
        self.total_input_tokens += getattr(usage, "input_tokens", 0)
        self.total_output_tokens += getattr(usage, "output_tokens", 0)
        self.total_cache_read_tokens += getattr(usage, "cache_read_input_tokens", 0)
        self.total_cache_creation_tokens += getattr(
            usage, "cache_creation_input_tokens", 0
        )
        self.call_count += 1

        if model not in self.model_costs:
            self.model_costs[model] = {"input": 0, "output": 0}
        self.model_costs[model]["input"] += getattr(usage, "input_tokens", 0)
        self.model_costs[model]["output"] += getattr(usage, "output_tokens", 0)

    @property
    def estimated_cost_usd(self) -> float:
        total = 0.0
        for model, tokens in self.model_costs.items():
            rates = _MODEL_COSTS.get(model, {"input": 0, "output": 0})
            total += (tokens["input"] / 1_000_000) * rates["input"]
            total += (tokens["output"] / 1_000_000) * rates["output"]
        return total

    def summary(self) -> str:
        return (
            f"API calls: {self.call_count}, "
            f"input: {self.total_input_tokens:,}, "
            f"output: {self.total_output_tokens:,}, "
            f"cache_read: {self.total_cache_read_tokens:,}, "
            f"cache_creation: {self.total_cache_creation_tokens:,}, "
            f"estimated cost: ${self.estimated_cost_usd:.2f}"
        )


# Module-level accumulator — reset per pipeline run via reset_usage().
_usage = UsageStats()


def reset_usage() -> None:
    global _usage
    _usage = UsageStats()


def get_usage() -> UsageStats:
    return _usage


# ── Client ──────────────────────────────────────────────────────────

# Configurable model override (set via CLI --model or env var).
_active_model: str | None = None


def set_model(model: str) -> None:
    global _active_model
    _active_model = model


def get_model() -> str:
    return _active_model or os.environ.get("IDEA_ENHANCER_MODEL", DEFAULT_MODEL)


@lru_cache(maxsize=1)
def get_client() -> anthropic.Anthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Export it or copy .env.example to .env and source it."
        )
    return anthropic.Anthropic()


def extract_text(content: list[Any]) -> str:
    parts: list[str] = []
    for block in content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "\n".join(parts).strip()


# ── Retry helper ────────────────────────────────────────────────────

_MAX_RETRIES = 3
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_BASE_DELAY = 2.0  # seconds


def _should_retry(exc: Exception) -> bool:
    if isinstance(exc, anthropic.RateLimitError):
        return True
    if isinstance(exc, anthropic.APIStatusError) and hasattr(exc, "status_code"):
        return exc.status_code in _RETRYABLE_STATUS_CODES
    if isinstance(exc, (anthropic.APIConnectionError, anthropic.APITimeoutError)):
        return True
    return False


# ── Core call ───────────────────────────────────────────────────────


def call(
    *,
    system: str,
    user: str,
    max_tokens: int = 16000,
    effort: str = "high",
    thinking: bool = True,
    cache_system: bool = True,
    model: str | None = None,
    timeout: float = 300.0,
) -> str:
    """Single-shot Claude call with retry and cost tracking.

    Streams to avoid timeouts on long outputs.  The system prompt is
    cached when reused, so repeated personas / passes only pay full
    price once per 5-minute window.
    """
    model = model or get_model()
    client = get_client()
    system_param: Any
    if cache_system:
        system_param = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    else:
        system_param = system

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_param,
        "messages": [{"role": "user", "content": user}],
        "output_config": {"effort": effort},
        "timeout": timeout,
    }
    if thinking:
        kwargs["thinking"] = {"type": "adaptive"}

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            with client.messages.stream(**kwargs) as stream:
                message = stream.get_final_message()
            _usage.record(message, model)
            return extract_text(message.content)
        except Exception as exc:
            last_exc = exc
            if _should_retry(exc):
                delay = _BASE_DELAY * (2**attempt)
                logger.warning(
                    "API call failed (attempt %d/%d): %s — retrying in %.1fs",
                    attempt + 1,
                    _MAX_RETRIES,
                    exc,
                    delay,
                )
                time.sleep(delay)
            else:
                raise

    # All retries exhausted
    raise last_exc  # type: ignore[misc]


# ── Call with web search ────────────────────────────────────────────


def call_with_web_search(
    *,
    system: str,
    user: str,
    max_tokens: int = 16000,
    effort: str = "high",
    max_iterations: int = 5,
    model: str | None = None,
    timeout: float = 300.0,
) -> str:
    """Call with the server-side web_search tool. Handles ``pause_turn``
    if the server-side loop hits its iteration cap.  Includes retry
    logic for transient failures.
    """
    model = model or get_model()
    client = get_client()
    messages: list[dict[str, Any]] = [{"role": "user", "content": user}]
    response: Any = None

    for _ in range(max_iterations):
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                with client.messages.stream(
                    model=model,
                    max_tokens=max_tokens,
                    thinking={"type": "adaptive"},
                    output_config={"effort": effort},
                    system=[
                        {
                            "type": "text",
                            "text": system,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    tools=[WEB_SEARCH_TOOL],
                    messages=messages,
                    timeout=timeout,
                ) as stream:
                    response = stream.get_final_message()
                break  # success — exit retry loop
            except Exception as exc:
                last_exc = exc
                if _should_retry(exc):
                    delay = _BASE_DELAY * (2**attempt)
                    logger.warning(
                        "Web-search call failed (attempt %d/%d): %s — retrying in %.1fs",
                        attempt + 1,
                        _MAX_RETRIES,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    raise
        else:
            # All retries exhausted for this iteration
            raise last_exc  # type: ignore[misc]

        if response is not None:
            _usage.record(response, model)

        if response is not None and response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continue
        break

    # A4 fix: guard against response still being None
    if response is None:
        return "(no response received from API)"
    return extract_text(response.content)
