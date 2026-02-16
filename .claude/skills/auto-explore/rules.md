# Common Rules (Both Modes)

- **Be substantive**: Each iteration should produce real, useful output — not filler
- **Build on previous iterations**: Reference and connect to earlier work
- **Be specific in `<explore-next>`**: Concrete sub-topic/sub-task, not a vague direction
- **End every response with a tag**: Either `<explore-next>` or `<explore-done>` (the stop hook depends on it)
- **Stay on topic**: Keep related to the main topic, but explore interesting tangents

## Completion Signal: `<explore-done>`

Use `<explore-done>` instead of `<explore-next>` to signal that there is **genuinely nothing left worth doing**:

```
<explore-done>Core task complete. Enhancements applied: [list]. No further improvements worth the complexity.</explore-done>
```

The stop hook will detect this tag and gracefully end the session.

**When to use:**
- **Build mode**: Core task done AND no more enhancements worth the added complexity
- **Research mode**: The topic has been exhaustively covered (rare — there's almost always more to explore)

**When NOT to use:**
- There are known remaining sub-tasks or bugs
- Tests are failing or code has errors
- You haven't evaluated potential enhancements yet (build mode)
- You just want to stop because you feel like it
