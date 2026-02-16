---
name: comparison
description: "Structured side-by-side comparison with evaluation criteria and verdict"
mode: research
---

Structured comparison: {{TOPIC}}

You are conducting a rigorous, structured comparison. Parse the topic to identify the options being compared (e.g., "React vs Vue vs Svelte" → 3 options). If the topic doesn't clearly contain "vs" or comparison language, treat it as a comparison of the top alternatives in that space.

## Phased structure:

### Phase 1: Evaluation Framework (iteration 1)
Write `{{OUTPUT_DIR}}/00-comparison-framework.md`:
- Define 8-12 evaluation criteria with clear descriptions and weighting
- Criteria should cover: learning curve, performance, ecosystem, community, documentation, flexibility, enterprise readiness, developer experience
- Explain the scoring rubric (1-5 scale with anchors)

### Phase 2: Individual Analysis (one iteration per option)
For each option being compared, write a dedicated analysis file:
- Overview and philosophy
- Strengths (with concrete evidence: benchmarks, adoption stats, examples)
- Weaknesses (with concrete evidence)
- Best suited for (specific use cases)
- Community and ecosystem (libraries, tools, job market)
- Performance characteristics (with data where possible)

### Phase 3: Head-to-Head (one iteration)
Write a head-to-head comparison file:
- Comparison matrix table (criteria x options, scored 1-5)
- Winner per category with reasoning
- Total weighted scores
- Key trade-offs explained

### Phase 4: Recommendation (final iteration)
Write a recommendation file:
- Overall verdict with clear reasoning
- "Choose X if..." decision guide for different use cases
- Migration considerations (if switching from one to another)
- Future outlook for each option

Write findings to {{OUTPUT_DIR}}/. Update {{OUTPUT_DIR}}/_index.md each iteration.

Always end your response with:
<explore-next>specific comparison aspect to analyze next</explore-next>
