from __future__ import annotations

import logging
import time
from pathlib import Path

from idea_enhancer.client import call, get_usage, reset_usage, set_model
from idea_enhancer.critique import run_critiques, synthesize
from idea_enhancer.decision import run_decision
from idea_enhancer.interview import context_block, run_interview
from idea_enhancer.models import Report
from idea_enhancer.prompts import TITLE_SYSTEM, title_user
from idea_enhancer.research import run_research
from idea_enhancer.storage import IDEAS_DIR, slugify, write_report

logger = logging.getLogger("idea_enhancer")


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


def _partial_save(report: Report, output_dir: Path, phase_failed: str) -> Path:
    """Best-effort save of partial results when the pipeline fails."""
    try:
        path = write_report(report, root=output_dir)
        logger.warning(
            "Pipeline failed at '%s' — partial report saved to %s", phase_failed, path
        )
        return path
    except Exception:
        logger.error("Could not save partial report for phase '%s'.", phase_failed)
        raise


def enhance(
    idea: str,
    *,
    interactive: bool = True,
    skip_interview: bool = False,
    output_dir: Path = IDEAS_DIR,
    model: str | None = None,
) -> Path:
    idea = idea.strip()
    if not idea:
        raise ValueError("Idea text is empty.")

    # Configure model if overridden.
    if model:
        set_model(model)

    # Reset usage counters for this run.
    reset_usage()

    t0 = time.monotonic()
    logger.info("generating title")
    title = generate_title(idea)
    slug = slugify(title)
    report = Report(idea=idea, title=title, slug=slug)
    logger.info("title: %r (slug: %s)", title, slug)

    try:
        if not skip_interview:
            logger.info("phase 1: generating clarifying questions")
            report.interview = run_interview(idea, interactive=interactive)
        context = context_block(report.interview)

        logger.info("phase 2: market + competitor research (web search, parallel)")
        market, competitors = run_research(idea, context)
        report.market = market
        report.competitors = competitors

        logger.info("phase 3: multi-persona critique (4 personas, parallel)")
        report.critiques = run_critiques(idea, context, market, competitors)

        logger.info("phase 3b: synthesis")
        report.synthesis = synthesize(report.critiques)

        logger.info("phase 4: decision artifact")
        report.decision = run_decision(idea, context, market, competitors, report.synthesis)
    except Exception:
        _partial_save(report, output_dir, "pipeline")
        raise

    path = write_report(report, root=output_dir)
    elapsed = time.monotonic() - t0
    usage = get_usage()
    logger.info("done in %.1fs -> %s", elapsed, path)
    logger.info("usage: %s", usage.summary())
    return path
