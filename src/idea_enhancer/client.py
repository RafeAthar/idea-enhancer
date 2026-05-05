from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import anthropic

MODEL = "claude-opus-4-7"

WEB_SEARCH_TOOL: dict[str, Any] = {
    "type": "web_search_20260209",
    "name": "web_search",
}


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


def call(
    *,
    system: str,
    user: str,
    max_tokens: int = 16000,
    effort: str = "high",
    thinking: bool = True,
    cache_system: bool = True,
) -> str:
    """Single-shot Claude call. Streams to avoid timeouts on long outputs.

    The system prompt is cached when reused, so repeated personas / passes
    only pay full price once per 5-minute window.
    """
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
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system_param,
        "messages": [{"role": "user", "content": user}],
        "output_config": {"effort": effort},
    }
    if thinking:
        kwargs["thinking"] = {"type": "adaptive"}

    with client.messages.stream(**kwargs) as stream:
        message = stream.get_final_message()
    return extract_text(message.content)


def call_with_web_search(
    *,
    system: str,
    user: str,
    max_tokens: int = 16000,
    effort: str = "high",
    max_iterations: int = 5,
) -> str:
    """Call with the server-side web_search tool. Handles `pause_turn` if the
    server-side loop hits its iteration cap.
    """
    client = get_client()
    messages: list[dict[str, Any]] = [{"role": "user", "content": user}]

    for _ in range(max_iterations):
        with client.messages.stream(
            model=MODEL,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            output_config={"effort": effort},
            system=[
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ],
            tools=[WEB_SEARCH_TOOL],
            messages=messages,
        ) as stream:
            response = stream.get_final_message()

        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continue
        return extract_text(response.content)

    return extract_text(response.content)
