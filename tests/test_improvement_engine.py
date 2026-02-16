#!/usr/bin/env python
"""Tests for improvement_engine.py"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
from conftest import import_script

ie = import_script("improvement_engine.py")


def _make_session(slug="test", mode="research", status="completed",
                  template=None, completion_type="natural",
                  iterations=5, iter_ratio=0.5, output_density=5.0,
                  keywords=None, mode_corrected=None):
    entry = {
        "slug": slug, "mode": mode, "status": status,
        "iterations": iterations,
        "quality_signals": {
            "completion_type": completion_type,
            "iterations_vs_budget": iter_ratio,
            "output_density": output_density,
        },
    }
    if template:
        entry["template"] = template
    if keywords:
        entry["keywords"] = keywords
    if mode_corrected is not None:
        entry["mode_corrected"] = mode_corrected
    return entry


class TestTemplateStats(unittest.TestCase):
    """Test per-template performance aggregation."""

    def test_empty_sessions(self):
        stats = ie.template_stats([])
        self.assertEqual(stats, {})

    def test_single_session_no_template(self):
        sessions = [_make_session()]
        stats = ie.template_stats(sessions)
        self.assertIn("_none", stats)
        self.assertEqual(stats["_none"]["count"], 1)
        self.assertEqual(stats["_none"]["natural_completion_rate"], 1.0)

    def test_single_session_with_template(self):
        sessions = [_make_session(template="deep-dive")]
        stats = ie.template_stats(sessions)
        self.assertIn("deep-dive", stats)
        self.assertEqual(stats["deep-dive"]["count"], 1)

    def test_multiple_templates(self):
        sessions = [
            _make_session(template="deep-dive", completion_type="natural"),
            _make_session(template="deep-dive", completion_type="natural"),
            _make_session(template="quickstart", completion_type="budget_exhausted"),
        ]
        stats = ie.template_stats(sessions)
        self.assertEqual(stats["deep-dive"]["count"], 2)
        self.assertEqual(stats["deep-dive"]["natural_completion_rate"], 1.0)
        self.assertEqual(stats["quickstart"]["natural_completion_rate"], 0.0)

    def test_bandit_state(self):
        sessions = [
            _make_session(template="deep-dive", completion_type="natural"),
            _make_session(template="deep-dive", completion_type="budget_exhausted"),
            _make_session(template="deep-dive", completion_type="natural"),
        ]
        stats = ie.template_stats(sessions)
        bandit = stats["deep-dive"]["bandit"]
        self.assertEqual(bandit["alpha"], 3)  # 1 prior + 2 natural
        self.assertEqual(bandit["beta"], 2)   # 1 prior + 1 non-natural


class TestSuggestTemplate(unittest.TestCase):
    """Test Thompson Sampling template selection."""

    def test_empty_templates(self):
        tpl, score = ie.suggest_template([], [])
        self.assertIsNone(tpl)

    def test_single_template(self):
        tpl, score = ie.suggest_template([], ["deep-dive"], seed=42)
        self.assertEqual(tpl, "deep-dive")

    def test_deterministic_with_seed(self):
        sessions = [
            _make_session(template="deep-dive", completion_type="natural"),
            _make_session(template="deep-dive", completion_type="natural"),
            _make_session(template="quickstart", completion_type="budget_exhausted"),
        ]
        templates = ["deep-dive", "quickstart", "comparison"]
        r1 = ie.suggest_template(sessions, templates, seed=42)
        r2 = ie.suggest_template(sessions, templates, seed=42)
        self.assertEqual(r1, r2)

    def test_picks_from_available(self):
        templates = ["deep-dive", "quickstart"]
        tpl, _ = ie.suggest_template([], templates, seed=42)
        self.assertIn(tpl, templates)


class TestSuggestBudget(unittest.TestCase):
    """Test budget adaptation from history."""

    def test_not_enough_data(self):
        sessions = [_make_session(), _make_session()]
        result = ie.suggest_budget(sessions, "research")
        self.assertIsNone(result)

    def test_suggests_aggressive(self):
        sessions = [
            _make_session(mode="research", iter_ratio=0.98),
            _make_session(mode="research", iter_ratio=0.99),
            _make_session(mode="research", iter_ratio=0.97),
        ]
        result = ie.suggest_budget(sessions, "research")
        self.assertEqual(result, "aggressive")

    def test_suggests_conservative(self):
        sessions = [
            _make_session(mode="build", iter_ratio=0.2),
            _make_session(mode="build", iter_ratio=0.3),
            _make_session(mode="build", iter_ratio=0.25),
        ]
        result = ie.suggest_budget(sessions, "build")
        self.assertEqual(result, "conservative")

    def test_no_suggestion_when_balanced(self):
        sessions = [
            _make_session(mode="research", iter_ratio=0.6),
            _make_session(mode="research", iter_ratio=0.7),
            _make_session(mode="research", iter_ratio=0.5),
        ]
        result = ie.suggest_budget(sessions, "research")
        self.assertIsNone(result)


class TestModeCorrection(unittest.TestCase):
    """Test mode auto-detection accuracy tracking."""

    def test_no_data(self):
        total, corrected = ie.mode_correction_rate([])
        self.assertEqual(total, 0)
        self.assertEqual(corrected, 0)

    def test_with_corrections(self):
        sessions = [
            _make_session(mode_corrected=False),
            _make_session(mode_corrected=True),
            _make_session(mode_corrected=False),
            _make_session(),  # no mode_corrected field
        ]
        total, corrected = ie.mode_correction_rate(sessions)
        self.assertEqual(total, 3)
        self.assertEqual(corrected, 1)


class TestFrequentKeywords(unittest.TestCase):
    """Test keyword frequency extraction."""

    def test_empty_sessions(self):
        result = ie.frequent_keywords([])
        self.assertEqual(result, [])

    def test_counts_keywords(self):
        sessions = [
            _make_session(keywords=["docker", "python", "docker"]),
            _make_session(keywords=["docker", "rust"]),
        ]
        result = ie.frequent_keywords(sessions, top_n=3)
        keywords = [kw for kw, _ in result]
        self.assertEqual(keywords[0], "docker")
        self.assertIn("python", keywords)
        self.assertIn("rust", keywords)


class TestSessionSimilarity(unittest.TestCase):
    """Test Jaccard similarity between sessions."""

    def test_identical_keywords(self):
        a = {"keywords": ["docker", "python"]}
        b = {"keywords": ["docker", "python"]}
        self.assertAlmostEqual(ie.session_similarity(a, b), 1.0)

    def test_disjoint_keywords(self):
        a = {"keywords": ["docker", "python"]}
        b = {"keywords": ["rust", "go"]}
        self.assertAlmostEqual(ie.session_similarity(a, b), 0.0)

    def test_partial_overlap(self):
        a = {"keywords": ["docker", "python", "fastapi"]}
        b = {"keywords": ["docker", "python", "rust"]}
        sim = ie.session_similarity(a, b)
        self.assertAlmostEqual(sim, 2 / 4)  # 2 shared / 4 total unique


class TestDetectRepeat(unittest.TestCase):
    """Test repeat topic detection."""

    def test_no_match(self):
        sessions = [_make_session(keywords=["rust", "go"])]
        result = ie.detect_repeat_topic(sessions, ["docker", "python"])
        self.assertIsNone(result)

    def test_match_found(self):
        sessions = [_make_session(slug="docker-k8s", keywords=["docker", "kubernetes", "ci-cd"])]
        result = ie.detect_repeat_topic(sessions, ["docker", "kubernetes", "helm"], threshold=0.3)
        self.assertIsNotNone(result)
        self.assertEqual(result["slug"], "docker-k8s")

    def test_empty_keywords(self):
        sessions = [_make_session(keywords=["docker"])]
        result = ie.detect_repeat_topic(sessions, [])
        self.assertIsNone(result)


class TestExtractKeywords(unittest.TestCase):
    """Test TF-IDF keyword extraction."""

    def test_nonexistent_dir(self):
        result = ie.extract_keywords_tfidf("/nonexistent/path")
        self.assertEqual(result, [])

    def test_extracts_from_md_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "01-docker.md").write_text(
                "Docker containers are great for deployment.\n"
                "Docker images can be built from Dockerfiles.\n"
                "Kubernetes orchestrates docker containers.\n",
                encoding="utf-8",
            )
            (Path(tmpdir) / "02-python.md").write_text(
                "Python is a programming language.\n"
                "Python has great libraries for data science.\n",
                encoding="utf-8",
            )
            result = ie.extract_keywords_tfidf(tmpdir, top_n=5)
        self.assertTrue(len(result) > 0)
        keywords = [kw for kw, _ in result]
        self.assertIn("docker", keywords)


class TestCLI(unittest.TestCase):
    """Test CLI dispatch."""

    def test_unknown_command(self):
        import subprocess
        script = str(Path(__file__).parent.parent / "scripts" / "improvement_engine.py")
        result = subprocess.run(
            [sys.executable, script, "nonexistent"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_no_args(self):
        import subprocess
        script = str(Path(__file__).parent.parent / "scripts" / "improvement_engine.py")
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True, text=True, timeout=10,
        )
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
