from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from pathlib import Path

from idea_enhancer import __version__


def _load_dotenv() -> None:
    """Load ``.env`` into ``os.environ``.  Handles quoted values and
    inline comments.  Skips blank lines and ``#`` comments.
    """
    env_path = Path(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip()
        # Strip inline comments (but not inside quotes).
        # Match: value  # comment
        m = re.match(r"""^(["'])(.*)\1\s*(?:#.*)?$|^(.+?)(?:\s+#.*)?$""", v)
        if m:
            if m.group(1):  # quoted value
                v = m.group(2)
            else:  # unquoted value
                v = m.group(3).strip()
        os.environ.setdefault(k, v)


def _setup_logging(verbose: bool, quiet: bool) -> None:
    """Configure the ``idea_enhancer`` logger."""
    level = logging.WARNING
    if verbose:
        level = logging.DEBUG
    elif not quiet:
        level = logging.INFO

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("[%(name)s] %(levelname)s: %(message)s")
    )
    logger = logging.getLogger("idea_enhancer")
    logger.setLevel(level)
    logger.addHandler(handler)


def _read_idea(args: argparse.Namespace) -> str:
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if args.idea:
        return " ".join(args.idea)
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("Provide an idea as an argument, with --file, or pipe via stdin.")


def cmd_run(args: argparse.Namespace) -> int:
    from idea_enhancer.pipeline import enhance

    idea = _read_idea(args)
    path = enhance(
        idea,
        interactive=not args.non_interactive,
        skip_interview=args.skip_interview,
        output_dir=Path(args.output_dir) if args.output_dir else None,
        model=args.model,
    )
    print(path)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    from idea_enhancer.corpus import cmd_list as do_list
    from idea_enhancer.storage import IDEAS_DIR

    root = Path(args.output_dir) if args.output_dir else IDEAS_DIR
    return do_list(root)


def cmd_show(args: argparse.Namespace) -> int:
    from idea_enhancer.corpus import cmd_show as do_show
    from idea_enhancer.storage import IDEAS_DIR

    root = Path(args.output_dir) if args.output_dir else IDEAS_DIR
    return do_show(args.slug, root)


def cmd_search(args: argparse.Namespace) -> int:
    from idea_enhancer.corpus import cmd_search as do_search
    from idea_enhancer.storage import IDEAS_DIR

    root = Path(args.output_dir) if args.output_dir else IDEAS_DIR
    return do_search(" ".join(args.query), root)


def cmd_leaderboard(args: argparse.Namespace) -> int:
    from idea_enhancer.corpus import cmd_leaderboard as do_leaderboard
    from idea_enhancer.storage import IDEAS_DIR

    root = Path(args.output_dir) if args.output_dir else IDEAS_DIR
    return do_leaderboard(root)


def cmd_compare(args: argparse.Namespace) -> int:
    from idea_enhancer.corpus import cmd_compare as do_compare
    from idea_enhancer.storage import IDEAS_DIR

    root = Path(args.output_dir) if args.output_dir else IDEAS_DIR
    return do_compare(args.slug_a, args.slug_b, root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="enhance",
        description="Turn raw ideas into decision-grade reports.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    # Global flags
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable debug-level logging.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress all non-error output.",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    # ── run ─────────────────────────────────────────────────────────
    run = sub.add_parser("run", help="Run the full pipeline on an idea.")
    run.add_argument("idea", nargs="*", help="Idea text (positional). Optional if --file or stdin.")
    run.add_argument("--file", help="Read idea text from a file.")
    run.add_argument("--skip-interview", action="store_true", help="Skip Phase 1 entirely.")
    run.add_argument(
        "--non-interactive",
        action="store_true",
        help="Generate questions but don't prompt for answers.",
    )
    run.add_argument(
        "--model",
        help="Override the LLM model (e.g. claude-sonnet-4-20250514). "
        "Defaults to claude-opus-4-7 or IDEA_ENHANCER_MODEL env var.",
    )
    run.add_argument(
        "--output-dir",
        help="Directory for report output. Defaults to ideas/ in the project root.",
    )
    run.set_defaults(func=cmd_run)

    # ── list ────────────────────────────────────────────────────────
    ls = sub.add_parser("list", help="List all reports.")
    ls.add_argument("--output-dir", help="Reports directory.")
    ls.set_defaults(func=cmd_list)

    # ── show ────────────────────────────────────────────────────────
    show = sub.add_parser("show", help="Print a report by slug (prefix match OK).")
    show.add_argument("slug")
    show.add_argument("--output-dir", help="Reports directory.")
    show.set_defaults(func=cmd_show)

    # ── search ──────────────────────────────────────────────────────
    search = sub.add_parser("search", help="TF-IDF similarity search across reports.")
    search.add_argument("query", nargs="+")
    search.add_argument("--output-dir", help="Reports directory.")
    search.set_defaults(func=cmd_search)

    # ── leaderboard ─────────────────────────────────────────────────
    lb = sub.add_parser("leaderboard", help="Rank reports by score.")
    lb.add_argument("--output-dir", help="Reports directory.")
    lb.set_defaults(func=cmd_leaderboard)

    # ── compare ─────────────────────────────────────────────────────
    cmp = sub.add_parser("compare", help="LLM head-to-head between two reports.")
    cmp.add_argument("slug_a")
    cmp.add_argument("slug_b")
    cmp.add_argument("--output-dir", help="Reports directory.")
    cmp.set_defaults(func=cmd_compare)

    return parser


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    _setup_logging(getattr(args, "verbose", False), getattr(args, "quiet", False))

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
