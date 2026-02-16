#!/usr/bin/env python
"""
Tests for the auto-detection of build vs research mode from topic wording.

These patterns are embedded in setup-auto-explorer.sh's Python block.
The test replicates the exact regex patterns to validate detection accuracy.
"""

import re
import unittest


def detect_mode(topic):
    """
    Replicate the exact Python logic from setup-auto-explorer.sh for testing.
    Returns 'build' or 'research'.
    """
    lower_topic = topic.lower().strip()
    build_patterns = [
        r'^(build|implement|create|develop|fix|refactor|add|make|write|set\s*up|deploy|migrate|convert|port|upgrade|improve|optimize|update|configure|install|redesign|integrate|automate|extract|remove|delete|replace|move|rename|split|merge|clean\s*up|debug|patch|scaffold|generate|wire\s*up)',
        r'^(設計|建立|開發|實作|修復|重構|新增|部署|撰寫|建置|優化|更新|設定|安裝|改善|整合|自動化|提取|刪除|替換|移動|合併|清理|除錯|修補|產生|升級|進化)',
    ]
    for pat in build_patterns:
        if re.search(pat, lower_topic):
            return 'build'
    return 'research'


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


if __name__ == "__main__":
    unittest.main()
