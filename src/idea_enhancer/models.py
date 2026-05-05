from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class QA:
    question: str
    answer: str = ""

    @property
    def answered(self) -> bool:
        return bool(self.answer.strip())


@dataclass
class PersonaCritique:
    name: str
    text: str


@dataclass
class Scores:
    tam: int = 0
    competitive_density: int = 0
    moat: int = 0
    founder_fit: int = 0
    why_now: int = 0
    capital_efficiency: int = 0

    @property
    def total(self) -> int:
        return (
            self.tam
            + self.competitive_density
            + self.moat
            + self.founder_fit
            + self.why_now
            + self.capital_efficiency
        )

    @property
    def average(self) -> float:
        return self.total / 6.0


@dataclass
class DecisionArtifact:
    scores: Scores
    kill_criteria: list[str]
    validation_experiment: str
    recommendation: str
    rationale: str


@dataclass
class Report:
    idea: str
    title: str
    slug: str
    created: date = field(default_factory=date.today)
    interview: list[QA] = field(default_factory=list)
    market: str = ""
    competitors: str = ""
    critiques: list[PersonaCritique] = field(default_factory=list)
    synthesis: str = ""
    decision: DecisionArtifact | None = None
