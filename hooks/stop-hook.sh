#!/bin/bash

# Auto-Explorer Stop Hook
# Prevents session exit when an auto-explorer session is active
# Primary stop: rate limit threshold (account usage %)
# Secondary stop: max_iterations hard cap (if set)

set -euo pipefail

# Quick Python check — stop hook must not crash, so just allow exit on failure
if ! python -c "import sys; sys.exit(0 if sys.version_info >= (3, 6) else 1)" 2>/dev/null; then
  echo "Auto-Explorer: Python 3.6+ not found — stopping exploration." >&2
  exit 0
fi

# Delimiter for Python→bash data passing.
# IMPORTANT: Must NOT be a whitespace character (tab, space).
# Bash `read` strips leading whitespace IFS chars, which silently
# misaligns fields when the first field is empty (e.g., explore-done
# is empty but explore-next has a value → next gets assigned to done).
# Unit separator (0x1F) is safe: non-printable, non-whitespace.
SEP=$'\x1f'

# Read hook input from stdin (advanced stop hook API)
HOOK_INPUT=$(cat)

# NOTE: We intentionally do NOT check stop_hook_active here.
# The old check caused the loop to break after just one continuation:
# when Claude's response was triggered by a stop hook, the next invocation
# saw stop_hook_active=true and exited, killing the multi-iteration loop.
# Infinite loops are already prevented by: max_iterations, rate limits,
# <explore-done> tag, and state file existence checks below.

# Resolve script directory for helpers.py and history.py calls
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Check if auto-explorer is active
STATE_FILE=".claude/auto-explorer.local.md"

if [[ ! -f "$STATE_FILE" ]]; then
  # No active session - allow exit
  exit 0
fi

# Parse all frontmatter fields via helpers.py
PARSED=$(python "$SCRIPT_DIR/scripts/helpers.py" parse-frontmatter "$STATE_FILE" "$SEP" 2>/dev/null)

if [[ -z "$PARSED" ]]; then
  echo "Auto-Explorer: Failed to parse state file" >&2
  echo "   Stopping exploration. Use /auto-explore to start fresh." >&2
  rm -f "$STATE_FILE"
  exit 0
fi

# Split values into variables using unit separator
IFS="$SEP" read -r ITERATION MAX_ITERATIONS THRESHOLD TOPIC TOPIC_SLUG OUTPUT_DIR MODE STARTED_AT <<< "$PARSED"

# Defaults
if [[ -z "$THRESHOLD" ]]; then THRESHOLD="0.6"; fi
if [[ -z "$MODE" ]]; then MODE="research"; fi

# Validate numeric fields
if [[ ! "$ITERATION" =~ ^[0-9]+$ ]]; then
  echo "Auto-Explorer: State file corrupted (iteration: '$ITERATION')" >&2
  echo "   Stopping exploration. Use /auto-explore to start fresh." >&2
  rm -f "$STATE_FILE"
  exit 0
fi

if [[ ! "$MAX_ITERATIONS" =~ ^[0-9]+$ ]]; then
  echo "Auto-Explorer: State file corrupted (max_iterations: '$MAX_ITERATIONS')" >&2
  echo "   Stopping exploration. Use /auto-explore to start fresh." >&2
  rm -f "$STATE_FILE"
  exit 0
fi

# Count output files for summary messages (trim wc -l whitespace)
count_output_files() {
  local dir="$1"
  if [[ -d "$dir" ]]; then
    find "$dir" -maxdepth 1 -name '*.md' -not -name '_index.md' 2>/dev/null | wc -l | tr -d ' '
  else
    echo "0"
  fi
}

# Format session duration from started_at (passed as $1, not re-read from file)
get_session_duration() {
  local started_at="${1:-}"
  if [[ -n "$started_at" ]]; then
    python "$SCRIPT_DIR/scripts/helpers.py" format-duration "$started_at" 2>/dev/null || echo "?"
  else
    echo "?"
  fi
}

