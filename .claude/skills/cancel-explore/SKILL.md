---
description: "Cancel active Auto-Explorer session"
allowed-tools:
  - "Bash(test -f .claude/auto-explorer.local.md:*)"
  - "Bash(rm -f .claude/auto-explorer.local.md .claude/auto-explorer-summary-pending)"
  - "Bash(python *history.py end*)"
  - "Read(.claude/auto-explorer.local.md)"
hide-from-slash-command-tool: "true"
---

# Cancel Auto-Explorer

Check if an auto-explorer session is currently active by testing for the state file:

```bash
test -f .claude/auto-explorer.local.md
```

If the file exists:
1. Read `.claude/auto-explorer.local.md` to get the current iteration number, topic, and topic_slug
2. Record the cancellation in history:
   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/history.py" end "<topic_slug>" "<iteration>" "cancelled" "Cancelled by user"
   ```
3. Remove the state file and any pending summary flag:
   ```bash
   rm -f .claude/auto-explorer.local.md .claude/auto-explorer-summary-pending
   ```
4. Report to the user:
   - Confirm cancellation
   - Show which iteration it was on
   - Show the topic that was being explored
   - Mention that findings written so far are preserved in `auto-explore-findings/`

If the file does NOT exist:
- Inform the user that no auto-explorer session is currently active.
