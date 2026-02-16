#!/bin/bash

# Auto-Explorer Stop Hook
# Prevents session exit when an auto-explorer session is active
# Primary stop: rate limit threshold (account usage %)
# Secondary stop: max_iterations hard cap (if set)

set -euo pipefail

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

# Check if auto-explorer is active
STATE_FILE=".claude/auto-explorer.local.md"

if [[ ! -f "$STATE_FILE" ]]; then
  # No active session - allow exit
  exit 0
fi

# Parse all frontmatter fields in a single Python call
PARSED=$(python -c "
import sys
sep = sys.argv[2]
content = open(sys.argv[1], 'r', encoding='utf-8').read()
lines = content.split('\n')
in_fm = False
fields = {}
for line in lines:
    if line.strip() == '---':
        if in_fm: break
        in_fm = True
        continue
    if in_fm and ':' in line:
        key, val = line.split(':', 1)
        fields[key.strip()] = val.strip().strip('\"')
keys = ['iteration','max_iterations','threshold','topic','topic_slug','output_dir','mode']
print(sep.join(fields.get(k, '') for k in keys))
" "$STATE_FILE" "$SEP" 2>/dev/null)

if [[ -z "$PARSED" ]]; then
  echo "Auto-Explorer: Failed to parse state file" >&2
  echo "   Stopping exploration. Use /auto-explore to start fresh." >&2
  rm "$STATE_FILE"
  exit 0
fi

# Split values into variables using unit separator
IFS="$SEP" read -r ITERATION MAX_ITERATIONS THRESHOLD TOPIC TOPIC_SLUG OUTPUT_DIR MODE <<< "$PARSED"

# Defaults
if [[ -z "$THRESHOLD" ]]; then THRESHOLD="0.6"; fi
if [[ -z "$MODE" ]]; then MODE="research"; fi

# Validate numeric fields
if [[ ! "$ITERATION" =~ ^[0-9]+$ ]]; then
  echo "Auto-Explorer: State file corrupted (iteration: '$ITERATION')" >&2
  echo "   Stopping exploration. Use /auto-explore to start fresh." >&2
  rm "$STATE_FILE"
  exit 0
fi

if [[ ! "$MAX_ITERATIONS" =~ ^[0-9]+$ ]]; then
  echo "Auto-Explorer: State file corrupted (max_iterations: '$MAX_ITERATIONS')" >&2
  echo "   Stopping exploration. Use /auto-explore to start fresh." >&2
  rm "$STATE_FILE"
  exit 0
fi

# Resolve script directory for history.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Check if max iterations reached (only if set > 0)
if [[ $MAX_ITERATIONS -gt 0 ]] && [[ $ITERATION -ge $MAX_ITERATIONS ]]; then
  python "$SCRIPT_DIR/scripts/history.py" end "$TOPIC_SLUG" "$ITERATION" "max-iterations" "Completed all $MAX_ITERATIONS iterations" 2>/dev/null || true
  echo "Auto-Explorer: Completed all $MAX_ITERATIONS iterations on '$TOPIC'."
  echo "   Findings are in: $OUTPUT_DIR/"
  rm "$STATE_FILE"
  exit 0
fi

# Get transcript path from hook input
TRANSCRIPT_PATH=$(echo "$HOOK_INPUT" | python -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('transcript_path', ''))
" 2>/dev/null)

if [[ -z "$TRANSCRIPT_PATH" ]] || [[ ! -f "$TRANSCRIPT_PATH" ]]; then
  echo "Auto-Explorer: Transcript file not found" >&2
  echo "   Expected: $TRANSCRIPT_PATH" >&2
  echo "   Stopping exploration." >&2
  rm "$STATE_FILE"
  exit 0
fi

# --- Rate limit check (primary stopping mechanism) ---
RATE_CHECK=$(python "$SCRIPT_DIR/scripts/check-rate-limits.py" "$TRANSCRIPT_PATH" "$THRESHOLD" 2>/dev/null || echo '{"allowed":true}')

# Extract allowed, detail, and summary in a single Python call
RATE_PARSED=$(echo "$RATE_CHECK" | python -c "
import sys, json
sep = sys.argv[1]
data = json.load(sys.stdin)
allowed = 'yes' if data.get('allowed', True) else 'no'
# Detail lines for exceeded limits
detail_lines = []
for d in data.get('details', []):
    if d.get('exceeded'):
        w, pct, used, limit, threshold = d['window'], d['pct'], d['used'], d['limit'], d['threshold']
        detail_lines.append(f'  {w}: {used:,} / {limit:,} tokens ({pct}% >= {threshold*100:.0f}% threshold)')
detail = '\n'.join(detail_lines)
# Summary for system message
parts = [f\"{d['window']}:{d['pct']}%\" for d in data.get('details', []) if 'window' in d and 'pct' in d]
summary = ' | '.join(parts) if parts else 'no limits configured'
print(f'{allowed}{sep}{detail}{sep}{summary}')
" "$SEP" 2>/dev/null || echo "yes${SEP}${SEP}")

IFS="$SEP" read -r RATE_ALLOWED RATE_DETAIL RATE_SUMMARY <<< "$RATE_PARSED"

if [[ "$RATE_ALLOWED" == "no" ]]; then
  python "$SCRIPT_DIR/scripts/history.py" end "$TOPIC_SLUG" "$ITERATION" "rate-limited" "Rate limit threshold reached" 2>/dev/null || true
  echo "Auto-Explorer: Rate limit reached — stopping exploration."
  echo "   Topic: $TOPIC (completed $ITERATION iterations)"
  echo "   Exceeded limits:"
  echo "$RATE_DETAIL"
  echo ""
  echo "   Findings so far are in: $OUTPUT_DIR/"
  echo "   Edit ~/.claude/auto-explorer-limits.json to adjust limits."
  rm "$STATE_FILE"
  exit 0
fi

# Check for assistant messages in transcript
if ! grep -q '"role":"assistant"' "$TRANSCRIPT_PATH" 2>/dev/null; then
  echo "Auto-Explorer: No assistant messages found in transcript" >&2
  echo "   Stopping exploration." >&2
  rm "$STATE_FILE"
  exit 0
fi

# Extract last assistant message text AND explore-done/explore-next tags
TAGS=$(grep '"role":"assistant"' "$TRANSCRIPT_PATH" | tail -1 | python -c "
import json, re, sys
sep = sys.argv[1]
try:
    line = sys.stdin.read().strip()
    data = json.loads(line)
    content = data.get('message', {}).get('content', [])
    text = '\n'.join(item['text'] for item in content if item.get('type') == 'text')
    done = next_t = ''
    done_match = re.search(r'<explore-done>(.*?)</explore-done>', text, re.DOTALL)
    if done_match:
        done = re.sub(r'\s+', ' ', done_match.group(1).strip())
    next_match = re.search(r'<explore-next>(.*?)</explore-next>', text, re.DOTALL)
    if next_match:
        next_t = re.sub(r'\s+', ' ', next_match.group(1).strip())
    print(done + sep + next_t)
except Exception:
    print(sep)
" "$SEP" 2>/dev/null || echo "$SEP")

IFS="$SEP" read -r EXPLORE_DONE NEXT_SUBTOPIC <<< "$TAGS"

if [[ -n "$EXPLORE_DONE" ]]; then
  python "$SCRIPT_DIR/scripts/history.py" end "$TOPIC_SLUG" "$ITERATION" "completed" "$EXPLORE_DONE" 2>/dev/null || true
  echo "Auto-Explorer: Task completed!"
  echo "   Topic: $TOPIC (completed in $ITERATION iterations)"
  echo "   Reason: $EXPLORE_DONE"
  echo "   Output: $OUTPUT_DIR/"
  rm "$STATE_FILE"
  exit 0
fi

# Fallback if no <explore-next> tag found (mode-aware)
if [[ -z "$NEXT_SUBTOPIC" ]]; then
  if [[ "$MODE" == "build" ]]; then
    NEXT_SUBTOPIC="Continue working on the next sub-task for: $TOPIC"
  else
    NEXT_SUBTOPIC="Explore a deeper or less-covered aspect of: $TOPIC"
  fi
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

Work on the code in the working directory. Write a brief progress log to $OUTPUT_DIR/$FILE_NUM-<task-slug>.md.

$(if [[ $MAX_ITERATIONS -gt 0 ]] && [[ $NEXT_ITERATION -eq $MAX_ITERATIONS ]]; then
  echo "THIS IS THE FINAL ITERATION. Wrap up any remaining work and write $OUTPUT_DIR/summary.md with a comprehensive summary of what was built."
fi)

Remember: End your response with <explore-next>next specific sub-task</explore-next> or <explore-done>reason</explore-done> if genuinely complete."
else
  NEXT_PROMPT="Continue exploring '$TOPIC'. Iteration $ITER_DISPLAY.

Current sub-topic to research: $NEXT_SUBTOPIC

Write your findings to $OUTPUT_DIR/$FILE_NUM-<subtopic-slug>.md (choose an appropriate filename).

$(if [[ $MAX_ITERATIONS -gt 0 ]] && [[ $NEXT_ITERATION -eq $MAX_ITERATIONS ]]; then
  echo "THIS IS THE FINAL ITERATION. After writing your findings file, also write $OUTPUT_DIR/summary.md with a comprehensive summary of all exploration findings."
fi)

Remember: End your response with <explore-next>next specific sub-topic</explore-next>"
fi

# Update iteration in state file (atomic update via temp file)
TEMP_FILE="${STATE_FILE}.tmp.$$"
sed "s/^iteration: .*/iteration: $NEXT_ITERATION/" "$STATE_FILE" > "$TEMP_FILE"
mv "$TEMP_FILE" "$STATE_FILE"

# Build system message
SYSTEM_MSG="Auto-Explorer iteration $ITER_DISPLAY | Mode: ${MODE:-research} | Topic: $TOPIC | Sub-topic: $NEXT_SUBTOPIC | Usage: $RATE_SUMMARY"

# Output JSON to block the stop and feed the next prompt
python -c "
import json, sys
result = {
    'decision': 'block',
    'reason': sys.argv[1],
    'systemMessage': sys.argv[2]
}
print(json.dumps(result))
" "$NEXT_PROMPT" "$SYSTEM_MSG"

exit 0
