#!/usr/bin/env python
"""
Tests for the auto-export summary feature.

Validates that the summary-pending flag file path is consistent across
stop-hook.sh, cancel-explore/SKILL.md, and .gitignore. Also verifies
the stop-hook has both the flag check and flag creation code paths.
"""

import unittest

from conftest import PROJECT_ROOT

SUMMARY_FLAG_PATH = ".claude/auto-explorer-summary-pending"


class TestAutoExportConsistency(unittest.TestCase):
    """Verify the summary-pending flag file is referenced consistently."""

    def test_stop_hook_has_flag_definition(self):
        """stop-hook.sh must define SUMMARY_FLAG with the correct path."""
        content = (PROJECT_ROOT / "hooks" / "stop-hook.sh").read_text(encoding="utf-8")
        self.assertIn(f'SUMMARY_FLAG="{SUMMARY_FLAG_PATH}"', content)

    def test_stop_hook_has_flag_check(self):
        """stop-hook.sh must check for the flag file early (before max-iterations)."""
        content = (PROJECT_ROOT / "hooks" / "stop-hook.sh").read_text(encoding="utf-8")
        lines = content.split("\n")
        flag_check_line = None
        max_iter_line = None
        for i, line in enumerate(lines):
            if "if [[ -f \"$SUMMARY_FLAG\" ]]" in line and flag_check_line is None:
                flag_check_line = i
            if "MAX_ITERATIONS" in line and "-ge" in line and max_iter_line is None:
                max_iter_line = i
        self.assertIsNotNone(flag_check_line, "SUMMARY_FLAG check not found in stop-hook.sh")
        self.assertIsNotNone(max_iter_line, "MAX_ITERATIONS check not found in stop-hook.sh")
        self.assertLess(flag_check_line, max_iter_line,
                        "SUMMARY_FLAG check must come before MAX_ITERATIONS check")

    def test_stop_hook_creates_flag_on_explore_done(self):
        """stop-hook.sh must create the flag file when <explore-done> is detected."""
        content = (PROJECT_ROOT / "hooks" / "stop-hook.sh").read_text(encoding="utf-8")
        self.assertIn('echo "$EXPLORE_DONE" > "$SUMMARY_FLAG"', content)

    def test_stop_hook_cleans_up_flag(self):
        """stop-hook.sh must remove both STATE_FILE and SUMMARY_FLAG on completion."""
        content = (PROJECT_ROOT / "hooks" / "stop-hook.sh").read_text(encoding="utf-8")
        self.assertIn('rm -f "$STATE_FILE" "$SUMMARY_FLAG"', content)

    def test_cancel_explore_cleans_flag(self):
        """cancel-explore SKILL.md must clean up the summary-pending flag."""
        skill_path = PROJECT_ROOT / ".claude" / "skills" / "cancel-explore" / "SKILL.md"
        content = skill_path.read_text(encoding="utf-8")
        self.assertIn("auto-explorer-summary-pending", content)

    def test_gitignore_includes_flag(self):
        """.gitignore must ignore the summary-pending flag file."""
        content = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("auto-explorer-summary-pending", content)


class TestAutoExportPrompts(unittest.TestCase):
    """Verify the summary prompts are mode-aware."""

    def test_build_summary_prompt_exists(self):
        """stop-hook.sh must have a build-mode summary prompt."""
        content = (PROJECT_ROOT / "hooks" / "stop-hook.sh").read_text(encoding="utf-8")
        self.assertIn("Architecture", content)
        self.assertIn("Deliverables", content)
        self.assertIn("How to use", content)

    def test_research_summary_prompt_exists(self):
        """stop-hook.sh must have a research-mode summary prompt."""
        content = (PROJECT_ROOT / "hooks" / "stop-hook.sh").read_text(encoding="utf-8")
        self.assertIn("Executive summary", content)
        self.assertIn("Open questions", content)
        self.assertIn("Recommended next steps", content)

    def test_summary_prompt_says_no_tags(self):
        """Summary prompt must tell Claude not to emit explore tags."""
        content = (PROJECT_ROOT / "hooks" / "stop-hook.sh").read_text(encoding="utf-8")
        self.assertIn("Do NOT include <explore-next> or <explore-done>", content)


if __name__ == "__main__":
    unittest.main()
