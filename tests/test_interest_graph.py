#!/usr/bin/env python
"""Tests for interest_graph.py"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Import via conftest pattern
sys.path.insert(0, str(Path(__file__).parent))
from conftest import import_script

ig = import_script("interest_graph.py")


class TestLoadSave(unittest.TestCase):
    """Test load and save operations."""

    def test_load_returns_empty_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_graph = Path(tmpdir) / "interest-graph.json"
            fake_md = Path(tmpdir) / "user-interests.md"
            with mock.patch.object(ig, "GRAPH_FILE", fake_graph), \
                 mock.patch.object(ig, "MD_FILE", fake_md):
                graph = ig.load_graph()
        self.assertEqual(graph["version"], 1)
        self.assertEqual(graph["concepts"], {})
        self.assertEqual(graph["edges"], [])
        self.assertEqual(graph["meta"]["totalSessions"], 0)

    def test_load_reads_existing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_graph = Path(tmpdir) / "interest-graph.json"
            data = ig._empty_graph()
            data["concepts"]["python"] = {
                "labels": {"en": "Python"}, "category": "programming",
                "weight": 5.0, "lastSeen": "2026-02-16", "sessionCount": 3,
                "broader": [], "narrower": [], "related": [],
                "bandit": {"alpha": 2, "beta": 1},
            }
            fake_graph.write_text(json.dumps(data), encoding="utf-8")
            with mock.patch.object(ig, "GRAPH_FILE", fake_graph):
                graph = ig.load_graph()
        self.assertIn("python", graph["concepts"])
        self.assertEqual(graph["concepts"]["python"]["weight"], 5.0)

    def test_save_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_graph = Path(tmpdir) / "subdir" / "interest-graph.json"
            with mock.patch.object(ig, "GRAPH_FILE", fake_graph):
                graph = ig._empty_graph()
                ig.save_graph(graph)
            self.assertTrue(fake_graph.exists())
            saved = json.loads(fake_graph.read_text(encoding="utf-8"))
            self.assertEqual(saved["version"], 1)
            self.assertIn("lastUpdated", saved["meta"])

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_graph = Path(tmpdir) / "interest-graph.json"
            with mock.patch.object(ig, "GRAPH_FILE", fake_graph):
                graph = ig._empty_graph()
                graph["concepts"]["test"] = {
                    "labels": {"en": "Test"}, "category": "general",
                    "weight": 2.0, "lastSeen": "2026-02-16", "sessionCount": 1,
                    "broader": [], "narrower": [], "related": ["foo"],
                    "bandit": {"alpha": 1, "beta": 1},
                }
                ig.save_graph(graph)
                loaded = ig.load_graph()
        self.assertEqual(loaded["concepts"]["test"]["weight"], 2.0)
        self.assertEqual(loaded["concepts"]["test"]["related"], ["foo"])


class TestAddConcepts(unittest.TestCase):
    """Test concept addition and updates."""

    def test_add_new_concept(self):
        graph = ig._empty_graph()
        ig.add_concepts(graph, [{"id": "docker", "labels": {"en": "Docker"}, "category": "infrastructure"}])
        self.assertIn("docker", graph["concepts"])
        self.assertEqual(graph["concepts"]["docker"]["weight"], 1.0)
        self.assertEqual(graph["concepts"]["docker"]["sessionCount"], 1)
        self.assertEqual(graph["concepts"]["docker"]["bandit"], {"alpha": 1, "beta": 1})

    def test_update_existing_concept(self):
        graph = ig._empty_graph()
        graph["concepts"]["docker"] = {
            "labels": {"en": "Docker"}, "category": "infrastructure",
            "weight": 3.0, "lastSeen": "2026-02-10", "sessionCount": 2,
            "broader": ["infra"], "narrower": [], "related": ["k8s"],
            "bandit": {"alpha": 2, "beta": 1},
        }
        ig.add_concepts(graph, [{"id": "docker", "labels": {"en": "Docker"}, "category": "infrastructure"}])
        self.assertEqual(graph["concepts"]["docker"]["weight"], 4.0)
        self.assertEqual(graph["concepts"]["docker"]["sessionCount"], 3)

    def test_merge_relations(self):
        graph = ig._empty_graph()
        graph["concepts"]["docker"] = {
            "labels": {"en": "Docker"}, "category": "infrastructure",
            "weight": 1.0, "lastSeen": "2026-02-10", "sessionCount": 1,
            "broader": ["infra"], "narrower": [], "related": ["k8s"],
            "bandit": {"alpha": 1, "beta": 1},
        }
        ig.add_concepts(graph, [{
            "id": "docker",
            "related": ["ci-cd", "k8s"],
            "broader": ["containers"],
        }])
        self.assertIn("ci-cd", graph["concepts"]["docker"]["related"])
        self.assertIn("k8s", graph["concepts"]["docker"]["related"])
        self.assertIn("containers", graph["concepts"]["docker"]["broader"])
        self.assertIn("infra", graph["concepts"]["docker"]["broader"])

    def test_multilingual_labels(self):
        graph = ig._empty_graph()
        ig.add_concepts(graph, [{"id": "docker", "labels": {"en": "Docker", "zh": "Docker"}}])
        self.assertEqual(graph["concepts"]["docker"]["labels"]["zh"], "Docker")

    def test_default_category(self):
        graph = ig._empty_graph()
        ig.add_concepts(graph, [{"id": "misc"}])
        self.assertEqual(graph["concepts"]["misc"]["category"], "general")

    def test_add_multiple_concepts(self):
        graph = ig._empty_graph()
        ig.add_concepts(graph, [
            {"id": "python", "category": "programming"},
            {"id": "rust", "category": "programming"},
            {"id": "docker", "category": "infrastructure"},
        ])
        self.assertEqual(len(graph["concepts"]), 3)
        self.assertIn("python", graph["concepts"])
        self.assertIn("rust", graph["concepts"])
        self.assertIn("docker", graph["concepts"])


class TestCooccurrence(unittest.TestCase):
    """Test co-occurrence edge recording."""

    def test_new_edges(self):
        graph = ig._empty_graph()
        ig.record_cooccurrences(graph, ["python", "docker", "ci-cd"])
        self.assertEqual(len(graph["edges"]), 3)  # C(3,2) = 3

    def test_increment_existing_edge(self):
        graph = ig._empty_graph()
        graph["edges"] = [{"src": "ci-cd", "tgt": "docker", "w": 2, "lastSeen": "2026-02-10"}]
        ig.record_cooccurrences(graph, ["docker", "ci-cd"])
        self.assertEqual(len(graph["edges"]), 1)
        self.assertEqual(graph["edges"][0]["w"], 3)

    def test_symmetric_keys(self):
        graph = ig._empty_graph()
        ig.record_cooccurrences(graph, ["b", "a"])
        self.assertEqual(graph["edges"][0]["src"], "a")
        self.assertEqual(graph["edges"][0]["tgt"], "b")

    def test_dedup_keywords(self):
        graph = ig._empty_graph()
        ig.record_cooccurrences(graph, ["python", "python", "docker"])
        self.assertEqual(len(graph["edges"]), 1)  # Only one unique pair

    def test_single_keyword_no_edges(self):
        graph = ig._empty_graph()
        ig.record_cooccurrences(graph, ["python"])
        self.assertEqual(len(graph["edges"]), 0)


class TestDecay(unittest.TestCase):
    """Test half-life decay application."""

    def test_decay_reduces_weight(self):
        graph = ig._empty_graph()
        graph["concepts"]["old"] = {
            "labels": {"en": "Old"}, "category": "general",
            "weight": 8.0, "lastSeen": "2026-01-01", "sessionCount": 5,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 1, "beta": 1},
        }
        ig.apply_decay(graph)
        self.assertLess(graph["concepts"]["old"]["weight"], 8.0)

    def test_recent_concept_no_decay(self):
        graph = ig._empty_graph()
        today = ig.datetime.now().strftime("%Y-%m-%d")
        graph["concepts"]["fresh"] = {
            "labels": {"en": "Fresh"}, "category": "general",
            "weight": 5.0, "lastSeen": today, "sessionCount": 2,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 1, "beta": 1},
        }
        ig.apply_decay(graph)
        self.assertEqual(graph["concepts"]["fresh"]["weight"], 5.0)

    def test_prune_dead_concepts(self):
        graph = ig._empty_graph()
        graph["concepts"]["dead"] = {
            "labels": {"en": "Dead"}, "category": "general",
            "weight": 0.005, "lastSeen": "2024-01-01", "sessionCount": 1,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 1, "beta": 1},
        }
        graph["edges"] = [{"src": "dead", "tgt": "other", "w": 1, "lastSeen": "2024-01-01"}]
        ig.apply_decay(graph)
        self.assertNotIn("dead", graph["concepts"])
        self.assertEqual(len(graph["edges"]), 0)

    def test_high_session_count_not_pruned(self):
        graph = ig._empty_graph()
        graph["concepts"]["veteran"] = {
            "labels": {"en": "Veteran"}, "category": "general",
            "weight": 0.005, "lastSeen": "2024-01-01", "sessionCount": 5,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 3, "beta": 1},
        }
        ig.apply_decay(graph)
        self.assertIn("veteran", graph["concepts"])

    def test_missing_last_seen_skipped(self):
        graph = ig._empty_graph()
        graph["concepts"]["nodate"] = {
            "labels": {"en": "No Date"}, "category": "general",
            "weight": 3.0, "lastSeen": "", "sessionCount": 1,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 1, "beta": 1},
        }
        ig.apply_decay(graph)
        self.assertEqual(graph["concepts"]["nodate"]["weight"], 3.0)


class TestThompsonSampling(unittest.TestCase):
    """Test Thompson Sampling suggestions."""

    def test_deterministic_with_seed(self):
        graph = ig._empty_graph()
        today = ig.datetime.now().strftime("%Y-%m-%d")
        for cid in ("a", "b", "c"):
            graph["concepts"][cid] = {
                "labels": {"en": cid.upper()}, "category": "general",
                "weight": 5.0, "lastSeen": today, "sessionCount": 3,
                "broader": [], "narrower": [], "related": [],
                "bandit": {"alpha": 2, "beta": 1},
            }
        r1 = ig.suggest_topics(graph, n=3, seed=42)
        r2 = ig.suggest_topics(graph, n=3, seed=42)
        self.assertEqual([x[0] for x in r1], [x[0] for x in r2])

    def test_recency_filter(self):
        graph = ig._empty_graph()
        today = ig.datetime.now().strftime("%Y-%m-%d")
        for cid in ("a", "b"):
            graph["concepts"][cid] = {
                "labels": {"en": cid}, "category": "general",
                "weight": 5.0, "lastSeen": today, "sessionCount": 3,
                "broader": [], "narrower": [], "related": [],
                "bandit": {"alpha": 2, "beta": 1},
            }
        results = ig.suggest_topics(graph, n=5, recent_sessions=["a"], seed=42)
        ids = [r[0] for r in results]
        self.assertNotIn("a", ids)

    def test_empty_graph(self):
        graph = ig._empty_graph()
        results = ig.suggest_topics(graph, n=5, seed=42)
        self.assertEqual(results, [])

    def test_single_concept(self):
        graph = ig._empty_graph()
        today = ig.datetime.now().strftime("%Y-%m-%d")
        graph["concepts"]["solo"] = {
            "labels": {"en": "Solo"}, "category": "general",
            "weight": 5.0, "lastSeen": today, "sessionCount": 1,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 1, "beta": 1},
        }
        results = ig.suggest_topics(graph, n=5, seed=42)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "solo")

    def test_low_weight_excluded(self):
        graph = ig._empty_graph()
        today = ig.datetime.now().strftime("%Y-%m-%d")
        graph["concepts"]["low"] = {
            "labels": {"en": "Low"}, "category": "general",
            "weight": 0.01, "lastSeen": today, "sessionCount": 1,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 1, "beta": 1},
        }
        results = ig.suggest_topics(graph, n=5, seed=42)
        self.assertEqual(results, [])

    def test_returns_reasons(self):
        graph = ig._empty_graph()
        today = ig.datetime.now().strftime("%Y-%m-%d")
        graph["concepts"]["topic"] = {
            "labels": {"en": "Topic"}, "category": "general",
            "weight": 5.0, "lastSeen": today, "sessionCount": 1,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 1, "beta": 1},
        }
        results = ig.suggest_topics(graph, n=1, seed=42)
        self.assertEqual(len(results[0]), 3)  # (id, score, reason)
        self.assertIsInstance(results[0][2], str)


class TestBanditFeedback(unittest.TestCase):
    """Test bandit update operations."""

    def test_engaged_increments_alpha(self):
        graph = ig._empty_graph()
        graph["concepts"]["test"] = {
            "labels": {"en": "Test"}, "category": "general",
            "weight": 1.0, "lastSeen": "2026-02-16", "sessionCount": 1,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 2, "beta": 1},
        }
        ig.update_bandit(graph, "test", True)
        self.assertEqual(graph["concepts"]["test"]["bandit"]["alpha"], 3)
        self.assertEqual(graph["concepts"]["test"]["bandit"]["beta"], 1)

    def test_ignored_increments_beta(self):
        graph = ig._empty_graph()
        graph["concepts"]["test"] = {
            "labels": {"en": "Test"}, "category": "general",
            "weight": 1.0, "lastSeen": "2026-02-16", "sessionCount": 1,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 2, "beta": 1},
        }
        ig.update_bandit(graph, "test", False)
        self.assertEqual(graph["concepts"]["test"]["bandit"]["alpha"], 2)
        self.assertEqual(graph["concepts"]["test"]["bandit"]["beta"], 2)

    def test_missing_concept_no_error(self):
        graph = ig._empty_graph()
        ig.update_bandit(graph, "nonexistent", True)  # Should not raise


class TestGenerateMarkdown(unittest.TestCase):
    """Test Markdown generation from graph."""

    def test_empty_graph(self):
        graph = ig._empty_graph()
        graph["meta"]["lastUpdated"] = "2026-02-16"
        md = ig.generate_markdown(graph)
        self.assertIn("# User Interests", md)
        self.assertIn("source: auto-generated from interest-graph.json", md)

    def test_category_grouping(self):
        graph = ig._empty_graph()
        today = ig.datetime.now().strftime("%Y-%m-%d")
        graph["concepts"]["python"] = {
            "labels": {"en": "Python"}, "category": "programming",
            "weight": 5.0, "lastSeen": today, "sessionCount": 3,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 2, "beta": 1},
        }
        graph["concepts"]["docker"] = {
            "labels": {"en": "Docker"}, "category": "infrastructure",
            "weight": 3.0, "lastSeen": today, "sessionCount": 2,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 1, "beta": 1},
        }
        md = ig.generate_markdown(graph)
        self.assertIn("## Infrastructure", md)
        self.assertIn("## Programming", md)

    def test_keywords_listed(self):
        graph = ig._empty_graph()
        today = ig.datetime.now().strftime("%Y-%m-%d")
        graph["concepts"]["python"] = {
            "labels": {"en": "Python"}, "category": "programming",
            "weight": 5.0, "lastSeen": today, "sessionCount": 3,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 2, "beta": 1},
        }
        graph["concepts"]["rust"] = {
            "labels": {"en": "Rust"}, "category": "programming",
            "weight": 2.0, "lastSeen": today, "sessionCount": 1,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 1, "beta": 1},
        }
        md = ig.generate_markdown(graph)
        self.assertIn("- **keywords**: [python, rust]", md)

    def test_suggestions_section(self):
        graph = ig._empty_graph()
        today = ig.datetime.now().strftime("%Y-%m-%d")
        graph["concepts"]["topic1"] = {
            "labels": {"en": "Topic One"}, "category": "general",
            "weight": 5.0, "lastSeen": today, "sessionCount": 3,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 3, "beta": 1},
        }
        md = ig.generate_markdown(graph)
        self.assertIn("## Suggested Next Directions", md)
        self.assertIn("Topic One", md)

    def test_general_category_last(self):
        graph = ig._empty_graph()
        today = ig.datetime.now().strftime("%Y-%m-%d")
        graph["concepts"]["python"] = {
            "labels": {"en": "Python"}, "category": "programming",
            "weight": 5.0, "lastSeen": today, "sessionCount": 3,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 2, "beta": 1},
        }
        graph["concepts"]["misc"] = {
            "labels": {"en": "Misc"}, "category": "general",
            "weight": 3.0, "lastSeen": today, "sessionCount": 2,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 1, "beta": 1},
        }
        md = ig.generate_markdown(graph)
        prog_pos = md.index("## Programming")
        gen_pos = md.index("## General")
        self.assertLess(prog_pos, gen_pos)


class TestMigration(unittest.TestCase):
    """Test migration from user-interests.md."""

    def _make_md(self, content):
        """Write MD to temp file and return path."""
        import tempfile
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
        f.write(content)
        f.close()
        return f.name

    def test_parse_categories(self):
        md = self._make_md("""---
