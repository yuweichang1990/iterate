---
name: quickstart
description: "Practical focus — get up and running fast with working examples"
mode: research
---

Quickstart guide: {{TOPIC}}

You are creating a practical, hands-on guide. Focus on getting the reader productive as quickly as possible. Theory should be minimal — only enough to understand the "why" behind each step.

## Structure your exploration as follows:

1. **Setup** (iteration 1): Installation, prerequisites, environment setup
2. **Hello World** (iteration 2): Simplest possible working example, explained line by line
3. **Core Patterns** (iteration 3-4): The 3-5 patterns that cover 80% of real usage
4. **Common Tasks** (iteration 5-6): How to do the things people actually need (with code)
5. **Troubleshooting** (iteration 7): Common errors, debugging tips, FAQ
6. **Next Steps** (iteration 8+): Where to go for deeper learning, recommended resources

Every file should include runnable code examples where possible.
Prefer "show, don't tell" — lead with code, then explain.

Write findings to {{OUTPUT_DIR}}/. Start with 00-overview.md for a brief overview.
Each iteration, write a numbered file (01-<subtopic>.md, 02-<subtopic>.md, etc.).
Update {{OUTPUT_DIR}}/_index.md each iteration.

Always end your response with:
<explore-next>specific sub-topic to explore next</explore-next>
