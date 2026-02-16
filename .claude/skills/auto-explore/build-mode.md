# Build Mode Behavior

Each iteration, you must:

1. **Read the state file** `.claude/auto-explorer.local.md` for current topic, iteration, and output dir.

2. **Work on the current sub-task**:
   - Write or modify code files in the working directory (NOT in auto-explore-findings/)
   - Use all available tools: Read, Write, Edit, Bash, Glob, Grep
   - Run tests, linters, or build commands as needed
   - Fix errors encountered along the way

3. **Observe and reflect** — before deciding what to do next, ask yourself:
   - What did I discover while working? Any unexpected issues, failures, or insights?
   - Does the original plan (`00-plan.md`) still make sense given what I now know?
   - Should the next step be what I originally planned, or has something changed?
   - If the plan needs adjustment, adapt — don't follow a broken plan blindly.

4. **Write a progress log** to the output directory:
   - First iteration: Write `00-plan.md` with architecture plan and initial task breakdown (this is a starting direction, NOT a fixed checklist)
   - Subsequent iterations: Write `NN-<task-slug>.md` (e.g., `01-setup-project.md`) — brief log of what was done, decisions made, issues encountered, and **what you observed that may affect later steps**
   - Keep logs concise (not full code dumps — the code is in the working directory)

5. **Update `_index.md`** in the output directory every iteration:
   - List all tasks completed so far with status (done/in-progress/planned)
   - Include a "Current State" section: what works, what doesn't, what's next
   - If the plan has deviated from `00-plan.md`, note why
   - This ensures there's always an up-to-date progress overview even if the loop stops unexpectedly

6. **Update user interests**: Silently update `~/.claude/user-interests.md` with technologies and patterns used.

7. **Decide the next step based on what you observed**, not by mechanically following the plan:
     ```
     <explore-next>specific next sub-task based on current state</explore-next>
     ```
   The `00-plan.md` is an initial direction. If your observations suggest a different priority, follow your judgment.

## Build Mode Phases

Build mode has three phases. You transition automatically — no user input needed.

**Phase 1: Core Implementation**
Complete the user's original request. The first iteration writes `00-plan.md` as an initial direction, but this is NOT a fixed checklist. Each iteration, observe what happened, learn from it, and decide the next step accordingly. The plan may evolve as you discover new information — that's expected and desirable.

**Phase 2: Engineering Enhancement**
Once the core task is done, do NOT output `<explore-done>`. Instead:
1. Review the entire codebase/feature you just built
2. Evaluate potential enhancements — ask yourself:
   - Is this enhancement **worth the added complexity**?
   - Does it genuinely improve the code/feature, or is it just busywork?
   - Would a senior engineer approve this change in code review?
3. If you find worthwhile enhancements → **implement them**, one per iteration. Output:
   ```
   <explore-next>enhance: [specific enhancement description]</explore-next>
   ```
4. Keep code and documentation in sync — every code change must update related docs/comments
5. When no more engineering enhancements are worth making → transition to Phase 3

**CRITICAL: Listing findings is NOT the same as fixing them.**
Do NOT list improvements as "future work" or "candidates for a future iteration" and then stop. If you judged an improvement to be genuinely valuable, implement it in the next iteration. The whole point of Phase 2 is that YOU do the work — not that you hand the user a TODO list. Only skip an improvement if it is truly not worth the complexity.

**Engineering enhancement criteria (in priority order):**
- Bug fixes and edge case handling
- Error handling and robustness
- Performance improvements with clear impact
- Code quality: reduce duplication, improve naming, simplify logic
- Missing tests for critical paths
- User-facing improvements (better messages, validation, defaults)

**What is NOT worth enhancing:**
- Adding features nobody asked for
- Over-abstracting for hypothetical future use
- Cosmetic changes (reformatting, reordering imports)
- Adding comments to self-explanatory code
- Backwards-compatibility shims for code you just wrote

**Phase 3: Product & Strategy**
Once engineering is solid, shift perspective from engineer to product thinker. Ask yourself:

1. **User experience friction**: Are there pain points in the workflow that could be smoothed out? Think about the first-time user, the power user, and the user who hits an error.
2. **Emotional impact**: Would this change make users *feel* the tool is polished and cares about them? Small touches (helpful defaults, clear error recovery, progressive disclosure) build trust.
3. **Competitive positioning**: What would make a user choose this tool over doing the task manually or using an alternative? What's the "wow" moment?
4. **Onboarding & discoverability**: Can a new user go from install to value in under 2 minutes? Are features discoverable without reading docs?
5. **Retention signals**: After using the tool once, what would make users come back? What would make them recommend it?

**Product enhancement criteria (in priority order):**
- Reducing friction in the most common workflows
- Better defaults that work for 80% of users without configuration
- Clearer feedback loops (users should always know what happened, why, and what to do next)
- Graceful degradation (when things go wrong, guide users to recovery instead of dead-ending)
- Progressive disclosure (simple by default, powerful when needed)
- Delight moments (small unexpected touches that signal quality)

**What is NOT worth adding for product reasons:**
- Features that serve <5% of users but complicate the experience for everyone
- Dashboard/analytics that nobody will check regularly
- Configurability that creates decision paralysis
- "Me too" features copied from other tools without clear user need

Only output `<explore-done>` when you genuinely cannot find any enhancement — engineering OR product — worth the added complexity.

## Build Mode Rules
- **Actually build working code** — don't just describe what to do
- **Iterate incrementally** — each round should produce a working (or closer to working) state
- **Test as you go** — run the code, fix errors, verify behavior
- **The output directory is for logs only** — real code goes in the working directory
- **Enhancement = code + docs** — every code change in Phase 2 must also update related documentation
- **Do the work, don't delegate it to the user** — if you identify a worthwhile fix, implement it yourself in the next iteration. Never label something "genuinely valuable" and then leave it as "future work"
