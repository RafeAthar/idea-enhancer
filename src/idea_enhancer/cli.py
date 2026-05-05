from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return
    import os
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


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
    )
    print(path)
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    from idea_enhancer.corpus import cmd_list as do_list
    return do_list()


def cmd_show(args: argparse.Namespace) -> int:
    from idea_enhancer.corpus import cmd_show as do_show
    return do_show(args.slug)


def cmd_search(args: argparse.Namespace) -> int:
    from idea_enhancer.corpus import cmd_search as do_search
    return do_search(" ".join(args.query))


def cmd_leaderboard(_: argparse.Namespace) -> int:
    from idea_enhancer.corpus import cmd_leaderboard as do_leaderboard
    return do_leaderboard()


def cmd_compare(args: argparse.Namespace) -> int:
    from idea_enhancer.corpus import cmd_compare as do_compare
    return do_compare(args.slug_a, args.slug_b)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="enhance",
        description="Turn raw ideas into decision-grade reports.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Run the full pipeline on an idea.")
    run.add_argument("idea", nargs="*", help="Idea text (positional). Optional if --file or stdin.")
    run.add_argument("--file", help="Read idea text from a file.")
    run.add_argument("--skip-interview", action="store_true", help="Skip Phase 1 entirely.")
    run.add_argument(
        "--non-interactive",
        action="store_true",
        help="Generate questions but don't prompt for answers.",
    )
    run.set_defaults(func=cmd_run)

    ls = sub.add_parser("list", help="List all reports.")
    ls.set_defaults(func=cmd_list)

    show = sub.add_parser("show", help="Print a report by slug (prefix match OK).")
    show.add_argument("slug")
    show.set_defaults(func=cmd_show)

    search = sub.add_parser("search", help="TF-IDF similarity search across reports.")
    search.add_argument("query", nargs="+")
    search.set_defaults(func=cmd_search)

    lb = sub.add_parser("leaderboard", help="Rank reports by score.")
    lb.set_defaults(func=cmd_leaderboard)

    cmp = sub.add_parser("compare", help="LLM head-to-head between two reports.")
    cmp.add_argument("slug_a")
    cmp.add_argument("slug_b")
    cmp.set_defaults(func=cmd_compare)

    return parser


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
