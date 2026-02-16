#!/usr/bin/env python
"""
Tests for scripts/helpers.py — the shared utility module.

Covers: parse_frontmatter, make_slug, check_stale_session, get_stale_info,
        suggest_topic, format_duration, format_rate_summary.
"""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from conftest import import_script

helpers = import_script("helpers.py")


class TestParseFrontmatter(unittest.TestCase):
    """Test YAML-like frontmatter parsing."""

    def test_basic_fields(self):
        content = '---\ntopic: "Rust async"\nmode: research\niteration: 3\n---\nBody text'
        fields = helpers.parse_frontmatter(content)
        self.assertEqual(fields["topic"], "Rust async")
        self.assertEqual(fields["mode"], "research")
        self.assertEqual(fields["iteration"], "3")

    def test_empty_content(self):
        self.assertEqual(helpers.parse_frontmatter(""), {})

    def test_no_frontmatter(self):
        self.assertEqual(helpers.parse_frontmatter("Just body text"), {})

    def test_unclosed_frontmatter(self):
        content = "---\ntopic: test\nmode: build\n"
        fields = helpers.parse_frontmatter(content)
        # Still parses fields even without closing ---
        self.assertEqual(fields["topic"], "test")

    def test_quoted_values_stripped(self):
        content = '---\ntopic: "hello world"\n---\n'
        fields = helpers.parse_frontmatter(content)
        self.assertEqual(fields["topic"], "hello world")

    def test_colon_in_value(self):
        content = '---\nstarted_at: "2026-02-16T10:30:00Z"\n---\n'
        fields = helpers.parse_frontmatter(content)
        self.assertEqual(fields["started_at"], "2026-02-16T10:30:00Z")


class TestMakeSlug(unittest.TestCase):
    """Test slug generation."""

    def test_basic_english(self):
        self.assertEqual(helpers.make_slug("Rust async programming"), "rust-async-programming")

    def test_special_characters(self):
        self.assertEqual(helpers.make_slug("C++ vs Rust!"), "c-vs-rust")

    def test_cjk_falls_back_to_hash(self):
        slug = helpers.make_slug("分散式系統")
        self.assertTrue(slug.startswith("topic-"))
        self.assertEqual(len(slug), len("topic-") + 8)

    def test_mixed_cjk_and_english(self):
        slug = helpers.make_slug("Rust 非同步程式設計")
        self.assertEqual(slug, "rust")

    def test_long_slug_truncated(self):
        long_topic = "a very long topic " * 10
        slug = helpers.make_slug(long_topic)
        self.assertLessEqual(len(slug), 50)
        self.assertFalse(slug.endswith("-"))

    def test_empty_after_normalize(self):
        slug = helpers.make_slug("日本語テスト")
        self.assertTrue(slug.startswith("topic-"))


class TestCheckStaleSession(unittest.TestCase):
    """Test stale session detection."""

    def test_stale_session(self):
        old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).strftime("%Y-%m-%dT%H:%M:%SZ")
        content = f'---\nstarted_at: "{old_time}"\n---\n'
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            result = helpers.check_stale_session(f.name, max_hours=24)
        os.unlink(f.name)
        self.assertTrue(result)

    def test_fresh_session(self):
        recent_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        content = f'---\nstarted_at: "{recent_time}"\n---\n'
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            result = helpers.check_stale_session(f.name, max_hours=24)
        os.unlink(f.name)
        self.assertFalse(result)

    def test_missing_file(self):
        self.assertFalse(helpers.check_stale_session("/nonexistent/file.md"))

    def test_no_started_at(self):
        content = "---\ntopic: test\n---\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            result = helpers.check_stale_session(f.name)
        os.unlink(f.name)
        self.assertFalse(result)


class TestGetStaleInfo(unittest.TestCase):
    """Test extracting info from stale session state files."""

    def test_extracts_all_fields(self):
        content = '---\ntopic: "Rust async"\ntopic_slug: "rust-async"\niteration: 5\n---\n'
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            result = helpers.get_stale_info(f.name, "|")
        os.unlink(f.name)
        self.assertEqual(result, "Rust async|rust-async|5")

    def test_missing_file_returns_defaults(self):
        result = helpers.get_stale_info("/nonexistent/file.md", "|")
        self.assertEqual(result, "unknown|unknown|0")


class TestSuggestTopic(unittest.TestCase):
    """Test topic auto-selection from interests file."""

    def test_extracts_first_suggestion(self):
        content = """# Interests
## Suggested Next Directions
1. Build a Rust CLI tool
2. Learn WebAssembly
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            result = helpers.suggest_topic(f.name)
        os.unlink(f.name)
        self.assertEqual(result, "Build a Rust CLI tool")

    def test_skips_no_suggestions_yet(self):
        content = """## Suggested Next Directions
1. No suggestions yet
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            result = helpers.suggest_topic(f.name)
        os.unlink(f.name)
        self.assertEqual(result, "")

    def test_missing_file(self):
        self.assertEqual(helpers.suggest_topic("/nonexistent/file.md"), "")

    def test_no_section(self):
        content = "# Interests\nSome text without the section header\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            result = helpers.suggest_topic(f.name)
        os.unlink(f.name)
        self.assertEqual(result, "")


class TestFormatDuration(unittest.TestCase):
    """Test duration formatting from timestamp to now."""

    def test_invalid_timestamp(self):
        self.assertEqual(helpers.format_duration("not-a-date"), "?")

    def test_returns_string(self):
        # Can't test exact value since it depends on current time,
        # but verify it returns a non-error result for valid timestamps
        recent = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        result = helpers.format_duration(recent)
        self.assertNotEqual(result, "?")
        self.assertTrue(result.endswith("m"))


class TestFormatRateSummary(unittest.TestCase):
    """Test rate check JSON formatting."""

    def test_allowed_no_exceeded(self):
        data = {
            "allowed": True,
            "details": [
                {"window": "daily", "pct": 30.0, "used": 300000, "limit": 1000000, "threshold": 0.6, "exceeded": False}
            ]
        }
        result = helpers.format_rate_summary(json.dumps(data), "|")
        parts = result.split("|")
        self.assertEqual(parts[0], "yes")
        self.assertEqual(parts[1], "")  # no detail lines (nothing exceeded)
        self.assertIn("daily:30.0%", parts[2])

    def test_not_allowed_exceeded(self):
        data = {
            "allowed": False,
            "details": [
                {"window": "daily", "pct": 70.0, "used": 700000, "limit": 1000000, "threshold": 0.6, "exceeded": True}
            ]
        }
        result = helpers.format_rate_summary(json.dumps(data), "|")
        parts = result.split("|")
        self.assertEqual(parts[0], "no")
        self.assertIn("700,000", parts[1])
        self.assertIn("daily:70.0%", parts[2])

    def test_invalid_json(self):
        result = helpers.format_rate_summary("not json", "|")
        self.assertTrue(result.startswith("yes|"))


if __name__ == "__main__":
    unittest.main()
