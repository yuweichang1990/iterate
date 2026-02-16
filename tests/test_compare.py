#!/usr/bin/env python
"""Tests for I-block: Compare Mode."""

import os
import unittest

from conftest import import_script, PROJECT_ROOT

helpers = import_script("helpers.py")

TEMPLATES_DIR = PROJECT_ROOT / "templates"


class TestComparisonTemplate(unittest.TestCase):
    """Test comparison template exists and has required structure."""

    def test_template_exists(self):
        tpl = helpers.load_template("comparison", str(TEMPLATES_DIR))
        self.assertEqual(tpl["name"], "comparison")

    def test_template_is_research_mode(self):
        tpl = helpers.load_template("comparison", str(TEMPLATES_DIR))
        self.assertEqual(tpl["mode"], "research")

    def test_template_has_phases(self):
        tpl = helpers.load_template("comparison", str(TEMPLATES_DIR))
        self.assertIn("Phase 1", tpl["body"])
        self.assertIn("Phase 2", tpl["body"])
        self.assertIn("Phase 3", tpl["body"])
        self.assertIn("Phase 4", tpl["body"])

    def test_template_has_evaluation_criteria(self):
        tpl = helpers.load_template("comparison", str(TEMPLATES_DIR))
        self.assertIn("evaluation criteria", tpl["body"].lower())

    def test_template_has_recommendation(self):
        tpl = helpers.load_template("comparison", str(TEMPLATES_DIR))
        self.assertIn("recommendation", tpl["body"].lower())

    def test_template_has_placeholders(self):
        tpl = helpers.load_template("comparison", str(TEMPLATES_DIR))
        self.assertIn("{{TOPIC}}", tpl["body"])
        self.assertIn("{{OUTPUT_DIR}}", tpl["body"])

    def test_template_has_explore_next_tag(self):
        tpl = helpers.load_template("comparison", str(TEMPLATES_DIR))
        self.assertIn("<explore-next>", tpl["body"])

    def test_template_in_list(self):
        templates = helpers.list_templates(str(TEMPLATES_DIR))
        names = [t["name"] for t in templates]
        self.assertIn("comparison", names)


class TestCompareFlag(unittest.TestCase):
    """Test --compare flag in setup script."""

    def test_compare_flag_in_help(self):
        setup_path = PROJECT_ROOT / "scripts" / "setup-auto-explorer.sh"
        content = setup_path.read_text(encoding="utf-8")
        self.assertIn("--compare", content)

    def test_compare_sets_template(self):
        """--compare should set TEMPLATE_NAME to 'comparison'."""
        setup_path = PROJECT_ROOT / "scripts" / "setup-auto-explorer.sh"
        content = setup_path.read_text(encoding="utf-8")
        self.assertIn('TEMPLATE_NAME="comparison"', content)

    def test_compare_example_in_help(self):
        setup_path = PROJECT_ROOT / "scripts" / "setup-auto-explorer.sh"
        content = setup_path.read_text(encoding="utf-8")
        self.assertIn("--compare React vs Vue", content)


class TestCompareInExploreHelp(unittest.TestCase):
    """Test --compare in /explore-help documentation."""

    def test_compare_documented(self):
        help_path = PROJECT_ROOT / ".claude" / "skills" / "explore-help" / "SKILL.md"
        content = help_path.read_text(encoding="utf-8")
        self.assertIn("--compare", content)

    def test_compare_example(self):
        help_path = PROJECT_ROOT / ".claude" / "skills" / "explore-help" / "SKILL.md"
        content = help_path.read_text(encoding="utf-8")
        self.assertIn("--compare React vs Vue", content)


class TestCompareInScenarios(unittest.TestCase):
    """Test compare mode in SCENARIOS.md."""

    def test_compare_in_current_features(self):
        scenarios_path = PROJECT_ROOT / "SCENARIOS.md"
        content = scenarios_path.read_text(encoding="utf-8")
        future_idx = content.find("Future Directions")
        compare_idx = content.find("Compare mode")
        self.assertGreater(compare_idx, -1, "Compare mode section not found")
        self.assertLess(compare_idx, future_idx, "Compare mode should be before Future Directions")

    def test_compare_not_in_future(self):
        scenarios_path = PROJECT_ROOT / "SCENARIOS.md"
        content = scenarios_path.read_text(encoding="utf-8")
        future_idx = content.find("Future Directions")
        future_section = content[future_idx:]
        self.assertNotIn("Compare Mode", future_section)


if __name__ == "__main__":
    unittest.main()
