#!/usr/bin/env python
"""
Auto-Explorer HTML Export

Converts a directory of Markdown findings into a single navigable HTML report.
Zero external dependencies — uses only Python standard library.

Usage:
  python export-html.py <output_dir> [output_file]

  output_dir:  Path to the findings directory (e.g., auto-explore-findings/rust-async/)
  output_file: Optional HTML output path (default: <output_dir>/report.html)
"""

import html
import os
import re
import sys
from pathlib import Path


# --- Markdown to HTML conversion ---

def convert_inline(text):
    """Convert inline Markdown to HTML: bold, italic, code, links."""
    text = html.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    return text


def render_table(rows):
    """Render parsed table rows to HTML."""
    if len(rows) < 1:
        return ''
    parts = ['<table>']
    for i, cells in enumerate(rows):
        tag = 'th' if i == 0 else 'td'
        cells_html = ''.join(f'<{tag}>{convert_inline(c)}</{tag}>' for c in cells)
        if i == 0:
            parts.append(f'<thead><tr>{cells_html}</tr></thead><tbody>')
        else:
            parts.append(f'<tr>{cells_html}</tr>')
    parts.append('</tbody></table>')
    return '\n'.join(parts)


def md_to_html(text):
    """Convert Markdown text to HTML."""
    lines = text.split('\n')
    result = []
    in_code = False
    code_lang = ''
    code_buf = []
    table_buf = []
    list_buf = []
    list_type = None

    def flush_list():
        nonlocal list_buf, list_type
        if list_buf:
            tag = list_type or 'ul'
            items = ''.join(f'<li>{convert_inline(l)}</li>' for l in list_buf)
            result.append(f'<{tag}>{items}</{tag}>')
            list_buf = []
            list_type = None

    def flush_table():
        nonlocal table_buf
        if table_buf:
            rows = []
            for line in table_buf:
                cells = [c.strip() for c in line.strip('|').split('|')]
                rows.append(cells)
            # Remove separator row (row 1 with ---/:--)
            if len(rows) > 1 and all(re.match(r'^[-:]+$', c) for c in rows[1]):
                rows.pop(1)
            result.append(render_table(rows))
            table_buf = []

    for line in lines:
        # Code block fences
        if line.strip().startswith('```'):
            if in_code:
                escaped = html.escape('\n'.join(code_buf))
                cls = f' class="language-{code_lang}"' if code_lang else ''
                result.append(f'<pre><code{cls}>{escaped}</code></pre>')
                code_buf = []
                in_code = False
                code_lang = ''
            else:
                flush_list()
                flush_table()
                in_code = True
                code_lang = line.strip()[3:].strip()
            continue

        if in_code:
            code_buf.append(line)
            continue

        stripped = line.strip()

        # Empty line — flush state
        if not stripped:
            flush_list()
            flush_table()
            continue

        # Headers
        hm = re.match(r'^(#{1,6})\s+(.*)', stripped)
        if hm:
            flush_list()
            flush_table()
            lvl = len(hm.group(1))
            txt = hm.group(2)
            anchor = re.sub(r'[^a-z0-9]+', '-', txt.lower()).strip('-')
            result.append(f'<h{lvl} id="{anchor}">{convert_inline(txt)}</h{lvl}>')
            continue

        # Horizontal rule
        if re.match(r'^[-*_]{3,}\s*$', stripped):
            flush_list()
            flush_table()
            result.append('<hr>')
            continue

        # Table row
        if '|' in stripped and stripped.startswith('|'):
            flush_list()
            table_buf.append(stripped)
            continue

        # Unordered list
        ul = re.match(r'^[-*+]\s+(.*)', stripped)
        if ul:
            flush_table()
            if list_type != 'ul':
                flush_list()
                list_type = 'ul'
            list_buf.append(ul.group(1))
            continue

        # Ordered list
        ol = re.match(r'^\d+\.\s+(.*)', stripped)
        if ol:
            flush_table()
            if list_type != 'ol':
                flush_list()
                list_type = 'ol'
            list_buf.append(ol.group(1))
            continue

        # Paragraph
        flush_list()
        flush_table()
        result.append(f'<p>{convert_inline(stripped)}</p>')

    flush_list()
    flush_table()
    return '\n'.join(result)


# --- HTML template ---

