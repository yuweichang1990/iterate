#!/usr/bin/env python
"""Tests for G-block: Exploration Templates."""

import os
import tempfile
import unittest

from conftest import import_script, PROJECT_ROOT

helpers = import_script("helpers.py")

TEMPLATES_DIR = PROJECT_ROOT / "templates"


class TestLoadTemplate(unittest.TestCase):
    """Test loading templates from files."""

    def test_load_existing_template(self):
        tpl = helpers.load_template("deep-dive", str(TEMPLATES_DIR))
        self.assertEqual(tpl["name"], "deep-dive")
        self.assertIn("research", tpl["mode"])
        self.assertIn("{{TOPIC}}", tpl["body"])
        self.assertIn("{{OUTPUT_DIR}}", tpl["body"])

    def test_load_with_md_extension(self):
        tpl = helpers.load_template("deep-dive.md", str(TEMPLATES_DIR))
        self.assertEqual(tpl["name"], "deep-dive")

    def test_load_nonexistent_template(self):
        with self.assertRaises(FileNotFoundError):
            helpers.load_template("nonexistent", str(TEMPLATES_DIR))

    def test_load_from_nonexistent_dir(self):
        with self.assertRaises(FileNotFoundError):
            helpers.load_template("deep-dive", "/nonexistent/dir")

    def test_template_has_body(self):
        tpl = helpers.load_template("deep-dive", str(TEMPLATES_DIR))
        self.assertTrue(len(tpl["body"]) > 50)

    def test_template_body_excludes_frontmatter(self):
        tpl = helpers.load_template("deep-dive", str(TEMPLATES_DIR))
        self.assertNotIn("---", tpl["body"][:10])
        self.assertNotIn("name:", tpl["body"][:20])

    def test_custom_template_file(self):
        """Load a template from a custom temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tpl_path = os.path.join(tmpdir, "custom.md")
            with open(tpl_path, "w", encoding="utf-8") as f:
                f.write("---\nname: custom\ndescription: A custom template\nmode: build\n---\n\nCustom body: {{TOPIC}}\n")
            tpl = helpers.load_template("custom", tmpdir)
            self.assertEqual(tpl["name"], "custom")
            self.assertEqual(tpl["mode"], "build")
            self.assertIn("Custom body", tpl["body"])


class TestListTemplates(unittest.TestCase):
    """Test listing available templates."""

    def test_lists_builtin_templates(self):
        templates = helpers.list_templates(str(TEMPLATES_DIR))
        names = [t["name"] for t in templates]
        self.assertIn("deep-dive", names)
        self.assertIn("quickstart", names)
        self.assertIn("architecture-review", names)
        self.assertIn("security-audit", names)

    def test_each_template_has_description(self):
        templates = helpers.list_templates(str(TEMPLATES_DIR))
        for tpl in templates:
            self.assertTrue(len(tpl["description"]) > 10, f"Template {tpl['name']} has empty/short description")

    def test_each_template_has_mode(self):
        templates = helpers.list_templates(str(TEMPLATES_DIR))
        for tpl in templates:
            self.assertIn(tpl["mode"], ("research", "build"), f"Template {tpl['name']} has invalid mode: {tpl['mode']}")

    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            templates = helpers.list_templates(tmpdir)
            self.assertEqual(templates, [])

    def test_nonexistent_dir(self):
        templates = helpers.list_templates("/nonexistent/dir")
        self.assertEqual(templates, [])


class TestBuiltinTemplateContent(unittest.TestCase):
    """Test that all built-in templates have required structure."""

    def _load_all(self):
        templates = []
        for name in ("deep-dive", "quickstart", "architecture-review", "security-audit", "comparison", "dual-lens"):
            tpl = helpers.load_template(name, str(TEMPLATES_DIR))
            templates.append(tpl)
        return templates

    def test_all_have_topic_placeholder(self):
        for tpl in self._load_all():
            self.assertIn("{{TOPIC}}", tpl["body"], f"{tpl['name']} missing {{{{TOPIC}}}}")

    def test_all_have_output_dir_placeholder(self):
        for tpl in self._load_all():
            self.assertIn("{{OUTPUT_DIR}}", tpl["body"], f"{tpl['name']} missing {{{{OUTPUT_DIR}}}}")

    def test_all_have_explore_next_tag(self):
        for tpl in self._load_all():
            self.assertIn("<explore-next>", tpl["body"], f"{tpl['name']} missing <explore-next> tag")

    def test_all_research_mode(self):
        """All built-in templates should be research mode."""
        for tpl in self._load_all():
            self.assertEqual(tpl["mode"], "research", f"{tpl['name']} should be research mode")


class TestTemplateInSetupHelp(unittest.TestCase):
    """Test that --template is documented in setup script help."""

    def test_template_in_help_options(self):
        setup_path = PROJECT_ROOT / "scripts" / "setup-auto-explorer.sh"
        content = setup_path.read_text(encoding="utf-8")
        self.assertIn("--template", content)

    def test_template_examples(self):
        setup_path = PROJECT_ROOT / "scripts" / "setup-auto-explorer.sh"
        content = setup_path.read_text(encoding="utf-8")
        self.assertIn("--template deep-dive", content)
        self.assertIn("--template quickstart", content)


class TestTemplateInExploreHelp(unittest.TestCase):
    """Test that --template is documented in /explore-help."""

    def test_template_documented(self):
        help_path = PROJECT_ROOT / ".claude" / "skills" / "explore-help" / "SKILL.md"
        content = help_path.read_text(encoding="utf-8")
        self.assertIn("--template", content)

    def test_template_names_listed(self):
        help_path = PROJECT_ROOT / ".claude" / "skills" / "explore-help" / "SKILL.md"
        content = help_path.read_text(encoding="utf-8")
        self.assertIn("deep-dive", content)
        self.assertIn("quickstart", content)
        self.assertIn("architecture-review", content)
        self.assertIn("security-audit", content)


class TestTemplateInScenarios(unittest.TestCase):
    """Test that templates are documented in SCENARIOS.md."""

    def test_templates_in_current_features(self):
        scenarios_path = PROJECT_ROOT / "SCENARIOS.md"
        content = scenarios_path.read_text(encoding="utf-8")
        # Templates should be in current features section (before "Future Directions")
        future_idx = content.find("Future Directions")
        templates_idx = content.find("Exploration templates")
        self.assertGreater(templates_idx, -1, "Templates section not found")
        self.assertLess(templates_idx, future_idx, "Templates section should be before Future Directions")

    def test_templates_not_in_future(self):
        scenarios_path = PROJECT_ROOT / "SCENARIOS.md"
        content = scenarios_path.read_text(encoding="utf-8")
        future_idx = content.find("Future Directions")
        future_section = content[future_idx:]
        # Exploration Templates should NOT be in Future Directions anymore
        self.assertNotIn("Exploration Templates", future_section)


if __name__ == "__main__":
    unittest.main()
