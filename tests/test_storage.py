"""Tests for storage.py — frontmatter parsing, slugify, render."""

from idea_enhancer.storage import parse_frontmatter, slugify


class TestSlugify:
    def test_basic(self):
        assert slugify("AI Personal CFO") == "ai-personal-cfo"

    def test_special_chars_removed(self):
        assert slugify("Hello, World! (v2)") == "hello-world-v2"

    def test_max_words(self):
        result = slugify("a b c d e f g h i")
        assert len(result.split("-")) == 6

    def test_empty_string(self):
        assert slugify("") == "idea"

    def test_multiple_hyphens_collapsed(self):
        assert slugify("hello---world") == "hello-world"


class TestParseFrontmatter:
    def test_standard_frontmatter(self):
        md = """\
---
title: My Idea
slug: my-idea
date: 2025-01-15
score: 6.5/10
recommendation: explore
---

# Content here"""
        meta = parse_frontmatter(md)
        assert meta["title"] == "My Idea"
        assert meta["slug"] == "my-idea"
        assert meta["date"] == "2025-01-15"
        assert meta["score"] == "6.5/10"
        assert meta["recommendation"] == "explore"

    def test_value_with_colon(self):
        """Values containing colons (URLs, timestamps) must be preserved."""
        md = """\
---
title: Test
url: https://example.com/path
timestamp: 2025-01-15T10:30:00
---

Content"""
        meta = parse_frontmatter(md)
        assert meta["url"] == "https://example.com/path"
        assert meta["timestamp"] == "2025-01-15T10:30:00"

    def test_no_frontmatter(self):
        md = "Just some content without frontmatter."
        meta = parse_frontmatter(md)
        assert meta == {}
