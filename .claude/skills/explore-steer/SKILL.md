---
description: "Steer active Auto-Explorer session in a new direction"
argument-hint: "<direction>"
allowed-tools:
  - "Bash(test -f .claude/auto-explorer.local.md:*)"
  - "Write(.claude/auto-explorer-steer.md)"
  - "Read(.claude/auto-explorer.local.md)"
hide-from-slash-command-tool: "true"
---

# Steer Auto-Explorer

Redirect the current exploration session without cancelling it. The direction change takes effect on the **next** iteration.

## Steps

1. Check if an auto-explorer session is active:
   ```bash
   test -f .claude/auto-explorer.local.md
   ```

2. If **active**: Write the user's direction to the steer file. The stop hook will consume it on the next iteration.
   - Read `.claude/auto-explorer.local.md` to show current topic and iteration
   - Write the user's argument text to `.claude/auto-explorer-steer.md`
   - Confirm to the user: "Direction change queued. It will take effect on the next iteration."
   - Show what was written and the current topic for context

3. If **not active**: Inform the user that no session is running. Suggest `/auto-explore <topic>` to start one.

## Argument

The `$ARGUMENTS` text is the direction change the user wants. Examples:
- `/explore-steer Focus more on practical examples`
- `/explore-steer Skip theory, go straight to benchmarks`
- `/explore-steer 請專注在效能比較`

If no argument is provided, ask the user what direction they want to steer toward.
