from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

from idea_enhancer.client import call
from idea_enhancer.storage import IDEAS_DIR, list_reports

WORD_RE = re.compile(r"[a-z][a-z0-9]+")
STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "have", "has", "are",
    "was", "were", "but", "not", "you", "your", "they", "their", "would",
    "could", "should", "will", "what", "which", "when", "where", "while",
    "into", "than", "then", "them", "also", "any", "all", "can", "may",
    "more", "less", "very", "much", "some", "such", "one", "two", "three",
    "about", "over", "under", "between", "out", "off", "down", "up", "its",
    "it", "is", "be", "an", "a", "of", "to", "in", "on", "or", "as", "by",
    "at", "if", "we", "us", "our", "i", "do", "does", "did", "so",
}


def _tokens(text: str) -> list[str]:
    return [w for w in WORD_RE.findall(text.lower()) if w not in STOPWORDS]


def _tfidf_matrix(docs: list[str]) -> tuple[list[Counter[str]], dict[str, float]]:
    """Returns per-doc tf vectors + idf weights. Stdlib only."""
    tfs = [Counter(_tokens(d)) for d in docs]
    df: Counter[str] = Counter()
    for tf in tfs:
        for term in tf:
            df[term] += 1
    n = len(docs) or 1
    idf = {term: math.log((n + 1) / (cnt + 1)) + 1 for term, cnt in df.items()}
    return tfs, idf


def _vec(tf: Counter[str], idf: dict[str, float]) -> dict[str, float]:
    if not tf:
        return {}
    norm = max(tf.values())
    return {term: (count / norm) * idf.get(term, 0.0) for term, count in tf.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def _score_value(meta: dict) -> float:
    raw = meta.get("score", "")
    m = re.match(r"([0-9]+(?:\.[0-9]+)?)", str(raw))
    return float(m.group(1)) if m else -1.0


def cmd_list(root: Path = IDEAS_DIR) -> int:
    reports = list_reports(root)
    if not reports:
        print(f"No reports in {root}/. Run `enhance run \"...\"` to create one.")
        return 0
    print(f"{'date':<12} {'score':>8}  {'rec':<8}  slug")
    print("-" * 70)
    for r in sorted(reports, key=lambda r: r.get("date", ""), reverse=True):
        print(
            f"{r.get('date',''):<12} {r.get('score','-'):>8}  "
            f"{r.get('recommendation','-'):<8}  {r.get('slug','?')}"
        )
    return 0


def _find_report(slug_or_prefix: str, root: Path = IDEAS_DIR) -> dict | None:
    reports = list_reports(root)
    matches = [r for r in reports if r.get("slug", "").startswith(slug_or_prefix)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        print(f"Ambiguous prefix {slug_or_prefix!r}; matches:")
        for m in matches:
            print(f"  {m.get('slug')}")
        return None
    print(f"No report matching {slug_or_prefix!r}.")
    return None


def cmd_show(slug: str, root: Path = IDEAS_DIR) -> int:
    r = _find_report(slug, root)
    if not r:
        return 1
    print(r["body"])
    return 0


def cmd_search(query: str, root: Path = IDEAS_DIR, top: int = 5) -> int:
    reports = list_reports(root)
    if not reports:
        print(f"No reports in {root}/.")
        return 0
    docs = [r["body"] for r in reports]
    tfs, idf = _tfidf_matrix(docs + [query])
    query_vec = _vec(tfs[-1], idf)
    scored: list[tuple[float, dict]] = []
    for tf, r in zip(tfs[:-1], reports):
        scored.append((_cosine(_vec(tf, idf), query_vec), r))
    scored.sort(key=lambda x: x[0], reverse=True)

    print(f"Query: {query!r}")
    print()
    for sim, r in scored[:top]:
        if sim <= 0:
            continue
        print(
            f"  {sim:.3f}  {r.get('date','?'):<12} "
            f"{r.get('slug','?'):<30} ({r.get('recommendation','-')})"
        )
    if not any(s > 0 for s, _ in scored):
        print("  (no matches)")
    return 0


def cmd_leaderboard(root: Path = IDEAS_DIR) -> int:
    reports = list_reports(root)
    if not reports:
        print(f"No reports in {root}/.")
        return 0
    ranked = sorted(reports, key=lambda r: _score_value(r), reverse=True)
    print(f"{'rank':>4}  {'score':>8}  {'rec':<8}  slug")
    print("-" * 70)
    for i, r in enumerate(ranked, 1):
        sv = _score_value(r)
        score_str = f"{sv:.1f}/10" if sv >= 0 else "n/a"
        print(
            f"{i:>4}  {score_str:>8}  "
            f"{r.get('recommendation','-'):<8}  {r.get('slug','?')}"
        )
    return 0


COMPARE_SYSTEM = """\
You are comparing two startup ideas head-to-head for a founder deciding \
where to allocate their next month of focus. Be specific and concrete. \
Output structure (markdown):

### Side-by-side
A short comparison covering: market size, competitive density, moat, \
why-now, and capital efficiency. One row per dimension, both ideas \
treated symmetrically.

### Where they meaningfully differ
The 2-3 dimensions where the ideas are NOT equivalent. Don't restate the \
table — explain the consequence.

### Recommendation
One paragraph: which would you pick, why, and under what condition would \
you flip. If neither is compelling vs. the founder's opportunity cost, \
say that explicitly.

Be tight. Under 500 words."""


def cmd_compare(slug_a: str, slug_b: str, root: Path = IDEAS_DIR) -> int:
    a = _find_report(slug_a, root)
    b = _find_report(slug_b, root)
    if not a or not b:
        return 1
    user = (
        f"### Idea A — {a.get('slug')}\n\n{a['body']}\n\n"
        f"### Idea B — {b.get('slug')}\n\n{b['body']}\n\n"
        "Compare per the system prompt."
    )
    print(call(system=COMPARE_SYSTEM, user=user, max_tokens=4000, effort="high"))
    return 0
