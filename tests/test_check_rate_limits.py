#!/usr/bin/env python
"""Tests for check-rate-limits.py"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import importlib

# Import the module by file path (has hyphens in name)
spec = importlib.util.spec_from_file_location(
    "check_rate_limits",
    str(Path(__file__).parent.parent / "scripts" / "check-rate-limits.py"),
)
check_rate_limits = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_rate_limits)


class TestGetSessionTokens(unittest.TestCase):
    """Test session token counting from transcript JSONL."""

    def test_empty_transcript(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write("")
            f.flush()
            result = check_rate_limits.get_session_tokens(f.name)
        os.unlink(f.name)
        self.assertEqual(result, 0)

    def test_counts_output_tokens(self):
        lines = [
            json.dumps({"role": "assistant", "usage": {"output_tokens": 100, "input_tokens": 500}}),
            json.dumps({"role": "assistant", "usage": {"output_tokens": 200, "input_tokens": 300}}),
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write("\n".join(lines))
            f.flush()
            result = check_rate_limits.get_session_tokens(f.name)
        os.unlink(f.name)
        self.assertEqual(result, 300)

    def test_missing_file(self):
        result = check_rate_limits.get_session_tokens("/nonexistent/file.jsonl")
        self.assertEqual(result, 0)

    def test_none_path(self):
        result = check_rate_limits.get_session_tokens(None)
        self.assertEqual(result, 0)

    def test_malformed_json_lines(self):
        lines = [
            json.dumps({"role": "assistant", "usage": {"output_tokens": 100}}),
            "not valid json",
            json.dumps({"role": "assistant", "usage": {"output_tokens": 50}}),
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write("\n".join(lines))
            f.flush()
            result = check_rate_limits.get_session_tokens(f.name)
        os.unlink(f.name)
        self.assertEqual(result, 150)


class TestGetDailyTokens(unittest.TestCase):
    """Test daily token extraction from stats-cache."""

    def test_normal_stats(self):
        stats = {
            "dailyModelTokens": [
                {"date": "2026-02-15", "tokensByModel": {"claude-opus-4-6": 1000, "claude-sonnet-4-5-20250929": 500}},
                {"date": "2026-02-16", "tokensByModel": {"claude-opus-4-6": 2000}},
            ]
        }
        result = check_rate_limits.get_daily_tokens(stats)
        self.assertEqual(result["2026-02-15"], 1500)
        self.assertEqual(result["2026-02-16"], 2000)

    def test_empty_stats(self):
        result = check_rate_limits.get_daily_tokens({})
        self.assertEqual(result, {})

    def test_missing_tokens_by_model(self):
        stats = {"dailyModelTokens": [{"date": "2026-02-16"}]}
        result = check_rate_limits.get_daily_tokens(stats)
        self.assertEqual(result.get("2026-02-16", 0), 0)


class TestCheckLimits(unittest.TestCase):
    """Test the main check_limits function."""

    def _write_json(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def _write_state(self, path, started_at):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f'---\nstarted_at: "{started_at}"\n---\n')

    @patch.object(check_rate_limits, "LIMITS_FILE")
    def test_no_limits_file(self, mock_limits):
        mock_limits.__str__ = lambda s: "/nonexistent/limits.json"
        mock_limits.exists = lambda: False
        # Patch load_json to return None for missing file
        with patch.object(check_rate_limits, "load_json", return_value=None):
            result = check_rate_limits.check_limits()
        self.assertTrue(result["allowed"])

    def test_daily_under_threshold(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            limits_file = Path(tmpdir) / "limits.json"
            stats_file = Path(tmpdir) / "stats.json"
            state_file = Path(tmpdir) / "state.md"

            now = datetime.now(timezone.utc)
            today = now.strftime("%Y-%m-%d")

            self._write_json(limits_file, {
                "threshold": 0.6,
                "rate_limits": {"daily": {"tokens": 1000000}}
            })
            self._write_json(stats_file, {
                "dailyModelTokens": [{"date": today, "tokensByModel": {"model": 100000}}]
            })
            self._write_state(state_file, now.strftime("%Y-%m-%dT%H:%M:%SZ"))

            with patch.object(check_rate_limits, "LIMITS_FILE", limits_file), \
                 patch.object(check_rate_limits, "STATS_FILE", stats_file), \
                 patch.object(check_rate_limits, "STATE_FILE", state_file):
                result = check_rate_limits.check_limits(threshold_override=0.6)

            self.assertTrue(result["allowed"])

    def test_daily_over_threshold(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            limits_file = Path(tmpdir) / "limits.json"
            stats_file = Path(tmpdir) / "stats.json"
            state_file = Path(tmpdir) / "state.md"

            now = datetime.now(timezone.utc)
            today = now.strftime("%Y-%m-%d")

            self._write_json(limits_file, {
                "threshold": 0.6,
                "rate_limits": {"daily": {"tokens": 1000000}}
            })
            self._write_json(stats_file, {
                "dailyModelTokens": [{"date": today, "tokensByModel": {"model": 700000}}]
            })
            self._write_state(state_file, now.strftime("%Y-%m-%dT%H:%M:%SZ"))

            with patch.object(check_rate_limits, "LIMITS_FILE", limits_file), \
                 patch.object(check_rate_limits, "STATS_FILE", stats_file), \
                 patch.object(check_rate_limits, "STATE_FILE", state_file):
                result = check_rate_limits.check_limits(threshold_override=0.6)

            self.assertFalse(result["allowed"])


class TestThresholdOverride(unittest.TestCase):
    """Test that threshold_override takes precedence."""

    def test_override_respected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            limits_file = Path(tmpdir) / "limits.json"
            stats_file = Path(tmpdir) / "stats.json"
            state_file = Path(tmpdir) / "state.md"

            now = datetime.now(timezone.utc)
            today = now.strftime("%Y-%m-%d")

            # Config says 0.6 threshold, but override says 0.9
            with open(limits_file, "w") as f:
                json.dump({"threshold": 0.6, "rate_limits": {"daily": {"tokens": 1000000}}}, f)
            with open(stats_file, "w") as f:
                json.dump({"dailyModelTokens": [{"date": today, "tokensByModel": {"model": 700000}}]}, f)
            state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(state_file, "w") as f:
                f.write(f'---\nstarted_at: "{now.strftime("%Y-%m-%dT%H:%M:%SZ")}"\n---\n')

            with patch.object(check_rate_limits, "LIMITS_FILE", limits_file), \
                 patch.object(check_rate_limits, "STATS_FILE", stats_file), \
                 patch.object(check_rate_limits, "STATE_FILE", state_file):
                # At 0.6 threshold, 70% usage would exceed
                result_strict = check_rate_limits.check_limits(threshold_override=0.6)
                # At 0.9 threshold, 70% usage would not exceed
                result_lenient = check_rate_limits.check_limits(threshold_override=0.9)

            self.assertFalse(result_strict["allowed"])
            self.assertTrue(result_lenient["allowed"])


if __name__ == "__main__":
    unittest.main()
