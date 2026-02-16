#!/usr/bin/env python
"""Tests for dual-lens exploration template and graph-brief generation."""

import unittest

from conftest import import_script, PROJECT_ROOT

helpers = import_script("helpers.py")
interest_graph = import_script("interest_graph.py")

TEMPLATES_DIR = PROJECT_ROOT / "templates"


class TestDualLensTemplate(unittest.TestCase):
    """Test that the dual-lens template loads and has required structure."""

    def setUp(self):
        self.tpl = helpers.load_template("dual-lens", str(TEMPLATES_DIR))

    def test_loads_correctly(self):
        self.assertEqual(self.tpl["name"], "dual-lens")
        self.assertEqual(self.tpl["mode"], "research")

    def test_has_topic_placeholder(self):
        self.assertIn("{{TOPIC}}", self.tpl["body"])

    def test_has_output_dir_placeholder(self):
        self.assertIn("{{OUTPUT_DIR}}", self.tpl["body"])

    def test_has_graph_brief_placeholder(self):
        self.assertIn("{{GRAPH_BRIEF}}", self.tpl["body"])

    def test_has_phase_structure(self):
        body = self.tpl["body"]
        self.assertIn("Phase 1", body)
        self.assertIn("Phase 2", body)
        self.assertIn("Phase 3", body)
        self.assertIn("Phase 4", body)

    def test_has_system_a_and_b(self):
        body = self.tpl["body"]
        self.assertIn("System A", body)
        self.assertIn("System B", body)

    def test_has_synthesis_gates(self):
        body = self.tpl["body"]
        self.assertIn("Gate 1", body)
        self.assertIn("Applicability", body)
        self.assertIn("Gate 2", body)
        self.assertIn("Feasibility", body)
        self.assertIn("DISCARD", body)

    def test_has_evidence_and_risk_instructions(self):
        body = self.tpl["body"]
        self.assertIn("Evidence Requirement", body)
        self.assertIn("Risk Assessment", body)
        self.assertIn("failure mode", body.lower())

    def test_system_b_ignores_graph(self):
        body = self.tpl["body"]
        self.assertIn("deliberately ignores", body)
        self.assertIn("no prior knowledge graph", body)

    def test_has_explore_next_tag(self):
        self.assertIn("<explore-next>", self.tpl["body"])