CSS = """
:root { --bg: #fff; --fg: #1a1a2e; --muted: #6c757d; --border: #dee2e6;
        --code-bg: #f4f5f7; --accent: #4361ee; --sidebar-w: 260px; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #1a1a2e; --fg: #e0e0e0; --muted: #8a8a9a; --border: #333;
          --code-bg: #16213e; --accent: #7b8cde; }
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       color: var(--fg); background: var(--bg); line-height: 1.7; }
nav { position: fixed; top: 0; left: 0; width: var(--sidebar-w); height: 100vh;
      overflow-y: auto; padding: 1.5rem 1rem; border-right: 1px solid var(--border);
      background: var(--bg); font-size: 0.85rem; }
nav h2 { font-size: 1rem; margin-bottom: 1rem; color: var(--accent); }
nav a { display: block; padding: 0.3rem 0; color: var(--fg); text-decoration: none;
        border-bottom: 1px solid var(--border); }
nav a:hover { color: var(--accent); }
main { margin-left: var(--sidebar-w); padding: 2rem 3rem; max-width: 52rem; }
h1 { font-size: 1.8rem; margin: 2rem 0 1rem; border-bottom: 2px solid var(--accent); padding-bottom: 0.3rem; }
h2 { font-size: 1.4rem; margin: 1.8rem 0 0.8rem; }
h3 { font-size: 1.15rem; margin: 1.4rem 0 0.6rem; }
h4,h5,h6 { margin: 1rem 0 0.5rem; }
p { margin: 0.6rem 0; }
a { color: var(--accent); }
code { font-family: 'SF Mono', 'Fira Code', Consolas, monospace; font-size: 0.88em;
       background: var(--code-bg); padding: 0.15em 0.4em; border-radius: 3px; }
pre { background: var(--code-bg); padding: 1rem; border-radius: 6px; overflow-x: auto;
      margin: 1rem 0; border: 1px solid var(--border); }
pre code { background: none; padding: 0; font-size: 0.85em; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.9rem; }
th, td { border: 1px solid var(--border); padding: 0.5rem 0.75rem; text-align: left; }
th { background: var(--code-bg); font-weight: 600; }
ul, ol { margin: 0.6rem 0; padding-left: 1.8rem; }
li { margin: 0.25rem 0; }
hr { border: none; border-top: 1px solid var(--border); margin: 2rem 0; }
strong { font-weight: 600; }
.section { border-top: 1px solid var(--border); padding-top: 1.5rem; margin-top: 2rem; }
.file-label { font-size: 0.8rem; color: var(--muted); margin-bottom: 0.5rem; }
.generated { text-align: center; color: var(--muted); font-size: 0.8rem; margin-top: 3rem;
             padding: 1rem; border-top: 1px solid var(--border); }
@media (max-width: 768px) {
  nav { position: static; width: 100%; height: auto; border-right: none;
        border-bottom: 1px solid var(--border); }
  main { margin-left: 0; padding: 1rem; }
}
@media print { nav { display: none; } main { margin-left: 0; } }
"""


def generate_report(output_dir, output_file=None):
    """Generate a single-file HTML report from a findings directory.

    Args:
        output_dir: Path to the findings directory
        output_file: Optional output HTML path (default: output_dir/report.html)

    Returns:
        Path to the generated HTML file
    """
    output_dir = Path(output_dir)
    if not output_dir.is_dir():
        print(f"Error: Directory not found: {output_dir}", file=sys.stderr)
        sys.exit(1)

    if output_file is None:
        output_file = output_dir / "report.html"
    else:
        output_file = Path(output_file)

    # Discover and sort Markdown files
    md_files = sorted(
        f for f in output_dir.iterdir()
        if f.suffix == '.md' and f.name != '_index.md'
    )

    # Put _index.md first if it exists
    index_file = output_dir / '_index.md'
    if index_file.exists():
        md_files.insert(0, index_file)

    if not md_files:
        print(f"Error: No Markdown files found in {output_dir}", file=sys.stderr)
        sys.exit(1)

    # Read topic from .topic file or directory name
    topic_file = output_dir / '.topic'
    if topic_file.exists():
        topic = topic_file.read_text(encoding='utf-8').strip()
    else:
        topic = output_dir.name

    # Build navigation and content
    nav_items = []
    sections = []

    for md_file in md_files:
        content = md_file.read_text(encoding='utf-8')
        file_id = md_file.stem
        file_html = md_to_html(content)

        # Extract first h1 as section title, or use filename
        h1_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
        title = h1_match.group(1) if h1_match else md_file.stem

        nav_items.append(f'<a href="#{file_id}">{html.escape(md_file.name)}</a>')
        sections.append(
            f'<div class="section" id="{file_id}">'
            f'<div class="file-label">{html.escape(md_file.name)}</div>'
            f'{file_html}</div>'
        )

    nav_html = '\n'.join(nav_items)
    content_html = '\n'.join(sections)
    title_escaped = html.escape(topic)

    report = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_escaped} — Auto-Explorer Report</title>
<style>{CSS}</style>
</head>
<body>
<nav>
<h2>Auto-Explorer</h2>
<p style="margin-bottom:1rem;color:var(--muted);font-size:0.8rem">{title_escaped}</p>
{nav_html}
</nav>
<main>
{content_html}
<div class="generated">Generated by Auto-Explorer HTML Export</div>
</main>
</body>
</html>"""

    output_file.write_text(report, encoding='utf-8')
    return output_file


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: export-html.py <output_dir> [output_file]", file=sys.stderr)
        sys.exit(1)

    out_dir = sys.argv[1]
    out_file = sys.argv[2] if len(sys.argv) > 2 else None
    result = generate_report(out_dir, out_file)
    print(f"Report generated: {result}")
