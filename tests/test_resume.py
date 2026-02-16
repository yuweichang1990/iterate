#!/usr/bin/env python
"""
Tests for the session resume feature (v1.6.0 F-block).

Covers: history.py cmd_resume, resumed status icon, --resume in setup/help docs.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from conftest import PROJECT_ROOT, import_script

history = import_script("history.py")


class TestHistoryResume(unittest.TestCase):
    """Test cmd_resume finds, marks, and outputs session info."""

    def _make_history(self, entries):
        tmpdir = tempfile.mkdtemp()
        hist_file = Path(tmpdir) / ".history.json"
        hist_file.write_text(json.dumps(entries), encoding="utf-8")
        return tmpdir, hist_file

    def test_resume_finds_most_recent_resumable(self):
        """With no slug, should find the most recent resumable entry."""
        entries = [
            {"slug": "old", "status": "completed", "topic": "Old", "mode": "research",
             "output_dir": "findings/old", "threshold": 0.6, "iterations": 5, "budget": "moderate"},
            {"slug": "recent", "status": "rate-limited", "topic": "Recent", "mode": "build",
             "output_dir": "findings/recent", "threshold": 0.8, "iterations": 10, "budget": "aggressive"},
        ]
        tmpdir, hist_file = self._make_history(entries)
        try:
            with patch.object(history, "HISTORY_FILE", hist_file):
                import io, sys
                captured = io.StringIO()
                sys.stdout = captured
                history.cmd_resume(["|"])
                sys.stdout = sys.__stdout__
                output = captured.getvalue().strip()

            parts = output.split("|")
            self.assertEqual(parts[0], "Recent")
            self.assertEqual(parts[1], "build")
            self.assertEqual(parts[2], "recent")

            # Verify old entry marked as resumed
            data = json.loads(hist_file.read_text(encoding="utf-8"))
            self.assertEqual(data[1]["status"], "resumed")
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_resume_finds_by_slug(self):
        """With slug, should find matching entry."""
        entries = [
            {"slug": "rust-async", "status": "rate-limited", "topic": "Rust async",
             "mode": "research", "output_dir": "findings/rust-async",
             "threshold": 0.6, "iterations": 8, "budget": "moderate"},
            {"slug": "go-generics", "status": "max-iterations", "topic": "Go generics",
             "mode": "research", "output_dir": "findings/go-generics",
             "threshold": 0.4, "iterations": 30, "budget": "conservative"},
        ]
        tmpdir, hist_file = self._make_history(entries)
        try:
            with patch.object(history, "HISTORY_FILE", hist_file):
                import io, sys
                captured = io.StringIO()
                sys.stdout = captured
                history.cmd_resume(["rust-async", "|"])
                sys.stdout = sys.__stdout__
                output = captured.getvalue().strip()

            parts = output.split("|")
            self.assertEqual(parts[0], "Rust async")
            self.assertEqual(parts[2], "rust-async")
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_resume_exits_when_none_found(self):
        """Should exit(1) when no resumable session exists."""
        entries = [
            {"slug": "done", "status": "completed", "topic": "Done"},
        ]
        tmpdir, hist_file = self._make_history(entries)
        try:
            with patch.object(history, "HISTORY_FILE", hist_file):
                with self.assertRaises(SystemExit) as ctx:
                    history.cmd_resume(["|"])
                self.assertEqual(ctx.exception.code, 1)
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_resume_skips_completed_sessions(self):
        """Completed sessions should not be resumable."""
        entries = [
            {"slug": "a", "status": "completed", "topic": "A"},
            {"slug": "b", "status": "cancelled", "topic": "B", "mode": "research",
             "output_dir": "findings/b", "threshold": 0.6, "iterations": 3, "budget": "moderate"},
        ]
        tmpdir, hist_file = self._make_history(entries)
        try:
            with patch.object(history, "HISTORY_FILE", hist_file):
                import io, sys
                captured = io.StringIO()
                sys.stdout = captured
                history.cmd_resume(["|"])
                sys.stdout = sys.__stdout__
                output = captured.getvalue().strip()

            parts = output.split("|")
            self.assertEqual(parts[0], "B")
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_resume_skips_already_resumed(self):
        """Already-resumed sessions should not be resumable again."""
        entries = [
            {"slug": "a", "status": "resumed", "topic": "A"},
            {"slug": "b", "status": "rate-limited", "topic": "B", "mode": "research",
             "output_dir": "findings/b", "threshold": 0.6, "iterations": 5, "budget": "moderate"},
        ]
        tmpdir, hist_file = self._make_history(entries)
        try:
            with patch.object(history, "HISTORY_FILE", hist_file):
                import io, sys
                captured = io.StringIO()
                sys.stdout = captured
                history.cmd_resume(["|"])
                sys.stdout = sys.__stdout__
                output = captured.getvalue().strip()

            parts = output.split("|")
            self.assertEqual(parts[0], "B")
        finally:
            import shutil
            shutil.rmtree(tmpdir)


class TestResumedStatusIcon(unittest.TestCase):
    """Test that 'resumed' has a status icon."""

    def test_resumed_icon(self):
        self.assertEqual(history.status_icon("resumed"), "->")


class TestResumableStatuses(unittest.TestCase):
    """Test RESUMABLE_STATUSES constant."""

    def test_expected_statuses(self):
        self.assertIn("rate-limited", history.RESUMABLE_STATUSES)
        self.assertIn("max-iterations", history.RESUMABLE_STATUSES)
        self.assertIn("cancelled", history.RESUMABLE_STATUSES)
        self.assertIn("error", history.RESUMABLE_STATUSES)

    def test_non_resumable(self):
        self.assertNotIn("completed", history.RESUMABLE_STATUSES)
        self.assertNotIn("running", history.RESUMABLE_STATUSES)
        self.assertNotIn("resumed", history.RESUMABLE_STATUSES)


class TestResumeInSetupHelp(unittest.TestCase):
    """Test --resume is documented in setup script help text."""

    def setUp(self):
        self.setup_content = (PROJECT_ROOT / "scripts" / "setup-auto-explorer.sh").read_text(encoding="utf-8")

    def test_resume_in_help_options(self):
        self.assertIn("--resume", self.setup_content)

    def test_resume_examples(self):
        self.assertIn("/auto-explore --resume", self.setup_content)

    def test_resume_slug_example(self):
        self.assertIn("--resume rust-async", self.setup_content)


class TestResumeInExploreHelp(unittest.TestCase):
    """Test --resume is documented in /explore-help."""

    def setUp(self):
        self.help_content = (PROJECT_ROOT / ".claude" / "skills" / "explore-help" / "SKILL.md").read_text(encoding="utf-8")

    def test_resume_documented(self):
        self.assertIn("--resume", self.help_content)

    def test_resume_description(self):
        self.assertIn("Resume a previous session", self.help_content)


class TestResumeInStopHook(unittest.TestCase):
    """Test stop hook mentions --resume in end messages."""

    def setUp(self):
        self.hook_content = (PROJECT_ROOT / "hooks" / "stop-hook.sh").read_text(encoding="utf-8")

    def test_resume_hint_in_rate_limited_message(self):
        self.assertIn("--resume", self.hook_content)

    def test_resume_hint_format(self):
        self.assertIn("/auto-explore --resume $TOPIC_SLUG", self.hook_content)


if __name__ == "__main__":
    unittest.main()
