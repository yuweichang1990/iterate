# ADR 0002: Dual-Lens Exploration Template

**Status**: Accepted
**Date**: 2026-02-17

## What Problem Are We Solving?

The interest graph (v1.8.0+) suggests topics based on past interests via Thompson Sampling. While it has anti-bubble mechanisms (gap detection, serendipity bonus, decay), it fundamentally only operates within *known* concepts. The best solution to a problem might lie entirely outside the user's existing knowledge graph.

This is the classic **exploit vs. explore** dilemma: System A (exploit) leverages what you already know, but System B (explore) deliberately ignores it. Without System B, you're trapped in a filter bubble of your own past interests.

## What Are We Building?

A new exploration template (`dual-lens`) that implements a dual-system approach:

| System | Purpose | Technique |
|--------|---------|-----------|
| System A (Exploit) | Leverage existing knowledge graph | Connected insights, adjacent-possible |
| System B (Explore) | Deliberately ignore the graph | Cross-domain analogies, contrarian thinking, first-principles |
| Synthesis Layer | Evaluate all proposals rigorously | 2-gate filter + 6-dimension scoring |

### Phase Structure (~10 iteration budget)

| Phase | Iterations | Purpose |
|-------|-----------|---------|
| 1: Framing | 1 | Define problem, success criteria, evaluation rubric |
| 2: System A | 2-4 | Exploit existing knowledge |
| 3: System B | 5-7 | Fresh exploration from scratch |
| 4: Synthesis | 8+ | Strict evaluation, verdict, roadmap |

## Key Decisions

### 1. Equal iteration budgets for System A and B

Both systems get 3 iterations each. This prevents exploit-dominance — without enforcement, the familiar System A would naturally consume more time and attention.

Why: The whole point is to break filter bubbles. If System A gets 80% of the budget, System B proposals are half-baked and get rejected in synthesis.

### 2. Strict 2-gate synthesis (not a free-form summary)

The synthesis layer uses binary gates (Applicability, Feasibility) before scoring. This prevents System B's creative proposals from being dismissed with "that's interesting but..." — they must fail on concrete criteria or they advance.

Why: Without gates, there's a bias toward familiar proposals. Binary gates force explicit reasoning about why something fails.

### 3. `{{GRAPH_BRIEF}}` placeholder with lazy evaluation

The template uses a new `{{GRAPH_BRIEF}}` placeholder that's only resolved when the template contains it. This means:
- Zero overhead for other templates
- The setup script calls `interest_graph.py graph-brief` only when needed
- Falls back to "(No interest graph data available)" if the graph is empty

Why: Not all templates need the interest graph. Lazy evaluation keeps the common path fast.

### 4. System B explicitly told to ignore the brief

The template instructs System B to "deliberately ignore the Knowledge Brief above" and "pretend the user has no prior knowledge graph." This is a prompt-level enforcement — Claude can see the brief but is instructed not to use it.

Why: We can't technically hide the brief from System B (it's in the same context), but explicit instructions work well with LLMs. The 3 different techniques (analogies, contrarian, first-principles) also naturally pull thinking away from the knowledge graph.

### 5. Evidence requirements on both systems

Both System A and System B proposals must cite concrete evidence. System A cites which existing knowledge it builds on; System B cites the reasoning technique and why it might succeed where conventional thinking fails.

Why: Without evidence requirements, System B proposals tend to be speculative hand-waving. Requiring evidence forces intellectual rigor on both sides.

## What Could Go Wrong?

| Risk | Mitigation |
|------|-----------|
| System B produces impractical proposals | Gate 1 (Applicability) and Gate 2 (Feasibility) filter them out explicitly |
| System A dominates synthesis despite equal budgets | Scoring includes "Novelty" dimension that favors System B; the verdict must track which system produced winners |
| Empty interest graph makes System A useless | Falls back to "(No interest graph data available)" — System A can still work from general knowledge |
| Template is too rigid for <10 iteration sessions | Phase boundaries are advisory ("iterations 2-4"), not enforced — Claude can adapt |
| `generate_brief()` is slow on large graphs | Community detection and gap finding already have safeguards (max_nodes in find_gaps) |

## Files Changed

| File | Change |
|------|--------|
| `templates/dual-lens.md` | **New** — The template itself |
| `scripts/interest_graph.py` | Added `generate_brief()` function + `graph-brief` CLI |
| `scripts/setup-auto-explorer.sh` | Added `{{GRAPH_BRIEF}}` placeholder substitution |
| `scripts/improvement_engine.py` | Added `"dual-lens"` to template list |
| `tests/test_dual_lens.py` | **New** — Template + graph-brief tests |
| `tests/test_templates.py` | Added dual-lens + comparison to `_load_all()` |
