from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from idea_enhancer.client import call_with_web_search
from idea_enhancer.prompts import (
    COMPETITOR_SYSTEM,
    MARKET_SYSTEM,
    competitor_user,
    market_user,
)


def market_scan(idea: str, context: str) -> str:
    return call_with_web_search(
        system=MARKET_SYSTEM,
        user=market_user(idea, context),
    )


def competitor_scan(idea: str, context: str) -> str:
    return call_with_web_search(
        system=COMPETITOR_SYSTEM,
        user=competitor_user(idea, context),
    )


def run_research(idea: str, context: str) -> tuple[str, str]:
    """Run market + competitor scans in parallel."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        market_fut = pool.submit(market_scan, idea, context)
        comp_fut = pool.submit(competitor_scan, idea, context)
        return market_fut.result(), comp_fut.result()
