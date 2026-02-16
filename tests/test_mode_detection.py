#!/usr/bin/env python
"""
Tests for the auto-detection of build vs research mode from topic wording.

The canonical implementation lives in scripts/helpers.py.
Tests cover direct verbs, polite prefixes (EN + CJK), and research exclusions.
"""

import unittest

from conftest import import_script

helpers = import_script("helpers.py")
detect_mode = helpers.detect_mode


class TestEnglishBuildPatterns(unittest.TestCase):
    """Test English action verb detection."""

    def test_original_verbs(self):
        """Verbs from v1.0.0 — must still work."""
        verbs = [
            "build a REST API",
            "implement authentication",
            "create a dashboard",
            "develop a plugin",
            "fix the login bug",
            "refactor the database layer",
            "add unit tests",
            "make it faster",
            "write a CLI tool",
            "set up CI/CD",
            "deploy to AWS",
            "migrate from MySQL",
            "convert to TypeScript",
            "port to Linux",
            "upgrade dependencies",
        ]
        for topic in verbs:
            with self.subTest(topic=topic):
                self.assertEqual(detect_mode(topic), "build", f"Failed for: {topic}")

    def test_new_verbs(self):
        """Verbs added in v1.2.0."""
        verbs = [
            "improve error handling",
            "optimize database queries",
            "update the README",
            "configure webpack",
            "install dependencies",
            "redesign the landing page",
            "integrate Stripe payments",
            "automate the deployment",
            "extract shared utilities",
            "remove deprecated code",
            "delete the old API",
            "replace Redux with Zustand",
            "move files to src/",
            "rename the component",
            "split the monolith",
            "merge the feature branches",
            "clean up unused imports",
            "debug the memory leak",
            "patch the security vulnerability",
            "scaffold a new project",
            "generate API types",
            "wire up the event system",
        ]
        for topic in verbs:
            with self.subTest(topic=topic):
                self.assertEqual(detect_mode(topic), "build", f"Failed for: {topic}")

    def test_research_topics(self):
        """Topics without action verbs should be research."""
        topics = [
            "Rust async programming",
            "distributed consensus algorithms",
            "WebAssembly performance",
            "how does React rendering work",
            "Go generics",
            "what are building systems",  # 'building' is not at start → research
            "the art of debugging",  # 'debugging' is not at start
        ]
        for topic in topics:
            with self.subTest(topic=topic):
                self.assertEqual(detect_mode(topic), "research", f"Failed for: {topic}")

    def test_case_insensitive(self):
        self.assertEqual(detect_mode("BUILD a REST API"), "build")
        self.assertEqual(detect_mode("Fix The Bug"), "build")

    def test_setup_with_space(self):
        self.assertEqual(detect_mode("set up the project"), "build")
        self.assertEqual(detect_mode("setup the project"), "build")

    def test_cleanup_with_space(self):
        self.assertEqual(detect_mode("clean up the codebase"), "build")


class TestCJKBuildPatterns(unittest.TestCase):
    """Test CJK (Chinese) action verb detection."""

    def test_original_cjk_verbs(self):
        """CJK verbs from v1.0.0."""
        topics = [
            "設計一個 REST API",
            "建立使用者認證",
            "開發自動化工具",
            "實作搜尋功能",
            "修復登入問題",
            "重構資料庫層",
            "新增測試",
            "部署到雲端",
            "撰寫文件",
            "建置 CI/CD",
        ]
        for topic in topics:
            with self.subTest(topic=topic):
                self.assertEqual(detect_mode(topic), "build", f"Failed for: {topic}")

    def test_new_cjk_verbs(self):
        """CJK verbs added in v1.2.0."""
        topics = [
            "優化查詢效能",
            "更新 README",
            "設定 webpack",
            "安裝依賴套件",
            "改善錯誤處理",
            "整合 Stripe 付款",
            "自動化部署流程",
            "提取共用工具",
            "刪除舊的 API",
            "替換 Redux",
            "移動檔案到 src/",
            "合併功能分支",
            "清理未使用的 import",
            "除錯記憶體洩漏",
            "修補安全漏洞",
            "產生 API 型別",
            "升級依賴套件",
            "進化此 project",
        ]
        for topic in topics:
            with self.subTest(topic=topic):
                self.assertEqual(detect_mode(topic), "build", f"Failed for: {topic}")

    def test_cjk_research_topics(self):
        """CJK topics without action verbs should be research."""
        topics = [
            "Rust 非同步程式設計",
            "分散式共識演算法",
            "WebAssembly 效能分析",
            "React 渲染機制",
        ]
        for topic in topics:
            with self.subTest(topic=topic):
                self.assertEqual(detect_mode(topic), "research", f"Failed for: {topic}")


class TestPolitePrefix(unittest.TestCase):
    """Test that polite prefixes are stripped before matching (v1.3.0).

    Users naturally write "please build X" or "請進化此 project" — the polite
    prefix should not prevent build mode detection.
    """

    def test_english_polite_build(self):
        """English polite prefixes + action verbs → build."""
        topics = [
            "please build a REST API",
            "can you fix the login bug",
            "could you refactor the database",
            "i want to create a dashboard",
            "i need to deploy to AWS",
            "i'd like to improve error handling",
            "let's implement authentication",
            "help me add unit tests",
        ]
        for topic in topics:
            with self.subTest(topic=topic):
                self.assertEqual(detect_mode(topic), "build", f"Failed for: {topic}")

    def test_english_polite_research(self):
        """English polite prefixes + non-action topics → research."""
        topics = [
            "please research quantum computing",
            "can you explain how React works",
            "could you describe distributed systems",
            "help me understand WebAssembly",
        ]
        for topic in topics:
            with self.subTest(topic=topic):
                self.assertEqual(detect_mode(topic), "research", f"Failed for: {topic}")

    def test_cjk_polite_build(self):
        """CJK polite prefixes + action verbs → build."""
        topics = [
            "請進化此 project",
            "請自我進化此 project",
            "幫我建立一個 REST API",
            "協助我修復登入問題",
            "請幫忙優化查詢效能",
            "請協助我重構資料庫層",
            "自我進化此 project",
        ]
        for topic in topics:
            with self.subTest(topic=topic):
                self.assertEqual(detect_mode(topic), "build", f"Failed for: {topic}")

    def test_cjk_polite_research(self):
        """CJK polite prefixes + non-action topics → research."""
        topics = [
            "請研究量子計算",
            "幫我了解 WebAssembly",
        ]
        for topic in topics:
            with self.subTest(topic=topic):
                self.assertEqual(detect_mode(topic), "research", f"Failed for: {topic}")


if __name__ == "__main__":
    unittest.main()
