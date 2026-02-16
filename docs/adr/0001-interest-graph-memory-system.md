# ADR 0001: Interest Graph & Memory System

**Status**: Accepted
**Date**: 2026-02-16

## What Problem Are We Solving?

Auto-Explorer tracks your interests in a simple Markdown file (`~/.claude/user-interests.md`). This works, but it has real limitations:

- **Everything is flat.** "Docker" and "Python" sit in a keyword list with no connections between them. We can't say "you like Docker AND CI/CD together."
- **Nothing fades.** A topic you explored 6 months ago has the same weight as one from yesterday. Your interest file just grows forever.
- **Suggestions are static.** The "Suggested Next Directions" section is a hand-written numbered list. It doesn't learn from what you actually choose to explore.
- **No feedback loop.** If we suggest "Kubernetes" 5 times and you never pick it, we keep suggesting it.

We researched solutions in `auto-explore-findings/1-memory-2-3-3/` and designed a 3-phase upgrade. This ADR covers Phase 1.

## What Are We Building?

### The Big Picture: 3-Phase Rollout

| Phase | Version | What It Adds |
|-------|---------|-------------|
| **1** | v1.8.0 | Interest graph with smart suggestions and decay (this ADR) |
| 2 | v1.9.0 | Improvement engine: template selection, budget tuning |
| 3 | v1.10.0 | Community detection, serendipity, prompt evolution |

### Phase 1: Interest Graph

Replace the flat keyword list with a structured graph (`~/.claude/interest-graph.json`):

```
Concepts:  docker ──related──> kubernetes
              │                    │
           broader              broader
              │                    │
              v                    v
         infrastructure      infrastructure
```

Each concept tracks:
- **Weight**: how much you care about it (decays over time with a 90-day half-life)
- **Relationships**: broader/narrower/related (like a lightweight ontology called SKOS)
- **Bandit state**: alpha/beta counters for Thompson Sampling (the algorithm that picks what to suggest next)
- **Co-occurrence edges**: "these two topics appeared in the same session"

## Key Decisions

### 1. Auto-migrate on first run

The first time `interest_graph.py` runs and finds no graph file, it automatically converts your existing `user-interests.md` into the new format. You don't have to do anything. Your ~170 keywords become structured concepts with categories and relationships intact.

Why: Manual migration steps get forgotten. Auto-migration means the feature just works.

### 2. Claude keeps updating Markdown, the stop hook syncs to the graph

We considered having Claude update the JSON graph directly (by changing the CLAUDE.md instructions). Instead, we chose to keep the existing flow: Claude updates `user-interests.md` as before, and the stop hook runs `interest_graph.py decay` after each session.

Why: Changing global CLAUDE.md instructions is risky and affects all conversations. The stop hook approach is safer and fully backward-compatible.

### 3. Graph lives at `~/.claude/interest-graph.json` (global)

The interest graph is per-user, not per-project. It lives next to `user-interests.md` in `~/.claude/`.

Why: Your interests follow you across projects. A project-local graph would fragment your interest data.

### 4. Thompson Sampling for suggestions

Instead of a static list, we use a bandit algorithm called Thompson Sampling. Each concept has an alpha (times you engaged) and beta (times you ignored it). The algorithm samples from Beta(alpha, beta) distributions to balance:
- **Exploitation**: suggesting topics you've liked before
- **Exploration**: giving less-tried topics a chance
- **Serendipity**: boosting under-connected concepts for novel discoveries

The result: suggestions get better the more you use Auto-Explorer.

### 5. Quality signals in session history

When a session ends, we now record how it went:
- **completion_type**: Did it finish naturally, hit the iteration cap, or get rate-limited?
- **iterations_vs_budget**: How much of the budget was used? (ratio like 0.8 = used 80%)
- **output_density**: How much content per iteration? (KB/iter)

These signals feed the improvement engine in Phase 2.

## What Could Go Wrong?

| Risk | Mitigation |
|------|-----------|
| Thompson Sampling starts cold (all priors are uniform) | Needs ~10 sessions to become useful. The serendipity bonus helps in the meantime. |
| Migration creates approximate co-occurrence edges (adjacent keywords, not real co-occurrence) | Good enough for bootstrapping. Real co-occurrences accumulate with actual use. |
| Graph file gets corrupted | Original `user-interests.md` is never deleted. You can always re-migrate. |
| Stop hook gets slightly slower | Decay is <5ms. Negligible compared to API calls. |

## Files Changed

| File | Change |
|------|--------|
| `scripts/interest_graph.py` | **New** — Core module: load, save, add concepts, decay, suggest, migrate, generate MD |
| `tests/test_interest_graph.py` | **New** — 44 tests across 10 test classes |
| `scripts/history.py` | Extended `cmd_end()` with 4 new optional args for quality signals |
| `scripts/helpers.py` | Added `budget-iterations` subcommand |
| `hooks/stop-hook.sh` | Quality signal computation + decay call in all 3 exit paths |
