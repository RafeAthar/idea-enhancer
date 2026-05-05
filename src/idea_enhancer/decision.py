from __future__ import annotations

import re

from idea_enhancer.client import call
from idea_enhancer.models import DecisionArtifact, Scores
from idea_enhancer.prompts import DECISION_SYSTEM, decision_user

SCORE_LINE_RE = re.compile(r"^-\s*([A-Za-z][A-Za-z\s\-/]*?):\s*(\d{1,2})", re.MULTILINE)
RECOMMENDATION_RE = re.compile(
    r"Recommendation:\s*(kill|explore|build)\s*[\.\-:]?\s*(.*)",
    re.IGNORECASE,
)


def _section(text: str, header: str) -> str:
    pattern = re.compile(
        rf"^###\s*{re.escape(header)}\s*\n(.*?)(?=^###\s|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    m = pattern.search(text)
    return m.group(1).strip() if m else ""


def _parse_scores(scores_block: str) -> Scores:
    found: dict[str, int] = {}
    for m in SCORE_LINE_RE.finditer(scores_block):
        label = m.group(1).strip().lower()
        try:
            val = max(1, min(10, int(m.group(2))))
        except ValueError:
            continue
        found[label] = val
    return Scores(
        tam=found.get("tam", 5),
        competitive_density=found.get("competitive density", 5),
        moat=found.get("moat", 5),
        founder_fit=found.get("founder-fit", found.get("founder fit", 5)),
        why_now=found.get("why-now timing", found.get("why-now", 5)),
        capital_efficiency=found.get("capital efficiency", 5),
    )


def _parse_kill_criteria(block: str) -> list[str]:
    out: list[str] = []
    for line in block.splitlines():
        s = line.strip()
        if s.startswith(("-", "*", "•")):
            out.append(s[1:].strip())
    return out[:5]


def _parse_recommendation(block: str) -> tuple[str, str]:
    m = RECOMMENDATION_RE.search(block)
    if not m:
        return "explore", block.strip()
    return m.group(1).lower(), m.group(2).strip().lstrip("—-:.").strip()


def parse_decision(text: str) -> DecisionArtifact:
    scores_block = _section(text, "Scores (1-10, integer)") or _section(text, "Scores")
    kill_block = _section(text, "Kill criteria")
    exp_block = _section(text, "Cheapest validation experiment")
    rec_block = _section(text, "Recommendation")

    scores = _parse_scores(scores_block)
    kill = _parse_kill_criteria(kill_block)
    rec, rationale = _parse_recommendation(rec_block)

    return DecisionArtifact(
        scores=scores,
        kill_criteria=kill or ["(no kill criteria parsed — see raw output)"],
        validation_experiment=exp_block or "(no experiment parsed — see raw output)",
        recommendation=rec,
        rationale=rationale,
    )


def run_decision(
    idea: str, context: str, market: str, competitors: str, synthesis: str
) -> DecisionArtifact:
    raw = call(
        system=DECISION_SYSTEM,
        user=decision_user(idea, context, market, competitors, synthesis),
        max_tokens=2500,
        effort="high",
    )
    return parse_decision(raw)
