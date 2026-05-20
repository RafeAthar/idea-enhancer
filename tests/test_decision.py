"""Tests for decision.py — the most fragile parser in the codebase."""

from idea_enhancer.decision import _parse_scores, _parse_kill_criteria, _parse_recommendation, parse_decision
from idea_enhancer.models import Scores


class TestParseScores:
    def test_standard_format(self):
        block = """\
- TAM: 8
- Competitive density: 6
- Moat: 4
- Founder-fit: 7
- Why-now timing: 9
- Capital efficiency: 5"""
        scores = _parse_scores(block)
        assert scores.tam == 8
        assert scores.competitive_density == 6
        assert scores.moat == 4
        assert scores.founder_fit == 7
        assert scores.why_now == 9
        assert scores.capital_efficiency == 5
        assert scores.total == 39
        assert scores.average == 6.5

    def test_alternative_labels(self):
        block = """\
- TAM: 7
- Competitive density: 5
- Moat: 3
- Founder fit: 6
- Why-now: 8
- Capital efficiency: 4"""
        scores = _parse_scores(block)
        assert scores.founder_fit == 6
        assert scores.why_now == 8

    def test_missing_fields_default_to_5(self):
        block = """\
- TAM: 9
- Moat: 2"""
        scores = _parse_scores(block)
        assert scores.tam == 9
        assert scores.moat == 2
        assert scores.competitive_density == 5  # default
        assert scores.founder_fit == 5  # default

    def test_values_clamped_to_1_10(self):
        block = """\
- TAM: 0
- Moat: 15"""
        scores = _parse_scores(block)
        assert scores.tam == 1
        assert scores.moat == 10

    def test_empty_block(self):
        scores = _parse_scores("")
        assert scores.tam == 5
        assert scores.average == 5.0


class TestParseKillCriteria:
    def test_dash_list(self):
        block = """\
- No paying customers after 30 interviews
- CAC exceeds 3x LTV in first cohort
- No organic search volume for core problem"""
        criteria = _parse_kill_criteria(block)
        assert len(criteria) == 3
        assert "No paying customers after 30 interviews" in criteria

    def test_bullet_list(self):
        block = """\
* First criterion
* Second criterion"""
        criteria = _parse_kill_criteria(block)
        assert len(criteria) == 2

    def test_max_five_criteria(self):
        block = "\n".join(f"- criterion {i}" for i in range(8))
        criteria = _parse_kill_criteria(block)
        assert len(criteria) == 5


class TestParseRecommendation:
    def test_standard_format(self):
        block = "Recommendation: explore. The market shows promise but moat is unclear."
        rec, rationale = _parse_recommendation(block)
        assert rec == "explore"
        assert "moat is unclear" in rationale

    def test_build(self):
        block = "Recommendation: build. Strong founder fit and empty niche."
        rec, rationale = _parse_recommendation(block)
        assert rec == "build"

    def test_kill(self):
        block = "Recommendation: kill - Market too small and competitive."
        rec, rationale = _parse_recommendation(block)
        assert rec == "kill"

    def test_no_match_defaults_to_explore(self):
        block = "This idea needs more research."
        rec, rationale = _parse_recommendation(block)
        assert rec == "explore"
        assert "more research" in rationale


class TestParseDecision:
    def test_full_decision(self):
        raw = """\
### Scores (1-10, integer)

- TAM: 7
- Competitive density: 8
- Moat: 3
- Founder-fit: 6
- Why-now timing: 5
- Capital efficiency: 4

### Kill criteria

- CAC exceeds LTV in 90 days
- No signups after 200 landing page visitors
- Competitor releases free alternative

### Cheapest validation experiment

Post in 3 relevant subreddits with a landing page. Measure signups.

### Recommendation

Recommendation: explore. Market exists but moat is weak."""
        artifact = parse_decision(raw)
        assert artifact.scores.tam == 7
        assert artifact.scores.total == 33
        assert len(artifact.kill_criteria) == 3
        assert artifact.recommendation == "explore"
        assert "moat is weak" in artifact.rationale