version: 1
session_count: 10
---
# User Interests

## Programming
- **keywords**: [python, rust]
- **description**: Languages

## Systems
- **keywords**: [docker, kubernetes]
- **description**: Infra
""")
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_graph = Path(tmpdir) / "interest-graph.json"
            with mock.patch.object(ig, "GRAPH_FILE", fake_graph):
                graph = ig.migrate_from_markdown(md)
        self.assertIn("python", graph["concepts"])
        self.assertIn("rust", graph["concepts"])
        self.assertIn("docker", graph["concepts"])
        self.assertEqual(graph["concepts"]["python"]["category"], "programming")
        self.assertEqual(graph["concepts"]["docker"]["category"], "systems")
        import os
        os.unlink(md)

    def test_parse_frontmatter_session_count(self):
        md = self._make_md("""---
version: 1
session_count: 22
---
# User Interests

## General
- **keywords**: [testing]
- **description**: Testing stuff
""")
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_graph = Path(tmpdir) / "interest-graph.json"
            with mock.patch.object(ig, "GRAPH_FILE", fake_graph):
                graph = ig.migrate_from_markdown(md)
        self.assertEqual(graph["meta"]["totalSessions"], 22)
        import os
        os.unlink(md)

    def test_cooccurrence_edges(self):
        md = self._make_md("""---
