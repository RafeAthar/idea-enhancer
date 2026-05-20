"""Tests for interview.py — question parsing."""

from idea_enhancer.interview import parse_questions


class TestParseQuestions:
    def test_numbered_with_dots(self):
        text = """\
1. Who is the target user?
2. What problem does this solve?
3. Why now?"""
        questions = parse_questions(text)
        assert len(questions) == 3
        assert questions[0] == "Who is the target user?"

    def test_numbered_with_parens(self):
        text = """\
1) First question
2) Second question"""
        questions = parse_questions(text)
        assert len(questions) == 2

    def test_max_seven_questions(self):
        lines = [f"{i}. Question {i}" for i in range(1, 10)]
        questions = parse_questions("\n".join(lines))
        assert len(questions) == 7

    def test_fallback_to_non_blank_lines(self):
        text = """\
Who is the user?
What is the problem?
Why now?"""
        questions = parse_questions(text)
        assert len(questions) == 3

    def test_empty_input(self):
        questions = parse_questions("")
        assert questions == []

    def test_skips_headers(self):
        text = """\
# Questions

1. Real question?"""
        questions = parse_questions(text)
        assert len(questions) == 1
        assert questions[0] == "Real question?"
