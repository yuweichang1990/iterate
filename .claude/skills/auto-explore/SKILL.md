---
description: "Start Auto-Explorer in current session"
argument-hint: "[TOPIC] [--budget conservative|moderate|aggressive] [--mode research|build] [--max-iterations N]"
allowed-tools:
  - "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/setup-auto-explorer.sh:*)"
  - "Read"
  - "Write"
  - "Edit"
  - "Bash"
  - "WebSearch"
  - "WebFetch"
  - "Glob"
  - "Grep"
hide-from-slash-command-tool: "true"
---

# Auto-Explorer: Autonomous Exploration Session

First, run the setup script to initialize the exploration session:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/setup-auto-explorer.sh" $ARGUMENTS
```

If the setup script succeeds, begin the exploration loop. Follow these rules precisely:

## Step 0: Read Mode

Read `.claude/auto-explorer.local.md` — the setup script has already auto-detected the mode from the topic wording and stored it in the `mode:` field of the frontmatter.

- **`mode: research`** — The topic is a concept, subject, or question to learn about.
- **`mode: build`** — The topic is a task or feature to implement.

State which mode was detected in your first response and proceed accordingly. If the auto-detected mode seems wrong for the topic, you may override it (update the `mode:` field in the state file).

## Mode Behavior

- `mode: research` → Follow [research-mode.md](research-mode.md)
- `mode: build` → Follow [build-mode.md](build-mode.md)

## Common Rules

See [rules.md](rules.md)

## CRITICAL

- Every response MUST end with either `<explore-next>` or `<explore-done>`
- Do NOT try to exit by other means — the stop hook manages the lifecycle
- Each iteration should take a different angle, not repeat previous work