# Get transcript path from hook input (moved early for session stats)
TRANSCRIPT_PATH=$(echo "$HOOK_INPUT" | python "$SCRIPT_DIR/scripts/helpers.py" extract-json-field transcript_path 2>/dev/null)

HAVE_TRANSCRIPT=false
if [[ -n "$TRANSCRIPT_PATH" ]] && [[ -f "$TRANSCRIPT_PATH" ]]; then
  HAVE_TRANSCRIPT=true
fi

# Compute session stats (tokens, files, output KB) for history tracking
EST_TOKENS="0"
FILES_WRITTEN="0"
OUTPUT_KB="0.0"
if [[ "$HAVE_TRANSCRIPT" == true ]]; then
  STATS=$(python "$SCRIPT_DIR/scripts/helpers.py" session-stats "$TRANSCRIPT_PATH" "$OUTPUT_DIR" "$SEP" 2>/dev/null || echo "0${SEP}0${SEP}0.0")
  IFS="$SEP" read -r EST_TOKENS FILES_WRITTEN OUTPUT_KB <<< "$STATS"
fi

# Check for summary-pending flag (auto-export: summary was just generated)
SUMMARY_FLAG=".claude/auto-explorer-summary-pending"
if [[ -f "$SUMMARY_FLAG" ]]; then
  DURATION=$(get_session_duration "$STARTED_AT")
  FILE_COUNT=$(count_output_files "$OUTPUT_DIR")
  DONE_REASON=$(cat "$SUMMARY_FLAG" 2>/dev/null || echo "completed")
  # Compute quality signals
  COMPLETION_TYPE="natural"
  BUDGET_ITERS=$(python "$SCRIPT_DIR/scripts/helpers.py" budget-iterations "$THRESHOLD" 2>/dev/null || echo "10")
  ITER_RATIO=$(python -c "print(round(int('$ITERATION')/max(int('$BUDGET_ITERS'),1),2))" 2>/dev/null || echo "0.5")
  OUTPUT_DENSITY=$(python -c "print(round(float('${OUTPUT_KB:-0}')/max(int('$ITERATION'),1),1))" 2>/dev/null || echo "0")
  python "$SCRIPT_DIR/scripts/history.py" end "$TOPIC_SLUG" "$ITERATION" "completed" "$DONE_REASON" \
    "$EST_TOKENS" "$FILES_WRITTEN" "$OUTPUT_KB" \
    "$COMPLETION_TYPE" "$ITER_RATIO" "$OUTPUT_DENSITY" "" 2>/dev/null || true
  python "$SCRIPT_DIR/scripts/interest_graph.py" decay 2>/dev/null || true
  # Auto-generate HTML report on completion
  HTML_REPORT=""
  if python "$SCRIPT_DIR/scripts/export-html.py" "$OUTPUT_DIR" 2>/dev/null; then
    HTML_REPORT="$OUTPUT_DIR/report.html"
  fi
  echo "Auto-Explorer: Task completed!"
  echo ""
  echo "   Topic:      $TOPIC"
  echo "   Mode:       $MODE"
  echo "   Iterations: $ITERATION"
  echo "   Duration:   $DURATION"
  echo "   Files:      $FILE_COUNT documents in $OUTPUT_DIR/"
  echo "   Tokens:     ~$EST_TOKENS output tokens (est.)"
  echo "   Summary:    $OUTPUT_DIR/summary.md"
  if [[ -n "$HTML_REPORT" ]]; then
  echo "   HTML:       $HTML_REPORT"
  fi
  echo ""
  echo "   Next steps: Review summary with 'cat $OUTPUT_DIR/summary.md'"
  rm -f "$STATE_FILE" "$SUMMARY_FLAG"
  exit 0
fi

