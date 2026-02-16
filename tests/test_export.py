#!/usr/bin/env python
"""Tests for scripts/export-html.py — HTML report generation."""

import os
import tempfile
import unittest

from conftest import import_script

export_html = import_script("export-html.py")


class TestConvertInline(unittest.TestCase):
    """Test inline Markdown to HTML conversion."""

    def test_bold(self):
        self.assertIn("<strong>bold</strong>", export_html.convert_inline("**bold**"))

    def test_italic(self):
        self.assertIn("<em>italic</em>", export_html.convert_inline("*italic*"))

    def test_inline_code(self):
        self.assertIn("<code>code</code>", export_html.convert_inline("`code`"))

    def test_link(self):
        result = export_html.convert_inline("[text](http://example.com)")
        self.assertIn('href="http://example.com"', result)
        self.assertIn(">text<", result)

    def test_html_escaping(self):
        result = export_html.convert_inline("<script>alert(1)</script>")
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)


class TestMdToHtml(unittest.TestCase):
    """Test full Markdown to HTML conversion."""

    def test_headers(self):
        result = export_html.md_to_html("# Title\n## Subtitle")
        self.assertIn("<h1", result)
        self.assertIn("<h2", result)
        self.assertIn('id="title"', result)

    def test_code_block(self):
        md = "```python\nprint('hello')\n```"
        result = export_html.md_to_html(md)
        self.assertIn("<pre>", result)
        self.assertIn("<code", result)
        self.assertIn("language-python", result)
        self.assertIn("print(", result)

    def test_code_block_html_escaping(self):
        md = "```\n<div>test</div>\n```"
        result = export_html.md_to_html(md)
        self.assertIn("&lt;div&gt;", result)
        self.assertNotIn("<div>test</div>", result)

    def test_unordered_list(self):
        md = "- item 1\n- item 2\n- item 3"
        result = export_html.md_to_html(md)
        self.assertIn("<ul>", result)
        self.assertEqual(result.count("<li>"), 3)

    def test_ordered_list(self):
        md = "1. first\n2. second"
        result = export_html.md_to_html(md)
        self.assertIn("<ol>", result)
        self.assertEqual(result.count("<li>"), 2)

    def test_paragraph(self):
        result = export_html.md_to_html("Just some text.")
        self.assertIn("<p>Just some text.</p>", result)

    def test_horizontal_rule(self):
        result = export_html.md_to_html("---")
        self.assertIn("<hr>", result)

    def test_table(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = export_html.md_to_html(md)
        self.assertIn("<table>", result)
        self.assertIn("<th>", result)
        self.assertIn("<td>", result)

    def test_table_separator_row_removed(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = export_html.md_to_html(md)
        # Should NOT have a row with just dashes
        self.assertNotIn("---", result)

    def test_empty_input(self):
        result = export_html.md_to_html("")
        self.assertEqual(result, "")

    def test_header_anchor_generation(self):
        result = export_html.md_to_html("## Hello World!")
        self.assertIn('id="hello-world"', result)


class TestRenderTable(unittest.TestCase):
    """Test table rendering."""

    def test_empty_rows(self):
        self.assertEqual(export_html.render_table([]), "")

    def test_header_only(self):
        result = export_html.render_table([["A", "B"]])
        self.assertIn("<thead>", result)
        self.assertIn("<th>", result)

    def test_header_and_data(self):
        result = export_html.render_table([["Name", "Value"], ["x", "1"]])
        self.assertIn("<th>", result)
        self.assertIn("<td>", result)


class TestGenerateReport(unittest.TestCase):
    """Test full report generation from a directory of Markdown files."""

    def test_generates_html_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create sample Markdown files
            with open(os.path.join(tmpdir, "00-overview.md"), "w", encoding="utf-8") as f:
                f.write("# Overview\n\nThis is the overview.\n")
            with open(os.path.join(tmpdir, "01-details.md"), "w", encoding="utf-8") as f:
                f.write("# Details\n\nMore information here.\n")

            result = export_html.generate_report(tmpdir)

            self.assertTrue(result.exists())
            self.assertEqual(result.name, "report.html")
            content = result.read_text(encoding="utf-8")
            self.assertIn("<!DOCTYPE html>", content)
            self.assertIn("Auto-Explorer", content)

    def test_index_file_first(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "01-details.md"), "w", encoding="utf-8") as f:
                f.write("# Details\n")
            with open(os.path.join(tmpdir, "_index.md"), "w", encoding="utf-8") as f:
                f.write("# Index\n")

            result = export_html.generate_report(tmpdir)
            content = result.read_text(encoding="utf-8")

            # _index.md should appear before 01-details.md in the HTML
            idx_pos = content.find('id="_index"')
            det_pos = content.find('id="01-details"')
            self.assertGreater(idx_pos, -1)
            self.assertGreater(det_pos, -1)
            self.assertLess(idx_pos, det_pos)

    def test_custom_output_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "00-test.md"), "w", encoding="utf-8") as f:
                f.write("# Test\n")
            custom_path = os.path.join(tmpdir, "custom-report.html")
            result = export_html.generate_report(tmpdir, custom_path)

            self.assertEqual(str(result), custom_path)
            self.assertTrue(os.path.exists(custom_path))

    def test_topic_from_topic_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, ".topic"), "w", encoding="utf-8") as f:
                f.write("Rust Async Programming\n")
            with open(os.path.join(tmpdir, "00-test.md"), "w", encoding="utf-8") as f:
                f.write("# Test\n")
            result = export_html.generate_report(tmpdir)
            content = result.read_text(encoding="utf-8")
            self.assertIn("Rust Async Programming", content)

    def test_topic_fallback_to_dirname(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "00-test.md"), "w", encoding="utf-8") as f:
                f.write("# Test\n")
            result = export_html.generate_report(tmpdir)
            content = result.read_text(encoding="utf-8")
            # Should use directory name as title
            dirname = os.path.basename(tmpdir)
            self.assertIn(dirname, content)

    def test_nav_sidebar_contains_filenames(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "00-overview.md"), "w", encoding="utf-8") as f:
                f.write("# Overview\n")
            with open(os.path.join(tmpdir, "01-details.md"), "w", encoding="utf-8") as f:
                f.write("# Details\n")
            result = export_html.generate_report(tmpdir)
            content = result.read_text(encoding="utf-8")
            self.assertIn("00-overview.md", content)
            self.assertIn("01-details.md", content)

    def test_dark_mode_css_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "00-test.md"), "w", encoding="utf-8") as f:
                f.write("# Test\n")
            result = export_html.generate_report(tmpdir)
            content = result.read_text(encoding="utf-8")
            self.assertIn("prefers-color-scheme: dark", content)

    def test_responsive_css_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "00-test.md"), "w", encoding="utf-8") as f:
                f.write("# Test\n")
            result = export_html.generate_report(tmpdir)
            content = result.read_text(encoding="utf-8")
            self.assertIn("max-width: 768px", content)

    def test_no_md_files_exits(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(SystemExit):
                export_html.generate_report(tmpdir)

    def test_cjk_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "00-test.md"), "w", encoding="utf-8") as f:
                f.write("# Rust 非同步程式設計\n\n這是測試內容。\n")
            with open(os.path.join(tmpdir, ".topic"), "w", encoding="utf-8") as f:
                f.write("Rust 非同步程式設計\n")
            result = export_html.generate_report(tmpdir)
            content = result.read_text(encoding="utf-8")
            self.assertIn("非同步程式設計", content)
            self.assertIn("這是測試內容", content)


class TestMdToHtmlEdgeCases(unittest.TestCase):
    """Test edge cases in Markdown conversion."""

    def test_nested_bold_italic(self):
        result = export_html.md_to_html("***bold italic***")
        # Should have both strong and em
        self.assertIn("<strong>", result)

    def test_multiple_code_blocks(self):
        md = "```\nblock 1\n```\n\nSome text\n\n```\nblock 2\n```"
        result = export_html.md_to_html(md)
        self.assertEqual(result.count("<pre>"), 2)

    def test_mixed_list_types(self):
        md = "- bullet\n\n1. numbered"
        result = export_html.md_to_html(md)
        self.assertIn("<ul>", result)
        self.assertIn("<ol>", result)

    def test_header_levels(self):
        md = "# H1\n## H2\n### H3\n#### H4"
        result = export_html.md_to_html(md)
        self.assertIn("<h1", result)
        self.assertIn("<h2", result)
        self.assertIn("<h3", result)
        self.assertIn("<h4", result)


if __name__ == "__main__":
    unittest.main()
