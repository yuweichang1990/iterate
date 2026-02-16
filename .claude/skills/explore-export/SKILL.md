---
description: "Export Auto-Explorer findings as a navigable HTML report"
argument-hint: "[session-slug]"
hide-from-slash-command-tool: "true"
---

# Export Auto-Explorer Findings to HTML

Generate a single-file HTML report from a session's Markdown findings — complete with sidebar navigation, dark/light mode, and responsive layout. Zero external dependencies.

## Steps

1. Determine which session to export:
   - If `$ARGUMENTS` contains a session slug, use `auto-explore-findings/<slug>/` as the source directory.
   - If `$ARGUMENTS` is empty, check for an active session in `.claude/auto-explorer.local.md` and use its `output_dir`.
   - If no active session, check `.history.json` for the most recent session and use its `output_dir`.
   - If still nothing found, inform the user and suggest: `/explore-export <session-slug>`

2. Run the export script:
   ```bash
   python "$PLUGIN_DIR/scripts/export-html.py" "<output_dir>"
   ```
   This generates `<output_dir>/report.html`.

3. Report the result:
   - Show the path to the generated HTML file
   - Show the number of Markdown files included
   - Suggest opening the file in a browser

## Examples

```
/explore-export                     # export active or most recent session
/explore-export rust-async          # export specific session
```

## Notes

- The HTML report is a single self-contained file (no external CSS/JS)
- Supports dark/light mode via `prefers-color-scheme`
- Mobile-responsive with collapsible sidebar
- `_index.md` is placed first in the report if it exists
- Print-friendly (sidebar hidden in print view)
