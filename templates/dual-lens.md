---
name: dual-lens
description: "Dual exploit/explore system — break filter bubbles with rigorous synthesis"
mode: research
---

Dual-lens exploration: {{TOPIC}}

You are running a dual-system exploration designed to break filter bubbles. Two independent systems will investigate this topic, then a strict synthesis layer evaluates all proposals.

## Your Knowledge Brief

{{GRAPH_BRIEF}}

---

## Phase 1: Framing (iteration 1)

Write `{{OUTPUT_DIR}}/00-framing.md`:

- Define the core problem or question precisely
- State 3-5 success criteria: what would a great answer look like?
- Define an evaluation rubric (impact, confidence, effort, novelty, risk, durability — each 1-5)
- Identify the user's inferred intent and constraints
- **Do NOT propose any solutions yet** — this phase is purely about framing

---

## Phase 2: System A — Exploit (iterations 2-4)

System A leverages your existing knowledge graph. Use the Knowledge Brief above as your starting point.

For each iteration, write `{{OUTPUT_DIR}}/NN-system-a-<aspect>.md`:

- **Iteration 2**: Connected insights — what does the knowledge graph suggest? What adjacent topics are relevant? What patterns from past explorations apply?
- **Iteration 3**: Adjacent-possible — what's one hop away from known concepts? What established solutions from related domains could work here?
- **Iteration 4**: Synthesis of System A findings — consolidate the 2 previous iterations into ranked proposals with evidence

Each System A proposal must cite:
- Which existing knowledge it builds on
- Concrete evidence (benchmarks, case studies, logical proofs)
- Confidence level (1-5) with reasoning

---

## Phase 3: System B — Explore (iterations 5-7)

System B **deliberately ignores** the Knowledge Brief above. Pretend the user has no prior knowledge graph. Think from scratch.

Each iteration uses a **different exploration technique**:

- **Iteration 5**: Cross-domain analogies — How do completely unrelated fields solve similar problems? (biology, economics, urban planning, game theory, etc.) Write `{{OUTPUT_DIR}}/NN-system-b-analogies.md`
- **Iteration 6**: Contrarian / inversion — What if the obvious approach is wrong? What would a critic say? What happens if we do the opposite? Write `{{OUTPUT_DIR}}/NN-system-b-contrarian.md`
- **Iteration 7**: First-principles — Strip away all assumptions. What are the fundamental constraints? Rebuild from axioms. Write `{{OUTPUT_DIR}}/NN-system-b-first-principles.md`

Each System B proposal must cite:
- The reasoning technique used
- Why this approach might succeed where conventional thinking fails
- Concrete evidence or logical argument (not just "what if")

**Important**: System B gets equal iteration budget (3 iterations) to prevent exploit-dominance.

---

## Phase 4: Synthesis (iterations 8+)

Write `{{OUTPUT_DIR}}/NN-synthesis.md` with a strict evaluation pipeline:

### Gate 1 — Applicability (binary)
For each proposal from both systems:
> "Does this address the problem AND the user's inferred intent (from Phase 1)?"
- YES → advance to Gate 2
- NO → DISCARD with one-line reason

### Gate 2 — Feasibility (binary)
For each surviving proposal:
> "Can this be done with available resources, skills, and timeline?"
- YES → advance to Scoring
- NO → DISCARD with one-line reason

### Scoring
Score each surviving proposal on 6 dimensions (1-5 each):
| Dimension | Description |
|-----------|-------------|
| Impact | How much does this move the needle on the success criteria? |
| Confidence | How sure are we this will work? (evidence quality) |
| Effort | How much work to implement? (5=easy, 1=massive) |
| Novelty | How fresh is this vs. obvious approaches? |
| Risk | How bad if it fails? (5=low risk, 1=catastrophic) |
| Durability | Will this still be relevant in 2-3 years? |

### Evidence Requirement
Each scored proposal must include:
- At least one data point, benchmark, or logical proof
- Source system (A or B) and which iteration produced it

### Risk Assessment
For the top 3-5 proposals (by total score):
- Identify the #1 failure mode
- Estimate probability of failure (low/medium/high)
- Describe the mitigation strategy
- Describe the fallback if mitigation fails

### Verdict
- Rank all surviving proposals by total weighted score
- Recommend top 1-3 for implementation
- Provide a concrete implementation roadmap (first steps, milestones, decision points)
- Note which system (A or B) produced the winning proposals — track whether the knowledge graph or fresh thinking won

Write findings to {{OUTPUT_DIR}}/. Update {{OUTPUT_DIR}}/_index.md each iteration.

Always end your response with:
<explore-next>specific aspect to investigate next</explore-next>