# Check if max iterations reached (only if set > 0)
if [[ $MAX_ITERATIONS -gt 0 ]] && [[ $ITERATION -ge $MAX_ITERATIONS ]]; then
  DURATION=$(get_session_duration "$STARTED_AT")
  FILE_COUNT=$(count_output_files "$OUTPUT_DIR")
  # Compute quality signals
  COMPLETION_TYPE="budget_exhausted"
  BUDGET_ITERS=$(python "$SCRIPT_DIR/scripts/helpers.py" budget-iterations "$THRESHOLD" 2>/dev/null || echo "10")
  ITER_RATIO=$(python -c "print(round(int('$ITERATION')/max(int('$BUDGET_ITERS'),1),2))" 2>/dev/null || echo "0.5")
  OUTPUT_DENSITY=$(python -c "print(round(float('${OUTPUT_KB:-0}')/max(int('$ITERATION'),1),1))" 2>/dev/null || echo "0")
  python "$SCRIPT_DIR/scripts/history.py" end "$TOPIC_SLUG" "$ITERATION" "max-iterations" "Completed all $MAX_ITERATIONS iterations" \
    "$EST_TOKENS" "$FILES_WRITTEN" "$OUTPUT_KB" \
    "$COMPLETION_TYPE" "$ITER_RATIO" "$OUTPUT_DENSITY" "" 2>/dev/null || true
  python "$SCRIPT_DIR/scripts/interest_graph.py" decay 2>/dev/null || true
  echo "Auto-Explorer: Completed all $MAX_ITERATIONS iterations."
  echo ""
  echo "   Topic:      $TOPIC"
  echo "   Mode:       $MODE"
  echo "   Iterations: $ITERATION"
  echo "   Duration:   $DURATION"
  echo "   Files:      $FILE_COUNT documents in $OUTPUT_DIR/"
  echo "   Tokens:     ~$EST_TOKENS output tokens (est.)"
  echo ""
  echo ""
  echo "   Next steps:"
  echo "     - Review findings: cat $OUTPUT_DIR/_index.md"
  echo "     - Resume session:  /auto-explore --resume $TOPIC_SLUG"
  rm -f "$STATE_FILE"
  exit 0
fi

# --- Rate limit check (primary stopping mechanism) ---
# Skip rate check if transcript unavailable (allow this iteration, check next time)
RATE_SUMMARY="transcript unavailable"
if [[ "$HAVE_TRANSCRIPT" == true ]]; then
  RATE_CHECK=$(python "$SCRIPT_DIR/scripts/check-rate-limits.py" "$TRANSCRIPT_PATH" "$THRESHOLD" 2>/dev/null || echo '{"allowed":true}')

  # Extract allowed, detail, and summary via helpers.py
  RATE_PARSED=$(echo "$RATE_CHECK" | python "$SCRIPT_DIR/scripts/helpers.py" format-rate-summary "$SEP" 2>/dev/null || echo "yes${SEP}${SEP}")

  IFS="$SEP" read -r RATE_ALLOWED RATE_DETAIL RATE_SUMMARY <<< "$RATE_PARSED"

  if [[ "$RATE_ALLOWED" == "no" ]]; then
    DURATION=$(get_session_duration "$STARTED_AT")
    FILE_COUNT=$(count_output_files "$OUTPUT_DIR")
    # Compute quality signals
    COMPLETION_TYPE="rate_limited"
    BUDGET_ITERS=$(python "$SCRIPT_DIR/scripts/helpers.py" budget-iterations "$THRESHOLD" 2>/dev/null || echo "10")
    ITER_RATIO=$(python -c "print(round(int('$ITERATION')/max(int('$BUDGET_ITERS'),1),2))" 2>/dev/null || echo "0.5")
    OUTPUT_DENSITY=$(python -c "print(round(float('${OUTPUT_KB:-0}')/max(int('$ITERATION'),1),1))" 2>/dev/null || echo "0")
    python "$SCRIPT_DIR/scripts/history.py" end "$TOPIC_SLUG" "$ITERATION" "rate-limited" "Rate limit threshold reached" \
      "$EST_TOKENS" "$FILES_WRITTEN" "$OUTPUT_KB" \
      "$COMPLETION_TYPE" "$ITER_RATIO" "$OUTPUT_DENSITY" "" 2>/dev/null || true
    python "$SCRIPT_DIR/scripts/interest_graph.py" decay 2>/dev/null || true
    echo "Auto-Explorer: Rate limit reached — stopping exploration."
    echo ""
    echo "   Topic:      $TOPIC"
    echo "   Mode:       $MODE"
    echo "   Iterations: $ITERATION"
    echo "   Duration:   $DURATION"
    echo "   Files:      $FILE_COUNT documents in $OUTPUT_DIR/"
    echo "   Tokens:     ~$EST_TOKENS output tokens (est.)"
    echo ""
    echo "   Exceeded limits:"
    echo "$RATE_DETAIL"
    echo ""
    echo "   Next steps:"
    echo "     - Review findings: cat $OUTPUT_DIR/_index.md"
    echo "     - Adjust limits:   ~/.claude/auto-explorer-limits.json"
    echo "     - Resume session:  /auto-explore --resume $TOPIC_SLUG"
    rm -f "$STATE_FILE"
    exit 0
  fi
