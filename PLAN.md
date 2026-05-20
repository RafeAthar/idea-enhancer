# Idea Enhancer — Plan

A living document. Update as decisions change. Keep brief; link out for detail.

---

## 1. Concept

A tool that takes a raw idea (one sentence to a paragraph) and, with minimum
manual effort, produces an enriched analysis to help the author see through it:
clarifying questions, market scan, competitor scan, multi-perspective critique,
risks, founder-fit check, and a concrete next-step recommendation.

The goal is **better thinking per idea**, not pretty reports. The system should
force articulation, ground claims in real sources, and end every run with a
decision artifact (score + kill criteria + cheapest validation experiment).

---

## 2. Decisions made so far

- **Form factor:** local CLI tool (Claude Agent SDK), markdown output to an
  `ideas/` folder. No web UI in v0.
- **Flow:** `interview -> research -> multi-persona critique -> synthesis ->
  decision artifact`.
- **Grounding:** every factual claim about market/competitors must come from a
  fetched web source or be explicitly labeled as speculation. No ungrounded
  "competitor lists."
- **Critique style:** multi-persona panel (VC who already passed, skeptical
  target user, domain expert, supportive cofounder) run in parallel, then
  synthesized. Avoids LLM sycophancy.
- **Output:** dated markdown file per idea, plus a `compare` command across
  the corpus.
- **Scope of v1:** does (a) clarify thinking + (b) validate market. Pivot
  generation and execution planning are explicitly out of scope for v1.
- **Branch:** all development on `claude/idea-brainstorming-tool-bU1KY`.

---

## 3. Open questions (revisit before/while building)

- **Idea-type routing:** start with one generic pipeline, or build archetype
  routing (B2B SaaS / consumer / content / hardware / marketplace) from day
  one? Leaning: generic in v0, route in v2 once we see real failure modes.
- **Depth tiers:** single fixed depth, or `quick / standard / deep` modes?
  Leaning: single mode in v0, add tiers when cost becomes annoying.
- **Storage:** flat markdown files vs. SQLite index alongside. Leaning: flat
  files in v0, add an index when corpus search needs it.
- **Scoring rubric:** which dimensions, what scale (1-5? 1-10?), how weighted.
  Defer until after 5-10 real ideas processed.
- **Refresh policy:** how to mark reports stale and re-run. Defer to v2.
- **Privacy:** ideas stay local; no third-party storage beyond Claude API
  itself. Confirm before adding any cloud component.

---

## 4. Phased plan

### Phase 0 — Skeleton (1 sitting)
- Project scaffold, dependencies, Claude Agent SDK wired up.
- `enhance <idea-file-or-string>` command stub that round-trips to Claude and
  writes a markdown file to `ideas/YYYY-MM-DD-slug.md`.
- README with usage.

### Phase 1 — Interview layer
- Generate 3-7 clarifying questions from the raw idea.
- Interactive Q&A in the terminal; user can skip any question.
- Answers folded into the idea context for downstream steps.

### Phase 2 — Grounded research
- Web search tool wired in.
- Two sub-passes: market scan, competitor scan.
- Every claim cites a source URL or is tagged `[speculation]`.
- Calibrated "I couldn't find X" output when evidence is thin.

### Phase 3 — Multi-persona critique
- Personas: VC-who-passed, skeptical target user, domain expert, supportive
  cofounder. Run in parallel.
- Synthesis pass that surfaces real disagreement, not averaged mush.

### Phase 4 — Decision artifact
- Rough scoring (TAM ballpark, competitive density, moat, founder-fit).
- Explicit kill criteria.
- One cheapest-validation experiment (target: under $50 / under 2 days).
- Recommended next action: kill / explore / build.

### Phase 5 — Corpus features
- `list` and `compare` commands across `ideas/`.
- Embedding-based search ("ideas similar to X").
- Cross-idea leaderboard by score.

### Phase 6 (later, not committed) — possible extensions
- Idea variants / lateral pivots.
- Archetype routing.
- Refresh stale reports.
- Web UI.

---

## 5. Things to revisit deliberately

- After 5 real ideas processed: is the report length right? Which sections do
  you actually read?
- After 10 ideas: is the persona panel adding signal or just noise? Drop or
  swap personas.
- Before Phase 5: do we still need a SQLite index, or are markdown + grep
  enough?
- Anytime: if a phase's output isn't changing your behavior on real ideas,
  stop and rethink before adding more.

---

## 6. Non-goals (for now)

- Pretty PDF/Notion export.
- Multi-user / sharing.
- Auto-pivot generation.
- Execution planning (roadmaps, hiring, fundraising).
- Real-time market data feeds.