class TestGraphBrief(unittest.TestCase):
    """Test generate_brief() function."""

    def _make_graph(self, concepts=None, edges=None):
        graph = interest_graph._empty_graph()
        if concepts:
            graph["concepts"] = concepts
        if edges:
            graph["edges"] = edges
        return graph

    def test_empty_graph_fallback(self):
        graph = self._make_graph()
        brief = interest_graph.generate_brief(graph)
        self.assertEqual(brief, "(No interest graph data available)")

    def test_concepts_listed(self):
        graph = self._make_graph(concepts={
            "python": {
                "labels": {"en": "Python"},
                "category": "programming",
                "weight": 5.0,
                "lastSeen": "2026-02-17",
                "sessionCount": 3,
                "broader": [], "narrower": [], "related": [],
                "bandit": {"alpha": 1, "beta": 1},
            },
        })
        brief = interest_graph.generate_brief(graph)
        self.assertIn("Top Concepts:", brief)
        self.assertIn("Python", brief)
        self.assertIn("programming", brief)

    def test_max_concepts_limit(self):
        concepts = {}
        for i in range(20):
            concepts[f"topic-{i}"] = {
                "labels": {"en": f"Topic {i}"},
                "category": "general",
                "weight": float(20 - i),
                "lastSeen": "2026-02-17",
                "sessionCount": 1,
                "broader": [], "narrower": [], "related": [],
                "bandit": {"alpha": 1, "beta": 1},
            }
        graph = self._make_graph(concepts=concepts)
        brief = interest_graph.generate_brief(graph, max_concepts=5)
        # Should only have 5 concept lines
        concept_lines = [l for l in brief.split("\n") if l.startswith("  - ") and "weight:" in l]
        self.assertEqual(len(concept_lines), 5)

    def test_communities_included(self):
        concepts = {
            "docker": {
                "labels": {"en": "Docker"}, "category": "devops",
                "weight": 3.0, "lastSeen": "2026-02-17", "sessionCount": 2,
                "broader": [], "narrower": [], "related": [],
                "bandit": {"alpha": 1, "beta": 1},
            },
            "kubernetes": {
                "labels": {"en": "Kubernetes"}, "category": "devops",
                "weight": 3.0, "lastSeen": "2026-02-17", "sessionCount": 2,
                "broader": [], "narrower": [], "related": [],
                "bandit": {"alpha": 1, "beta": 1},
            },
        }
        edges = [{"src": "docker", "tgt": "kubernetes", "w": 3, "lastSeen": "2026-02-17"}]
        graph = self._make_graph(concepts=concepts, edges=edges)
        brief = interest_graph.generate_brief(graph)
        self.assertIn("Top Concepts:", brief)
        # Communities may or may not appear depending on label propagation result
        # but the function should not error

    def test_gaps_included(self):
        # Create a graph with structural gaps: A-C connected, B-C connected, but A-B not
        concepts = {}
        for name in ("a", "b", "c"):
            concepts[name] = {
                "labels": {"en": name.upper()}, "category": "general",
                "weight": 2.0, "lastSeen": "2026-02-17", "sessionCount": 1,
                "broader": [], "narrower": [], "related": [],
                "bandit": {"alpha": 1, "beta": 1},
            }
        # a-c and b-c connected, a-b not → gap
        # Need at least 2 shared neighbors for gap detection
        for name in ("d", "e"):
            concepts[name] = {
                "labels": {"en": name.upper()}, "category": "general",
                "weight": 1.0, "lastSeen": "2026-02-17", "sessionCount": 1,
                "broader": [], "narrower": [], "related": [],
                "bandit": {"alpha": 1, "beta": 1},
            }
        edges = [
            {"src": "a", "tgt": "d", "w": 1, "lastSeen": "2026-02-17"},
            {"src": "a", "tgt": "e", "w": 1, "lastSeen": "2026-02-17"},
            {"src": "b", "tgt": "d", "w": 1, "lastSeen": "2026-02-17"},
            {"src": "b", "tgt": "e", "w": 1, "lastSeen": "2026-02-17"},
        ]
        graph = self._make_graph(concepts=concepts, edges=edges)
        brief = interest_graph.generate_brief(graph)
        self.assertIn("Structural Gaps:", brief)
        self.assertIn("a", brief)
        self.assertIn("b", brief)

    def test_multiple_gaps_all_listed(self):
        """Regression: all gaps must appear, not just the last one (indentation bug)."""
        concepts = {}
        for name in ("x", "y", "z", "s1", "s2"):
            concepts[name] = {
                "labels": {"en": name.upper()}, "category": "general",
                "weight": 2.0, "lastSeen": "2026-02-17", "sessionCount": 1,
                "broader": [], "narrower": [], "related": [],
                "bandit": {"alpha": 1, "beta": 1},
            }
        # x and y share neighbors s1, s2 but aren't connected → gap 1
        # x and z share neighbors s1, s2 but aren't connected → gap 2
        edges = [
            {"src": "x", "tgt": "s1", "w": 1, "lastSeen": "2026-02-17"},
            {"src": "x", "tgt": "s2", "w": 1, "lastSeen": "2026-02-17"},
            {"src": "y", "tgt": "s1", "w": 1, "lastSeen": "2026-02-17"},
            {"src": "y", "tgt": "s2", "w": 1, "lastSeen": "2026-02-17"},
            {"src": "z", "tgt": "s1", "w": 1, "lastSeen": "2026-02-17"},
            {"src": "z", "tgt": "s2", "w": 1, "lastSeen": "2026-02-17"},
        ]
        graph = self._make_graph(concepts=concepts, edges=edges)
        brief = interest_graph.generate_brief(graph, max_gaps=5)
        gap_lines = [l for l in brief.split("\n") if "<->" in l]
        # There should be at least 2 gap lines (x<->y, x<->z, y<->z)
        self.assertGreaterEqual(len(gap_lines), 2,
            f"Expected multiple gap lines, got {len(gap_lines)}: {gap_lines}")


if __name__ == "__main__":
    unittest.main()
