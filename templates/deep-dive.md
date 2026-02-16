---
name: deep-dive
description: "Exhaustive research covering theory, practice, ecosystem, and edge cases"
mode: research
---

Deep-dive research: {{TOPIC}}

You are conducting exhaustive research on this topic. Cover it from every angle, going far beyond surface-level overviews.

## Structure your exploration as follows:

1. **Foundations** (iteration 1-2): Core concepts, history, and theoretical underpinnings
2. **Mechanics** (iteration 3-4): How it works internally — architecture, algorithms, data structures
3. **Ecosystem** (iteration 5-6): Tools, libraries, frameworks, and community resources
4. **Practice** (iteration 7-8): Real-world patterns, best practices, common pitfalls, and anti-patterns
5. **Advanced** (iteration 9-10): Edge cases, performance characteristics, scaling considerations
6. **Frontier** (iteration 11+): Current research, emerging trends, open problems, future directions

Write findings to {{OUTPUT_DIR}}/. Start with 00-overview.md for a broad overview.
Each iteration, write a numbered file (01-<subtopic>.md, 02-<subtopic>.md, etc.).
Update {{OUTPUT_DIR}}/_index.md each iteration with current progress.

Always end your response with:
<explore-next>specific sub-topic to explore next</explore-next>
