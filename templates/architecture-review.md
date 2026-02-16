---
name: architecture-review
description: "Structural analysis of a codebase — dependencies, patterns, risks"
mode: research
---

Architecture review: {{TOPIC}}

You are conducting a thorough architectural analysis of the codebase in the current working directory. Examine structure, patterns, dependencies, and quality.

## Structure your exploration as follows:

1. **Overview** (iteration 1): Project structure, entry points, tech stack, build system
2. **Dependency Analysis** (iteration 2): External dependencies, version health, supply chain risks
3. **Architecture Patterns** (iteration 3): Design patterns used, layering, separation of concerns
4. **Data Flow** (iteration 4): How data moves through the system — inputs, transformations, outputs
5. **Error Handling** (iteration 5): Error propagation, recovery strategies, failure modes
6. **Testing** (iteration 6): Test coverage, test quality, testing patterns, gaps
7. **Security** (iteration 7): Authentication, authorization, input validation, secrets management
8. **Performance** (iteration 8): Bottlenecks, caching, concurrency, resource usage
9. **Maintainability** (iteration 9): Code complexity, documentation, onboarding friction
10. **Recommendations** (iteration 10+): Prioritized improvement plan with effort estimates

Read actual source files in the working directory. Reference specific files and line numbers.
Be honest about both strengths and weaknesses.

Write findings to {{OUTPUT_DIR}}/. Start with 00-overview.md for a structural overview.
Each iteration, write a numbered file (01-<subtopic>.md, 02-<subtopic>.md, etc.).
Update {{OUTPUT_DIR}}/_index.md each iteration.

Always end your response with:
<explore-next>specific aspect to analyze next</explore-next>
