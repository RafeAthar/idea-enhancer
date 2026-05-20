from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from idea_enhancer.client import call
from idea_enhancer.models import PersonaCritique
from idea_enhancer.prompts import (
    PERSONAS,
    SYNTHESIS_SYSTEM,
    persona_user,
    synthesis_user,
)


def _run_persona(
    persona: tuple[str, str], idea: str, context: str, market: str, competitors: str
) -> PersonaCritique:
    name, system = persona
    text = call(
        system=system,
        user=persona_user(idea, context, market, competitors),
        max_tokens=4000,
        effort="high",
    )
    return PersonaCritique(name=name, text=text)


def run_critiques(
    idea: str, context: str, market: str, competitors: str
) -> list[PersonaCritique]:
    """Run all four personas in parallel."""
    with ThreadPoolExecutor(max_workers=len(PERSONAS)) as pool:
        futures = [
            pool.submit(_run_persona, (name, system), idea, context, market, competitors)
            for name, system in PERSONAS
        ]
        return [f.result() for f in futures]


def synthesize(critiques: list[PersonaCritique]) -> str:
    blob = "\n\n".join(f"### {c.name}\n\n{c.text}" for c in critiques)
    return call(
        system=SYNTHESIS_SYSTEM,
        user=synthesis_user(blob),
        max_tokens=3000,
        effort="high",
    )