fi

# --- Tag extraction ---
# Extract explore-done/explore-next from last assistant message.
# If transcript is unavailable, skip tag extraction and use fallback prompt.
EXPLORE_DONE=""
NEXT_SUBTOPIC=""

if [[ "$HAVE_TRANSCRIPT" == true ]] && grep -q '"role":"assistant"' "$TRANSCRIPT_PATH" 2>/dev/null; then
  # Extract last assistant message text AND explore-done/explore-next tags
  TAGS=$(grep '"role":"assistant"' "$TRANSCRIPT_PATH" | tail -1 | python "$SCRIPT_DIR/scripts/helpers.py" extract-tags "$SEP" 2>/dev/null || echo "$SEP")

  IFS="$SEP" read -r EXPLORE_DONE NEXT_SUBTOPIC <<< "$TAGS"

  if [[ -n "$EXPLORE_DONE" ]]; then
    # Auto-export: inject summary generation prompt before ending
    echo "$EXPLORE_DONE" > "$SUMMARY_FLAG"

    if [[ "$MODE" == "build" ]]; then
      SUMMARY_PROMPT="Your build task '$TOPIC' is complete: $EXPLORE_DONE

Before ending, write a comprehensive summary report to $OUTPUT_DIR/summary.md.

## What to include:
1. **Overview** — What was built and why
2. **Architecture** — Key technical decisions and structure
3. **Deliverables** — List of all files created/modified with one-line descriptions
4. **Testing** — Test coverage and results
5. **Known limitations** — What could be improved in the future
6. **How to use** — Quick start instructions for the end result

Also update $OUTPUT_DIR/_index.md with the final state.

Do NOT include <explore-next> or <explore-done> tags — this is the final wrap-up."
    else
      SUMMARY_PROMPT="Your research on '$TOPIC' is complete: $EXPLORE_DONE

Before ending, write a comprehensive summary report to $OUTPUT_DIR/summary.md.

## What to include:
1. **Executive summary** — Key findings in 3-5 bullet points
2. **Topic coverage** — What areas were explored and key insights from each
3. **File index** — All research files with one-line descriptions
4. **Connections** — How different sub-topics relate to each other
5. **Open questions** — What remains unexplored or uncertain
6. **Recommended next steps** — Actionable suggestions for deeper exploration

Also update $OUTPUT_DIR/_index.md with the final state.

Do NOT include <explore-next> or <explore-done> tags — this is the final wrap-up."
    fi

    SYSTEM_MSG="Auto-Explorer FINAL SUMMARY | Mode: ${MODE} | Topic: $TOPIC | Writing summary.md before session ends"
    python "$SCRIPT_DIR/scripts/helpers.py" json-output "$SUMMARY_PROMPT" "$SYSTEM_MSG"
    exit 0
  fi
fi

# Fallback if no <explore-next> tag found (mode-aware)
if [[ -z "$NEXT_SUBTOPIC" ]]; then
  if [[ "$MODE" == "build" ]]; then
    NEXT_SUBTOPIC="Continue working on the next sub-task for: $TOPIC"
  else
    NEXT_SUBTOPIC="Explore a deeper or less-covered aspect of: $TOPIC"
  fi
fi

