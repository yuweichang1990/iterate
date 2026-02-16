---
description: "Show Auto-Explorer session dashboard"
allowed-tools:
  - "Bash(python *history.py show:*)"
hide-from-slash-command-tool: "true"
---

# Auto-Explorer Status Dashboard

Run the history dashboard script:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/history.py" show
```

Display the output to the user as-is (it's pre-formatted). Do not modify or reformat it.

If the user asks for more details about a specific session, read the `_index.md` file from that session's output directory (shown in `auto-explore-findings/<slug>/`).
