from __future__ import annotations

import re
import sys

from idea_enhancer.client import call
from idea_enhancer.models import QA
from idea_enhancer.prompts import INTERVIEW_SYSTEM, interview_user

QUESTION_RE = re.compile(r"^\s*\d+[\.\)]\s*(.+)$")


def parse_questions(text: str) -> list[str]:
    questions: list[str] = []
    for line in text.splitlines():
        m = QUESTION_RE.match(line)
        if m:
            questions.append(m.group(1).strip())
    if not questions:
        questions = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    return questions[:7]


def generate_questions(idea: str) -> list[str]:
    text = call(
        system=INTERVIEW_SYSTEM,
        user=interview_user(idea),
        max_tokens=2000,
        effort="medium",
    )
    return parse_questions(text)


def interactive_answers(questions: list[str]) -> list[QA]:
    print()
    print("Clarifying questions — answer in 1-2 sentences, or press Enter to skip.")
    print("Type 'skip-rest' to skip all remaining questions.")
    print()
    out: list[QA] = []
    skip_all = False
    for i, q in enumerate(questions, 1):
        if skip_all:
            out.append(QA(question=q, answer=""))
            continue
        print(f"  {i}. {q}")
        try:
            ans = input("     > ").strip()
        except EOFError:
            ans = ""
            skip_all = True
        if ans.lower() == "skip-rest":
            ans = ""
            skip_all = True
        out.append(QA(question=q, answer=ans))
        print()
    return out


def run_interview(idea: str, interactive: bool) -> list[QA]:
    questions = generate_questions(idea)
    if not questions:
        return []
    if interactive and sys.stdin.isatty():
        return interactive_answers(questions)
    return [QA(question=q, answer="") for q in questions]


def context_block(qas: list[QA]) -> str:
    parts: list[str] = []
    for qa in qas:
        if qa.answered:
            parts.append(f"Q: {qa.question}\nA: {qa.answer}")
    return "\n\n".join(parts)
