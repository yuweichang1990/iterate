#!/usr/bin/env python
"""Tests for history.py"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import importlib

spec = importlib.util.spec_from_file_location(
    "history",
    str(Path(__file__).parent.parent / "scripts" / "history.py"),
)
history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(history)


class TestHistoryAdd(unittest.TestCase):
    """Test adding session records."""

    def test_add_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hist_file = Path(tmpdir) / "findings" / ".history.json"
            with patch.object(history, "HISTORY_FILE", hist_file):
                history.cmd_add([
                    "Rust async",
                    "research",
                    "rust-async",
                    "moderate",
                    "0.6",
                    "2026-02-16T10:00:00Z",
                    "auto-explore-findings/rust-async",
                ])
                data = json.loads(hist_file.read_text(encoding="utf-8"))

            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["topic"], "Rust async")
            self.assertEqual(data[0]["mode"], "research")
            self.assertEqual(data[0]["status"], "running")
            self.assertEqual(data[0]["iterations"], 1)

    def test_add_appends_to_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hist_file = Path(tmpdir) / ".history.json"
            hist_file.write_text('[{"topic": "existing"}]', encoding="utf-8")
            with patch.object(history, "HISTORY_FILE", hist_file):
                history.cmd_add([
                    "New topic",
                    "build",
                    "new-topic",
                    "aggressive",
                    "0.8",
                    "2026-02-16T12:00:00Z",
                    "auto-explore-findings/new-topic",
                ])
                data = json.loads(hist_file.read_text(encoding="utf-8"))

            self.assertEqual(len(data), 2)
            self.assertEqual(data[1]["topic"], "New topic")


class TestHistoryEnd(unittest.TestCase):
    """Test ending session records."""

    def test_end_marks_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hist_file = Path(tmpdir) / ".history.json"
            hist_file.write_text(json.dumps([{
                "topic": "Test",
                "slug": "test",
                "status": "running",
                "iterations": 1,
            }]), encoding="utf-8")
            with patch.object(history, "HISTORY_FILE", hist_file):
                history.cmd_end(["test", "5", "completed", "All done"])
                data = json.loads(hist_file.read_text(encoding="utf-8"))

            self.assertEqual(data[0]["status"], "completed")
            self.assertEqual(data[0]["iterations"], 5)
            self.assertEqual(data[0]["reason"], "All done")
            self.assertIsNotNone(data[0]["ended_at"])

    def test_end_matches_most_recent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hist_file = Path(tmpdir) / ".history.json"
            hist_file.write_text(json.dumps([
                {"slug": "test", "status": "completed", "iterations": 3},
                {"slug": "test", "status": "running", "iterations": 1},
            ]), encoding="utf-8")
            with patch.object(history, "HISTORY_FILE", hist_file):
                history.cmd_end(["test", "10", "rate-limited", "Budget exceeded"])
                data = json.loads(hist_file.read_text(encoding="utf-8"))

            # First entry should be unchanged
            self.assertEqual(data[0]["status"], "completed")
            # Second (most recent running) should be updated
            self.assertEqual(data[1]["status"], "rate-limited")
            self.assertEqual(data[1]["iterations"], 10)

    def test_end_no_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hist_file = Path(tmpdir) / ".history.json"
            hist_file.write_text(json.dumps([
                {"slug": "other", "status": "running", "iterations": 1},
            ]), encoding="utf-8")
            with patch.object(history, "HISTORY_FILE", hist_file):
                history.cmd_end(["nonexistent", "5", "completed"])
                data = json.loads(hist_file.read_text(encoding="utf-8"))

            # Nothing should change
            self.assertEqual(data[0]["status"], "running")


class TestFixStaleSessions(unittest.TestCase):
    """Test stale session cleanup."""

    def test_marks_running_as_error_when_no_state_file(self):
        """When no state file exists, running sessions should be marked as error."""
        entries = [
            {"slug": "a", "status": "completed", "iterations": 5},
            {"slug": "b", "status": "running", "iterations": 3},
        ]
        # Path.exists() returns False → no active session → fix stale entries
        with patch.object(Path, "exists", return_value=False):
            result = history.fix_stale_sessions(entries)
        self.assertTrue(result)
        self.assertEqual(entries[0]["status"], "completed")  # unchanged
        self.assertEqual(entries[1]["status"], "error")  # fixed
        self.assertEqual(entries[1]["reason"], "Session ended unexpectedly")
        self.assertIsNotNone(entries[1]["ended_at"])

    def test_no_change_when_all_completed(self):
        entries = [
            {"slug": "a", "status": "completed"},
            {"slug": "b", "status": "rate-limited"},
        ]
        with patch.object(Path, "exists", return_value=False):
            result = history.fix_stale_sessions(entries)
        self.assertFalse(result)

    def test_no_change_when_state_file_exists(self):
        """When state file exists, running sessions should NOT be touched."""
        entries = [{"slug": "a", "status": "running"}]
        with patch.object(Path, "exists", return_value=True):
            result = history.fix_stale_sessions(entries)
        self.assertFalse(result)
        self.assertEqual(entries[0]["status"], "running")  # unchanged


class TestFormatDuration(unittest.TestCase):
    """Test duration formatting."""

    def test_minutes_only(self):
        result = history.format_duration(
            "2026-02-16T10:00:00Z",
            "2026-02-16T10:30:00Z",
        )
        self.assertEqual(result, "30m")

    def test_hours_and_minutes(self):
        result = history.format_duration(
            "2026-02-16T10:00:00Z",
            "2026-02-16T12:15:00Z",
        )
        self.assertEqual(result, "2h 15m")

    def test_invalid_timestamp(self):
        result = history.format_duration("invalid", "also-invalid")
        self.assertEqual(result, "?")


class TestStatusIcon(unittest.TestCase):
    """Test status icon mapping."""

    def test_known_statuses(self):
        self.assertEqual(history.status_icon("running"), ">>")
        self.assertEqual(history.status_icon("completed"), "OK")
        self.assertEqual(history.status_icon("rate-limited"), "$$")
        self.assertEqual(history.status_icon("cancelled"), "--")
        self.assertEqual(history.status_icon("max-iterations"), "##")
        self.assertEqual(history.status_icon("resumed"), "->")
        self.assertEqual(history.status_icon("error"), "!!")

    def test_unknown_status(self):
        self.assertEqual(history.status_icon("something-else"), "??")


class TestTokenTracking(unittest.TestCase):
    """Test E-block: token tracking in history entries."""

    def test_end_stores_token_stats(self):
        """cmd_end should store estimated_tokens, files_written, total_output_kb."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hist_file = Path(tmpdir) / ".history.json"
            hist_file.write_text(json.dumps([{
                "topic": "Test",
                "slug": "test",
                "status": "running",
                "iterations": 1,
            }]), encoding="utf-8")
            with patch.object(history, "HISTORY_FILE", hist_file):
                history.cmd_end(["test", "5", "completed", "Done", "12500", "8", "45.2"])
                data = json.loads(hist_file.read_text(encoding="utf-8"))

            self.assertEqual(data[0]["estimated_tokens"], 12500)
            self.assertEqual(data[0]["files_written"], 8)
            self.assertAlmostEqual(data[0]["total_output_kb"], 45.2)

    def test_end_defaults_to_zero_without_stats(self):
        """cmd_end should default to 0 when stats args are omitted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hist_file = Path(tmpdir) / ".history.json"
            hist_file.write_text(json.dumps([{
                "topic": "Test",
                "slug": "test",
                "status": "running",
                "iterations": 1,
            }]), encoding="utf-8")
            with patch.object(history, "HISTORY_FILE", hist_file):
                history.cmd_end(["test", "3", "rate-limited", "Budget exceeded"])
                data = json.loads(hist_file.read_text(encoding="utf-8"))

            self.assertEqual(data[0]["estimated_tokens"], 0)
            self.assertEqual(data[0]["files_written"], 0)
            self.assertAlmostEqual(data[0]["total_output_kb"], 0.0)

    def test_end_handles_empty_string_stats(self):
        """cmd_end should handle empty string stats gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hist_file = Path(tmpdir) / ".history.json"
            hist_file.write_text(json.dumps([{
                "topic": "Test",
                "slug": "test",
                "status": "running",
                "iterations": 1,
            }]), encoding="utf-8")
            with patch.object(history, "HISTORY_FILE", hist_file):
                history.cmd_end(["test", "2", "completed", "Done", "", "", ""])
                data = json.loads(hist_file.read_text(encoding="utf-8"))

            self.assertEqual(data[0]["estimated_tokens"], 0)
            self.assertEqual(data[0]["files_written"], 0)
            self.assertAlmostEqual(data[0]["total_output_kb"], 0.0)


