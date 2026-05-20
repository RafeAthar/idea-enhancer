from __future__ import annotations

import logging
import re

from idea_enhancer.client import call
from idea_enhancer.models import DecisionArtifact, Scores
from idea_enhancer.prompts import DECISION_SYSTEM, decision_user

logger = logging.getLogger("idea_enhancer")

SCORE_LINE_RE = re.compile(r"^-\s*([A-Za-z][A-Za-z\s\-/]*?):\s*(\d{1,2})", re.MULTILINE)
RECOMMENDATION_RE = re.compile(
    r"Recommendation:\s*(kill|explore|build)\s*[\.\-:]?\s*(.*)",
    re.IGNORECASE,
)

# Mapping from normalized label → Scores field and human-readable name.
_SCORE_FIELDS: dict[str, tuple[str, str]] = {
    "tam": ("tam", "TAM"),
    "competitive density": ("competitive_density", "Competitive density"),
    "moat": ("moat", "Moat"),
    "founder-fit": ("founder_fit", "Founder-fit"),
    "founder fit": ("founder_fit", "Founder-fit"),
    "why-now timing": ("why_now", "Why-now timing"),
    "why-now": ("why_now", "Why-now timing"),
    "capital efficiency": ("capital_efficiency", "Capital efficiency"),
}


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

    # Build Scores with explicit per-field lookup + warning for defaults.
    field_values: dict[str, int] = {}
    for label, (field_name, display_name) in _SCORE_FIELDS.items():
        if label in found:
            field_values[field_name] = found[label]

    # Warn about any dimension that wasn't parsed (will use default 5).
    parsed_fields = set(field_values.keys())
    all_fields = {v[0] for v in _SCORE_FIELDS.values()}
    missing = all_fields - parsed_fields
    if missing:
        missing_names = sorted(
            {v[1] for v in _SCORE_FIELDS.values() if v[0] in missing}
        )
        logger.warning(
            "Decision parser: could not parse scores for %s — defaulting to 5/10. "
            "LLM output may have deviated from expected format.",
            ", ".join(missing_names),
        )

    return Scores(
        tam=field_values.get("tam", 5),
        competitive_density=field_values.get("competitive_density", 5),
        moat=field_values.get("moat", 5),
        founder_fit=field_values.get("founder_fit", 5),
        why_now=field_values.get("why_now", 5),
        capital_efficiency=field_values.get("capital_efficiency", 5),
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