# --- Interactive steering ---
# Check if the user dropped a steer file to redirect the next iteration.
# The file is consumed (deleted) after reading — it's a one-time directive.
STEER_FILE=".claude/auto-explorer-steer.md"
STEER_MSG=""
if [[ -f "$STEER_FILE" ]]; then
  STEER_MSG=$(cat "$STEER_FILE" 2>/dev/null || echo "")
  rm -f "$STEER_FILE"
fi

# Continue loop - increment iteration
NEXT_ITERATION=$((ITERATION + 1))

# Determine the file number for this iteration (zero-padded)
FILE_NUM=$(printf "%02d" "$NEXT_ITERATION")

# Build iteration display
if [[ $MAX_ITERATIONS -gt 0 ]]; then
  ITER_DISPLAY="$NEXT_ITERATION / $MAX_ITERATIONS"
else
  ITER_DISPLAY="$NEXT_ITERATION (no cap)"
fi

# Build the next prompt (mode-aware)
if [[ "$MODE" == "build" ]]; then
  NEXT_PROMPT="Continue building '$TOPIC'. Iteration $ITER_DISPLAY.

Current sub-task: $NEXT_SUBTOPIC

Work on the code in the working directory. Write a brief progress log to $OUTPUT_DIR/$FILE_NUM-<descriptive-name>.md and update $OUTPUT_DIR/_index.md with current progress.

$(if [[ $MAX_ITERATIONS -gt 0 ]] && [[ $NEXT_ITERATION -eq $MAX_ITERATIONS ]]; then
  echo "THIS IS THE FINAL ITERATION. Wrap up any remaining work and write $OUTPUT_DIR/summary.md with a comprehensive summary of what was built."
fi)

Remember: End your response with <explore-next>next specific sub-task</explore-next> or <explore-done>reason</explore-done> if genuinely complete.
$(if [[ -n "$STEER_MSG" ]]; then
  echo ""
  echo "USER DIRECTION CHANGE: $STEER_MSG"
  echo "Adjust your work to follow this guidance."
fi)"
else
  NEXT_PROMPT="Continue exploring '$TOPIC'. Iteration $ITER_DISPLAY.

Current sub-topic to research: $NEXT_SUBTOPIC

Write your findings to $OUTPUT_DIR/$FILE_NUM-<descriptive-name>.md and update $OUTPUT_DIR/_index.md with current progress.

$(if [[ $MAX_ITERATIONS -gt 0 ]] && [[ $NEXT_ITERATION -eq $MAX_ITERATIONS ]]; then
  echo "THIS IS THE FINAL ITERATION. After writing your findings file, also write $OUTPUT_DIR/summary.md with a comprehensive summary of all exploration findings."
fi)

Remember: End your response with <explore-next>next specific sub-topic</explore-next>
$(if [[ -n "$STEER_MSG" ]]; then
  echo ""
  echo "USER DIRECTION CHANGE: $STEER_MSG"
  echo "Adjust your exploration to follow this guidance."
fi)"
fi

# Update iteration in state file (atomic update via temp file)
TEMP_FILE="${STATE_FILE}.tmp.$$"
if sed "s/^iteration: .*/iteration: $NEXT_ITERATION/" "$STATE_FILE" > "$TEMP_FILE" 2>/dev/null; then
  mv "$TEMP_FILE" "$STATE_FILE"
else
  # sed failed — clean up temp file and continue with stale iteration count
  rm -f "$TEMP_FILE"
fi

# Build system message
STEER_INDICATOR=""
if [[ -n "$STEER_MSG" ]]; then
  STEER_INDICATOR=" | STEERED by user"
fi
SYSTEM_MSG="Auto-Explorer iteration $ITER_DISPLAY | Mode: ${MODE:-research} | Topic: $TOPIC | Sub-topic: $NEXT_SUBTOPIC | Usage: $RATE_SUMMARY$STEER_INDICATOR"

# Output JSON to block the stop and feed the next prompt
python "$SCRIPT_DIR/scripts/helpers.py" json-output "$NEXT_PROMPT" "$SYSTEM_MSG"

exit 0
