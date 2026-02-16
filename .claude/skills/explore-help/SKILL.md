---
description: "Explain Auto-Explorer plugin and available commands"
hide-from-slash-command-tool: "true"
---

# Auto-Explorer Help

## What is Auto-Explorer?

Auto-Explorer is an autonomous exploration system for Claude Code. You describe a topic you're interested in, and Claude will:

1. **Self-direct research** across multiple iterations
2. **Write structured findings** as Markdown files in `auto-explore-findings/<topic>/`
3. **Dynamically choose** the next sub-topic each round using `<explore-next>` tags
4. **Update your interest profile** in `~/.claude/user-interests.md` automatically
5. **Stop automatically** when account usage reaches the budget threshold

## Available Commands

### `/auto-explore [TOPIC] [OPTIONS]`
Start an autonomous exploration session.

**Arguments:**
- `TOPIC` — The subject to explore (optional; if omitted, picks from your suggested interests)

**Options:**
- `--budget conservative|moderate|aggressive` — Account usage threshold (when to stop):
  - `conservative` = stop at 40% account usage
  - `moderate` = stop at 60% account usage (default)
  - `aggressive` = stop at 80% account usage
- `--mode research|build` — Force mode instead of auto-detecting from topic wording
- `--max-iterations N` — Optional hard cap on iterations (default: unlimited)

**Examples:**
```
/auto-explore Rust async programming
/auto-explore --budget conservative WebAssembly
/auto-explore --budget aggressive distributed consensus algorithms
/auto-explore --max-iterations 30 Go generics
/auto-explore --mode research build system internals
/auto-explore
```

### `/cancel-explore`
Cancel the currently running exploration loop.

### `/explore-status`
Show the session dashboard — active session, today's sessions, and recent history.

### `/explore-help`
Show this help message.

## Modes

Auto-Explorer auto-detects the mode from your topic wording:

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Research** | Concepts, subjects, questions (e.g., "Rust async programming") | Writes research findings as Markdown reports |
| **Build** | Action verbs (e.g., "build a REST API", "fix the auth bug") | Writes working code, then autonomously enhances it |

**Build mode** has three phases:
1. **Core Implementation** — Complete the requested task
2. **Engineering Enhancement** — Fix bugs, improve robustness, add tests
3. **Product & Strategy** — Evaluate UX friction, onboarding, and competitive positioning

## How It Works

1. **Setup**: `/auto-explore` initializes a state file at `.claude/auto-explorer.local.md` (includes auto-detected mode)
2. **Exploration Loop**: Each iteration, Claude works on the current sub-topic/sub-task, writes output, and emits an `<explore-next>` tag
3. **Stop Hook**: When Claude finishes a response, the stop hook:
   - Checks account usage against rate limits (4h / daily / weekly windows)
   - If any window exceeds the budget threshold → stops exploration
   - Otherwise, reads the `<explore-next>` tag and feeds it as the next prompt (mode-aware)
4. **Dynamic Steering**: Each round's direction is determined by Claude's analysis, not a static repeated prompt
5. **Rate Limit Control**: The primary stopping mechanism. Configured in `~/.claude/auto-explorer-limits.json`
6. **Completion Signal**: In build mode, Claude outputs `<explore-done>` when the task is genuinely finished and no more enhancements are worth making

## Rate Limits

Rate limits are configured in `~/.claude/auto-explorer-limits.json` with three windows:
- **4h** — Session-level token cap (from transcript)
- **daily** — Daily token cap (from stats-cache.json)
- **weekly** — Weekly token cap (from stats-cache.json)

The `--budget` flag controls what percentage triggers a stop:
| Budget | Threshold | Meaning |
|--------|-----------|---------|
| conservative | 40% | Stop early, preserve most of your quota |
| moderate | 60% | Balanced (default) |
| aggressive | 80% | Use most of your quota for exploration |

## Output

Output is written to `auto-explore-findings/<topic>/` in the current working directory:

**Research mode:**
- `00-overview.md` — Initial topic overview
- `01-<subtopic>.md`, `02-<subtopic>.md`, ... — Per-iteration findings
- `_index.md` — Running summary, updated each iteration
- `summary.md` — Final summary (if `--max-iterations` set)

**Build mode:**
- Code is written to the working directory (not the findings folder)
- `00-plan.md` — Architecture plan and task breakdown
- `01-<task>.md`, `02-<task>.md`, ... — Per-iteration progress logs
- `_index.md` — Running progress overview, updated each iteration

## Recommended Usage

```bash
# Start Claude Code with no permission prompts for autonomous mode
claude --dangerously-skip-permissions

# Then start exploring
/auto-explore Rust async programming
```

## Links

- Rate limit config: `~/.claude/auto-explorer-limits.json`
- Interest file: `~/.claude/user-interests.md`
- State file: `.claude/auto-explorer.local.md`
- Session history: `auto-explore-findings/.history.json`
- Findings: `auto-explore-findings/<topic>/`
