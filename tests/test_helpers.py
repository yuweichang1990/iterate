#!/usr/bin/env python
"""
Tests for scripts/helpers.py — the shared utility module.

Covers: parse_frontmatter, make_slug, check_stale_session, get_stale_info,
        get_active_info, suggest_topic, suggest_topics, format_duration,
        format_rate_summary, validate_limits_config, abbreviate_number,
        get_session_stats.
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


class TestGetActiveInfo(unittest.TestCase):
    """Test extracting info from active session state files."""

    def test_extracts_all_fields(self):
        recent = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        content = f'---\ntopic: "Rust async"\nmode: research\niteration: 5\nstarted_at: "{recent}"\n---\n'
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            result = helpers.get_active_info(f.name, "|")
        os.unlink(f.name)
        parts = result.split("|")
        self.assertEqual(parts[0], "Rust async")
        self.assertEqual(parts[1], "research")
        self.assertEqual(parts[2], "5")
        self.assertTrue(parts[3].endswith("m"))  # duration like "0m"

    def test_missing_file_returns_defaults(self):
        result = helpers.get_active_info("/nonexistent/file.md", "|")
        self.assertEqual(result, "unknown|?|0|?")

    def test_missing_fields_have_defaults(self):
        content = '---\ntopic: "test"\n---\n'
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            result = helpers.get_active_info(f.name, "|")
        os.unlink(f.name)
        parts = result.split("|")
        self.assertEqual(parts[0], "test")
        self.assertEqual(parts[1], "?")  # no mode
        self.assertEqual(parts[2], "0")  # no iteration


class TestValidateLimitsConfig(unittest.TestCase):
    """Test rate limits config validation."""

    def test_valid_config(self):
        config = {"threshold": 0.6, "rate_limits": {"4h": {"tokens": 700000}, "daily": {"tokens": 4100000}, "weekly": {"tokens": 29000000}}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(config, f)
            f.flush()
            result = helpers.validate_limits_config(f.name)
        os.unlink(f.name)
        self.assertEqual(result, "ok")

    def test_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write("not json {{{")
            f.flush()
            result = helpers.validate_limits_config(f.name)
        os.unlink(f.name)
        self.assertTrue(result.startswith("invalid JSON"))

    def test_missing_file(self):
        result = helpers.validate_limits_config("/nonexistent/file.json")
        self.assertEqual(result, "file not found")

    def test_missing_rate_limits_key(self):
        config = {"threshold": 0.6}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(config, f)
            f.flush()
            result = helpers.validate_limits_config(f.name)
        os.unlink(f.name)
        self.assertEqual(result, 'missing "rate_limits" key')

    def test_negative_tokens(self):
        config = {"rate_limits": {"4h": {"tokens": -100}}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(config, f)
            f.flush()
            result = helpers.validate_limits_config(f.name)
        os.unlink(f.name)
        self.assertIn("positive number", result)

    def test_non_object_rate_limits(self):
        config = {"rate_limits": "not an object"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(config, f)
            f.flush()
            result = helpers.validate_limits_config(f.name)
        os.unlink(f.name)
        self.assertIn("must be an object", result)

    def test_partial_config_ok(self):
        """Config with only some windows should be valid."""
        config = {"rate_limits": {"daily": {"tokens": 4100000}}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(config, f)
            f.flush()
            result = helpers.validate_limits_config(f.name)
        os.unlink(f.name)
        self.assertEqual(result, "ok")


class TestAbbreviateNumber(unittest.TestCase):
    """Test number abbreviation for dashboard display."""

    def test_millions(self):
        self.assertEqual(helpers.abbreviate_number(4100000), "4.1M")

    def test_exact_millions(self):
        self.assertEqual(helpers.abbreviate_number(29000000), "29M")

    def test_thousands(self):
        self.assertEqual(helpers.abbreviate_number(281140), "281k")

    def test_exact_thousands(self):
        self.assertEqual(helpers.abbreviate_number(700000), "700k")

    def test_small_numbers(self):
        self.assertEqual(helpers.abbreviate_number(500), "500")

    def test_zero(self):
        self.assertEqual(helpers.abbreviate_number(0), "0")

    def test_one_million(self):
        self.assertEqual(helpers.abbreviate_number(1000000), "1M")


class TestGetSessionStats(unittest.TestCase):
    """Test session stats extraction (E-block)."""

    def test_counts_output_tokens_from_transcript(self):
        """Should sum output_tokens from transcript JSONL entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = os.path.join(tmpdir, "transcript.jsonl")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(output_dir)
            with open(transcript, "w", encoding="utf-8") as f:
                f.write('{"usage": {"output_tokens": 500}}\n')
                f.write('{"usage": {"output_tokens": 300}}\n')
                f.write('{"usage": {"input_tokens": 1000}}\n')  # input tokens ignored
                f.write('{"usage": {"output_tokens": 200}}\n')
            tokens, files, kb = helpers.get_session_stats(transcript, output_dir)
            self.assertEqual(tokens, 1000)

    def test_counts_files_in_output_dir(self):
        """Should count all files in output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = os.path.join(tmpdir, "transcript.jsonl")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(output_dir)
            with open(transcript, "w", encoding="utf-8") as f:
                f.write('{"usage": {}}\n')
            for name in ["00-overview.md", "01-details.md", "_index.md", ".topic"]:
                with open(os.path.join(output_dir, name), "w") as f:
                    f.write("content")
            tokens, files, kb = helpers.get_session_stats(transcript, output_dir)
            self.assertEqual(files, 4)  # all files counted

    def test_computes_output_kb(self):
        """Should compute total output size in KB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = os.path.join(tmpdir, "transcript.jsonl")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(output_dir)
            with open(transcript, "w", encoding="utf-8") as f:
                f.write("{}\n")
            # Write 1024 bytes = 1.0 KB
            with open(os.path.join(output_dir, "file.md"), "w") as f:
                f.write("x" * 1024)
            tokens, files, kb = helpers.get_session_stats(transcript, output_dir)
            self.assertAlmostEqual(kb, 1.0, places=0)

    def test_missing_transcript(self):
        """Should return 0 tokens for missing transcript."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(output_dir)
            tokens, files, kb = helpers.get_session_stats("/nonexistent.jsonl", output_dir)
            self.assertEqual(tokens, 0)

    def test_missing_output_dir(self):
        """Should return 0 files and 0 KB for missing output dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = os.path.join(tmpdir, "transcript.jsonl")
            with open(transcript, "w", encoding="utf-8") as f:
                f.write('{"usage": {"output_tokens": 100}}\n')
            tokens, files, kb = helpers.get_session_stats(transcript, "/nonexistent/dir")
            self.assertEqual(tokens, 100)
            self.assertEqual(files, 0)
            self.assertAlmostEqual(kb, 0.0)

    def test_empty_transcript(self):
        """Should handle empty transcript file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = os.path.join(tmpdir, "transcript.jsonl")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(output_dir)
            with open(transcript, "w", encoding="utf-8") as f:
                pass  # empty file
            tokens, files, kb = helpers.get_session_stats(transcript, output_dir)
            self.assertEqual(tokens, 0)


class TestSuggestTopics(unittest.TestCase):
    """Test extracting multiple topic suggestions."""

    def test_extracts_multiple(self):
        content = """# Interests
## Suggested Next Directions
1. Build a Rust CLI tool
2. Learn WebAssembly
3. Explore distributed systems
4. Study quantum computing
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            result = helpers.suggest_topics(f.name, max_count=3)
        os.unlink(f.name)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "Build a Rust CLI tool")
        self.assertEqual(result[1], "Learn WebAssembly")
        self.assertEqual(result[2], "Explore distributed systems")

    def test_fewer_than_requested(self):
        content = """## Suggested Next Directions
1. Only one topic
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            result = helpers.suggest_topics(f.name, max_count=3)
        os.unlink(f.name)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "Only one topic")

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("")
            f.flush()
            result = helpers.suggest_topics(f.name, max_count=3)
        os.unlink(f.name)
        self.assertEqual(result, [])

    def test_missing_file(self):
        result = helpers.suggest_topics("/nonexistent/file.md")
        self.assertEqual(result, [])

    def test_suggest_topic_still_works(self):
        """Ensure the original suggest_topic (singular) still works via suggest_topics."""
        content = """## Suggested Next Directions
1. First topic
2. Second topic
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            result = helpers.suggest_topic(f.name)
        os.unlink(f.name)
        self.assertEqual(result, "First topic")


if __name__ == "__main__":
    unittest.main()
