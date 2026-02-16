#!/usr/bin/env python
"""
Tests that validate version numbers are consistent across all locations.

Auto-Explorer stores its version in 3 locations:
  1. .claude-plugin/plugin.json (source of truth)
  2. .claude-plugin/marketplace.json (metadata.version)
  3. .claude-plugin/marketplace.json (plugins[0].version)

All must match. CHANGELOG.md should have an entry for the current version.
"""

import json
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


class TestVersionConsistency(unittest.TestCase):
    """All version locations must match plugin.json."""

    def setUp(self):
        with open(PROJECT_ROOT / ".claude-plugin" / "plugin.json", encoding="utf-8") as f:
            self.plugin = json.load(f)
        self.version = self.plugin["version"]

    def test_plugin_json_has_version(self):
        self.assertRegex(self.version, r"^\d+\.\d+\.\d+$", "Version must be semver")

    def test_marketplace_metadata_version(self):
        with open(PROJECT_ROOT / ".claude-plugin" / "marketplace.json", encoding="utf-8") as f:
            marketplace = json.load(f)
        self.assertEqual(
            marketplace["metadata"]["version"],
            self.version,
            "marketplace.json metadata.version doesn't match plugin.json",
        )

    def test_marketplace_plugin_version(self):
        with open(PROJECT_ROOT / ".claude-plugin" / "marketplace.json", encoding="utf-8") as f:
            marketplace = json.load(f)
        plugin_entry = marketplace["plugins"][0]
        self.assertEqual(
            plugin_entry["version"],
            self.version,
            "marketplace.json plugins[0].version doesn't match plugin.json",
        )

    def test_changelog_has_version_entry(self):
        changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        pattern = rf"## \[{re.escape(self.version)}\]"
        self.assertRegex(
            changelog,
            pattern,
            f"CHANGELOG.md missing entry for version {self.version}",
        )


if __name__ == "__main__":
    unittest.main()
