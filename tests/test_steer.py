#!/usr/bin/env python
"""
Tests for the interactive steering feature.

Covers: steer file creation, consumption in stop hook, prompt injection,
        and .gitignore entry.
"""

import os
import unittest
from pathlib import Path

from conftest import PROJECT_ROOT


class TestSteerFileGitignore(unittest.TestCase):
    """Verify steer file is in .gitignore."""

    def test_steer_file_in_gitignore(self):
        gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".claude/auto-explorer-steer.md", gitignore)


class TestSteerInStopHook(unittest.TestCase):
    """Verify stop hook has steer file handling logic."""

    def setUp(self):
        self.hook_content = (PROJECT_ROOT / "hooks" / "stop-hook.sh").read_text(encoding="utf-8")

    def test_steer_file_variable_defined(self):
        self.assertIn('STEER_FILE=".claude/auto-explorer-steer.md"', self.hook_content)

    def test_steer_file_is_read(self):
        self.assertIn('cat "$STEER_FILE"', self.hook_content)

    def test_steer_file_is_consumed(self):
        """Steer file should be deleted after reading (one-time directive)."""
        self.assertIn('rm -f "$STEER_FILE"', self.hook_content)

    def test_steer_injected_into_build_prompt(self):
        self.assertIn("USER DIRECTION CHANGE", self.hook_content)

    def test_steer_injected_into_research_prompt(self):
        # Both build and research branches should have the injection
        lines = self.hook_content.split("\n")
        direction_lines = [l for l in lines if "USER DIRECTION CHANGE" in l]
        self.assertGreaterEqual(len(direction_lines), 2, "Both build and research prompts should inject steer message")

    def test_steer_indicator_in_system_message(self):
        self.assertIn("STEERED by user", self.hook_content)


class TestSteerSkill(unittest.TestCase):
    """Verify /explore-steer skill file exists and is configured."""

    def test_skill_file_exists(self):
        skill_path = PROJECT_ROOT / ".claude" / "skills" / "explore-steer" / "SKILL.md"
        self.assertTrue(skill_path.exists(), f"Skill file not found: {skill_path}")

    def test_skill_has_description(self):
        content = (PROJECT_ROOT / ".claude" / "skills" / "explore-steer" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("description:", content)

    def test_skill_writes_steer_file(self):
        content = (PROJECT_ROOT / ".claude" / "skills" / "explore-steer" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("auto-explorer-steer.md", content)

    def test_skill_registered_in_plugin_json(self):
        import json
        plugin = json.loads((PROJECT_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        skills = plugin.get("skills", [])
        steer_skills = [s for s in skills if "explore-steer" in s]
        self.assertEqual(len(steer_skills), 1, "explore-steer should be registered in plugin.json")


class TestSteerInHelp(unittest.TestCase):
    """Verify /explore-steer is documented in help."""

    def test_steer_in_explore_help(self):
        help_content = (PROJECT_ROOT / ".claude" / "skills" / "explore-help" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("/explore-steer", help_content)

    def test_steer_examples_in_help(self):
        help_content = (PROJECT_ROOT / ".claude" / "skills" / "explore-help" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Focus more on practical examples", help_content)


if __name__ == "__main__":
    unittest.main()
