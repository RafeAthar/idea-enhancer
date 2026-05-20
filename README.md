# Idea Enhancer

A personal CLI for taking a raw idea and producing an enriched, decision-grade
report — grounded market and competitor research, multi-persona critique, and
a concrete recommendation. See `PLAN.md` for concept, decisions, and roadmap.

## Setup

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

```sh
# Run the full pipeline on an idea
enhance run "An AI personal CFO that auto-categorizes transactions and texts you weekly insights"

# Read the idea from a file
enhance run --file my_idea.md

# Skip the interactive interview
enhance run --skip-interview "..."

# Corpus operations across past ideas
enhance list
enhance show <slug>
enhance compare <slug-a> <slug-b>
enhance search "...query..."
enhance leaderboard
```

Reports land in `ideas/YYYY-MM-DD-<slug>.md`. Each report has a YAML frontmatter
header (date, score, recommendation) used by `list` / `leaderboard` / `compare`.

## How it works

A pipeline of small Claude calls, each with a focused job:

1. **Interview** — generate 3–7 clarifying questions; you answer or skip
2. **Research** — `web_search`-grounded market scan + competitor scan, with
   citations or `[speculation]` tags
3. **Critique** — four personas in parallel (VC who passed, skeptical user,
   domain expert, supportive cofounder), then a synthesis pass
4. **Decision artifact** — scores, kill criteria, cheapest validation
   experiment, recommendation (kill / explore / build)
5. **Corpus** — list, search, compare, and leaderboard across past reports

Model: `claude-opus-4-7` with adaptive thinking. Web search runs server-side.