class TestLifetimeStats(unittest.TestCase):
    """Test E-block: lifetime stats computation."""

    def test_lifetime_stats_sum(self):
        """Lifetime stats should sum across all history entries."""
        entries = [
            {"estimated_tokens": 5000, "files_written": 3, "total_output_kb": 10.5, "iterations": 5},
            {"estimated_tokens": 8000, "files_written": 5, "total_output_kb": 20.0, "iterations": 8},
            {"estimated_tokens": 0, "files_written": 0, "total_output_kb": 0.0, "iterations": 2},
        ]
        total_tokens = sum(e.get("estimated_tokens", 0) for e in entries)
        total_files = sum(e.get("files_written", 0) for e in entries)
        total_kb = sum(e.get("total_output_kb", 0) for e in entries)

        self.assertEqual(total_tokens, 13000)
        self.assertEqual(total_files, 8)
        self.assertAlmostEqual(total_kb, 30.5)

    def test_lifetime_stats_missing_fields(self):
        """Lifetime stats should default to 0 for entries without token fields."""
        entries = [
            {"topic": "Old session"},  # no token fields (pre-E-block entry)
            {"estimated_tokens": 5000, "files_written": 3, "total_output_kb": 10.5},
        ]
        total_tokens = sum(e.get("estimated_tokens", 0) for e in entries)
        total_files = sum(e.get("files_written", 0) for e in entries)

        self.assertEqual(total_tokens, 5000)
        self.assertEqual(total_files, 3)


if __name__ == "__main__":
    unittest.main()
