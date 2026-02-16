# Research Mode Behavior

Each iteration, you must:

1. **Read the state file** `.claude/auto-explorer.local.md` for current topic, iteration, and output dir.

2. **Research the current sub-topic** thoroughly:
   - Use web search, code analysis, or any available tools
   - Think deeply about the topic
   - Connect it to related concepts

3. **Write findings** to the output directory:
   - First iteration: Write `00-overview.md` with a broad topic overview
   - Subsequent iterations: Write `NN-<subtopic-slug>.md` (e.g., `01-memory-model.md`)
   - Each file: well-structured Markdown with headers, examples, and key takeaways

4. **Update `_index.md`** in the output directory every iteration:
   - List all files written so far with one-line summaries
   - Include a "Key Findings So Far" section (3-5 bullet points, updated each round)
   - This ensures there's always an up-to-date summary even if the loop stops unexpectedly

5. **Update user interests**: Silently update `~/.claude/user-interests.md` with new keywords and concepts.

6. **Output next direction**:
```
<explore-next>specific sub-topic or question to explore next</explore-next>
```
