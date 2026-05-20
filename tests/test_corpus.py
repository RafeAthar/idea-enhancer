"""Tests for corpus.py — TF-IDF search."""

from idea_enhancer.corpus import _tokens, _tfidf_matrix, _vec, _cosine, _score_value


class TestTokens:
    def test_basic(self):
        tokens = _tokens("The quick brown fox jumps over the lazy dog")
        assert "quick" in tokens
        assert "brown" in tokens
        assert "the" not in tokens  # stopword

    def test_alphanumeric_only(self):
        tokens = _tokens("hello world123")
        assert "hello" in tokens
        assert "world123" in tokens

    def test_case_insensitive(self):
        tokens = _tokens("Hello HELLO")
        assert tokens.count("hello") == 2


class TestCosine:
    def test_identical_docs(self):
        docs = ["machine learning artificial intelligence"]
        tfs, idf = _tfidf_matrix(docs)
        vec = _vec(tfs[0], idf)
        assert _cosine(vec, vec) == pytest.approx(1.0)

    def test_disjoint_docs(self):
        docs = ["alpha beta", "gamma delta"]
        tfs, idf = _tfidf_matrix(docs)
        assert _cosine(_vec(tfs[0], idf), _vec(tfs[1], idf)) == 0.0

    def test_empty_docs(self):
        tfs, idf = _tfidf_matrix([""])
        vec = _vec(tfs[0], idf)
        assert _cosine(vec, {}) == 0.0


class TestScoreValue:
    def test_integer_score(self):
        assert _score_value({"score": "7/10"}) == 7.0

    def test_decimal_score(self):
        assert _score_value({"score": "6.5/10"}) == 6.5

    def test_missing_score(self):
        assert _score_value({}) == -1.0

    def test_bare_number(self):
        assert _score_value({"score": "8"}) == 8.0


import pytest
