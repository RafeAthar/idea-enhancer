from __future__ import annotations

import sys
import time
from pathlib import Path

from idea_enhancer.client import call
from idea_enhancer.critique import run_critiques, synthesize
from idea_enhancer.decision import run_decision
from idea_enhancer.interview import context_block, run_interview
from idea_enhancer.models import Report
from idea_enhancer.prompts import TITLE_SYSTEM, title_user
from idea_enhancer.research import run_research
from idea_enhancer.storage import IDEAS_DIR, slugify, write_report


def log(msg: str) -> None:
    print(f"[idea-enhancer] {msg}", file=sys.stderr, flush=True)


def generate_title(idea: str) -> str:
    text = call(
        system=TITLE_SYSTEM,
        user=title_user(idea),
        max_tokens=100,
        effort="low",
        thinking=False,
    ).strip()
    first = text.splitlines()[0] if text else "Untitled idea"
    return first.strip().strip('"').strip("'") or "Untitled idea"


def enhance(
    idea: str,
    *,
    interactive: bool = True,
    skip_interview: bool = False,
    output_dir: Path = IDEAS_DIR,
) -> Path:
    idea = idea.strip()
    if not idea:
        raise ValueError("Idea text is empty.")

    t0 = time.monotonic()
    log("generating title")
    title = generate_title(idea)
    slug = slugify(title)
    report = Report(idea=idea, title=title, slug=slug)
    log(f"title: {title!r} (slug: {slug})")

    if not skip_interview:
        log("phase 1: generating clarifying questions")
        report.interview = run_interview(idea, interactive=interactive)
    context = context_block(report.interview)

    log("phase 2: market + competitor research (web search, parallel)")
    market, competitors = run_research(idea, context)
    report.market = market
    report.competitors = competitors

    log("phase 3: multi-persona critique (4 personas, parallel)")
    report.critiques = run_critiques(idea, context, market, competitors)

    log("phase 3b: synthesis")
    report.synthesis = synthesize(report.critiques)

    log("phase 4: decision artifact")
    report.decision = run_decision(idea, context, market, competitors, report.synthesis)

    path = write_report(report, root=output_dir)
    elapsed = time.monotonic() - t0
    log(f"done in {elapsed:.1f}s -> {path}")
    return path