version: 1
---
# User Interests

## Programming
- **keywords**: [python, rust, go]
- **description**: Languages
""")
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_graph = Path(tmpdir) / "interest-graph.json"
            with mock.patch.object(ig, "GRAPH_FILE", fake_graph):
                graph = ig.migrate_from_markdown(md)
        # Adjacent pairs: python-rust, go-rust
        self.assertTrue(len(graph["edges"]) >= 2)
        import os
        os.unlink(md)

    def test_skips_non_category_sections(self):
        md = self._make_md("""---
version: 1
---
# User Interests

## Programming
- **keywords**: [python]
- **description**: Languages

## Recently Explored
1. Some recent topic

## Suggested Next Directions
1. A suggestion
""")
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_graph = Path(tmpdir) / "interest-graph.json"
            with mock.patch.object(ig, "GRAPH_FILE", fake_graph):
                graph = ig.migrate_from_markdown(md)
        self.assertEqual(len(graph["concepts"]), 1)
        self.assertIn("python", graph["concepts"])
        import os
        os.unlink(md)

    def test_empty_file(self):
        md = self._make_md("")
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_graph = Path(tmpdir) / "interest-graph.json"
            with mock.patch.object(ig, "GRAPH_FILE", fake_graph):
                graph = ig.migrate_from_markdown(md)
        self.assertEqual(len(graph["concepts"]), 0)
        import os
        os.unlink(md)


class TestCommunityDetection(unittest.TestCase):
    """Test label propagation community detection."""

    def _make_graph_with_edges(self, edges, min_weight=2):
        graph = ig._empty_graph()
        today = ig.datetime.now().strftime("%Y-%m-%d")
        nodes = set()
        for src, tgt, w in edges:
            nodes.add(src)
            nodes.add(tgt)
            graph["edges"].append({"src": src, "tgt": tgt, "w": w, "lastSeen": today})
        for n in nodes:
            graph["concepts"][n] = {
                "labels": {"en": n.title()}, "category": "general",
                "weight": 1.0, "lastSeen": today, "sessionCount": 1,
                "broader": [], "narrower": [], "related": [],
                "bandit": {"alpha": 1, "beta": 1},
            }
        return graph

    def test_empty_graph(self):
        graph = ig._empty_graph()
        communities = ig.detect_communities(graph)
        self.assertEqual(communities, {})

    def test_single_community(self):
        graph = self._make_graph_with_edges([
            ("a", "b", 3), ("b", "c", 3), ("a", "c", 2),
        ])
        communities = ig.detect_communities(graph, min_edge_weight=2)
        self.assertEqual(len(communities), 1)
        members = list(communities.values())[0]
        self.assertEqual(set(members), {"a", "b", "c"})

    def test_two_communities(self):
        graph = self._make_graph_with_edges([
            ("a", "b", 3), ("a", "c", 3),
            ("x", "y", 3), ("x", "z", 3),
        ])
        communities = ig.detect_communities(graph, min_edge_weight=2)
        self.assertGreaterEqual(len(communities), 2)

    def test_filters_by_min_weight(self):
        graph = self._make_graph_with_edges([
            ("a", "b", 1), ("b", "c", 1),
        ])
        communities = ig.detect_communities(graph, min_edge_weight=2)
        self.assertEqual(communities, {})


class TestFindGaps(unittest.TestCase):
    """Test structural gap detection."""

    def test_empty_graph(self):
        graph = ig._empty_graph()
        gaps = ig.find_gaps(graph)
        self.assertEqual(gaps, [])

    def test_finds_gap(self):
        graph = ig._empty_graph()
        today = ig.datetime.now().strftime("%Y-%m-%d")
        # A-B connected, A-C connected, but B-C not connected → gap
        for n in ["a", "b", "c"]:
            graph["concepts"][n] = {
                "labels": {"en": n.upper()}, "category": "general",
                "weight": 1.0, "lastSeen": today, "sessionCount": 1,
                "broader": [], "narrower": [], "related": [],
                "bandit": {"alpha": 1, "beta": 1},
            }
        graph["edges"] = [
            {"src": "a", "tgt": "b", "w": 3, "lastSeen": today},
            {"src": "a", "tgt": "c", "w": 3, "lastSeen": today},
        ]
        # B and C share neighbor A, but need >=2 shared neighbors
        # Add D connected to both B and C
        graph["concepts"]["d"] = {
            "labels": {"en": "D"}, "category": "general",
            "weight": 1.0, "lastSeen": today, "sessionCount": 1,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 1, "beta": 1},
        }
        graph["edges"].extend([
            {"src": "b", "tgt": "d", "w": 3, "lastSeen": today},
            {"src": "c", "tgt": "d", "w": 3, "lastSeen": today},
        ])
        gaps = ig.find_gaps(graph)
        self.assertTrue(len(gaps) > 0)
        gap_pairs = [(g[0], g[1]) for g in gaps]
        # B-C should be a gap (shared: A and D)
        self.assertTrue(
            ("b", "c") in gap_pairs or ("c", "b") in gap_pairs
        )

    def test_no_gap_when_fully_connected(self):
        graph = ig._empty_graph()
        today = ig.datetime.now().strftime("%Y-%m-%d")
        for n in ["a", "b", "c"]:
            graph["concepts"][n] = {
                "labels": {"en": n.upper()}, "category": "general",
                "weight": 1.0, "lastSeen": today, "sessionCount": 1,
                "broader": [], "narrower": [], "related": [],
                "bandit": {"alpha": 1, "beta": 1},
            }
        # Fully connected triangle — no gaps possible
        graph["edges"] = [
            {"src": "a", "tgt": "b", "w": 3, "lastSeen": today},
            {"src": "a", "tgt": "c", "w": 3, "lastSeen": today},
            {"src": "b", "tgt": "c", "w": 3, "lastSeen": today},
        ]
        gaps = ig.find_gaps(graph)
        self.assertEqual(gaps, [])

    def test_respects_n_limit(self):
        graph = ig._empty_graph()
        today = ig.datetime.now().strftime("%Y-%m-%d")
        # Create a star topology: hub connects to many spokes, spokes share hub as neighbor
        for i in range(10):
            n = f"spoke{i}"
            graph["concepts"][n] = {
                "labels": {"en": n.title()}, "category": "general",
                "weight": 1.0, "lastSeen": today, "sessionCount": 1,
                "broader": [], "narrower": [], "related": [],
                "bandit": {"alpha": 1, "beta": 1},
            }
        graph["concepts"]["hub1"] = {
            "labels": {"en": "Hub1"}, "category": "general",
            "weight": 1.0, "lastSeen": today, "sessionCount": 1,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 1, "beta": 1},
        }
        graph["concepts"]["hub2"] = {
            "labels": {"en": "Hub2"}, "category": "general",
            "weight": 1.0, "lastSeen": today, "sessionCount": 1,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 1, "beta": 1},
        }
        for i in range(10):
            graph["edges"].append({"src": "hub1", "tgt": f"spoke{i}", "w": 3, "lastSeen": today})
            graph["edges"].append({"src": "hub2", "tgt": f"spoke{i}", "w": 3, "lastSeen": today})
        gaps = ig.find_gaps(graph, n=3)
        self.assertLessEqual(len(gaps), 3)

    def test_large_graph_safeguard(self):
        """Should return empty list when node count exceeds max_nodes."""
        graph = ig._empty_graph()
        today = ig.datetime.now().strftime("%Y-%m-%d")
        # Create a graph with many nodes
        for i in range(10):
            graph["concepts"][f"n{i}"] = {
                "labels": {"en": f"N{i}"}, "category": "general",
                "weight": 1.0, "lastSeen": today, "sessionCount": 1,
                "broader": [], "narrower": [], "related": [],
                "bandit": {"alpha": 1, "beta": 1},
            }
        # Connect them all to a hub
        for i in range(10):
            graph["edges"].append({"src": "hub", "tgt": f"n{i}", "w": 3, "lastSeen": today})
        # With max_nodes=5, should return empty (11 nodes > 5)
        gaps = ig.find_gaps(graph, n=5, max_nodes=5)
        self.assertEqual(gaps, [])
        # With default max_nodes (500), should work normally
        gaps_normal = ig.find_gaps(graph, n=5)
        self.assertIsInstance(gaps_normal, list)


class TestCLI(unittest.TestCase):
    """Test CLI dispatch."""

    def _run_cli(self, *args):
        script = str(Path(__file__).parent.parent / "scripts" / "interest_graph.py")
        result = subprocess.run(
            [sys.executable, script] + list(args),
            capture_output=True, text=True, timeout=10,
        )
        return result

    def test_load_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_graph = Path(tmpdir) / "interest-graph.json"
            data = ig._empty_graph()
            data["concepts"]["test"] = {
                "labels": {"en": "Test"}, "category": "general",
                "weight": 1.0, "lastSeen": "2026-02-16", "sessionCount": 1,
                "broader": [], "narrower": [], "related": [],
                "bandit": {"alpha": 1, "beta": 1},
            }
            fake_graph.write_text(json.dumps(data), encoding="utf-8")
            with mock.patch.dict("os.environ", {"HOME": tmpdir, "USERPROFILE": tmpdir}):
                # Need to use env var since GRAPH_FILE is a module constant
                # Instead, test via function calls
                pass
        # CLI integration tested via function calls in other tests
        # Subprocess CLI tested with no-args for usage message
        result = self._run_cli()
        self.assertNotEqual(result.returncode, 0)

    def test_unknown_command(self):
        result = self._run_cli("nonexistent")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown command", result.stderr)

    def test_suggest_command_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_graph = Path(tmpdir) / ".claude" / "interest-graph.json"
            fake_graph.parent.mkdir(parents=True, exist_ok=True)
            fake_graph.write_text(json.dumps(ig._empty_graph()), encoding="utf-8")
            # Can't easily override home in subprocess, so test via function
            graph = ig._empty_graph()
            results = ig.suggest_topics(graph, n=5, seed=42)
            self.assertEqual(results, [])

    def test_add_concepts_via_function(self):
        graph = ig._empty_graph()
        concepts_json = [{"id": "test-concept", "labels": {"en": "Test Concept"}, "category": "general"}]
        ig.add_concepts(graph, concepts_json)
        self.assertIn("test-concept", graph["concepts"])

    def test_decay_command_via_function(self):
        graph = ig._empty_graph()
        today = ig.datetime.now().strftime("%Y-%m-%d")
        graph["concepts"]["fresh"] = {
            "labels": {"en": "Fresh"}, "category": "general",
            "weight": 5.0, "lastSeen": today, "sessionCount": 2,
            "broader": [], "narrower": [], "related": [],
            "bandit": {"alpha": 1, "beta": 1},
        }
        ig.apply_decay(graph)
        self.assertEqual(graph["concepts"]["fresh"]["weight"], 5.0)


if __name__ == "__main__":
    unittest.main()
