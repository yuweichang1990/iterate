#!/bin/bash

# Auto-Explorer Setup Script
# Creates state file and output directory for autonomous exploration sessions
# Budget controls rate limit threshold (account usage %), not iteration count.

set -euo pipefail

# Parse arguments
TOPIC_PARTS=()
MAX_ITERATIONS=0
BUDGET=""
THRESHOLD=""

while [[ $# -gt 0 ]]; do
  case $1 in
    -h|--help)
      cat << 'HELP_EOF'
Auto-Explorer - Autonomous topic exploration with interest tracking

USAGE:
  /auto-explore [TOPIC...] [OPTIONS]

ARGUMENTS:
  TOPIC...    Topic to explore (can be multiple words without quotes)
              If omitted, auto-selects from your interest suggestions.

OPTIONS:
  --budget <level>        Account usage threshold — when to stop:
                            conservative = stop at 40% usage
                            moderate     = stop at 60% usage (default)
                            aggressive   = stop at 80% usage
  --max-iterations <n>    Optional hard cap on iterations (default: unlimited)
  -h, --help              Show this help message

DESCRIPTION:
  Starts an autonomous exploration session. Claude will:
  1. Research the topic across multiple iterations
  2. Write findings to auto-explore-findings/<topic>/
  3. Dynamically choose the next sub-topic each round
  4. Update your interest profile automatically
  5. Stop when account usage reaches the budget threshold

  The primary stopping mechanism is your account's rate limit.
  --max-iterations is an optional safety net on top of that.

EXAMPLES:
  /auto-explore Rust async programming
  /auto-explore --budget conservative WebAssembly
  /auto-explore --budget aggressive distributed consensus algorithms
  /auto-explore --max-iterations 30 Go generics
  /auto-explore                              (auto-select from interests)

STOPPING:
  /cancel-explore           Cancel the current exploration
  Auto-stops when account usage threshold is reached.
  Auto-stops when --max-iterations is reached (if set).

MONITORING:
  grep '^iteration:' .claude/auto-explorer.local.md
  head -15 .claude/auto-explorer.local.md
HELP_EOF
      exit 0
      ;;
    --max-iterations)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --max-iterations requires a number argument" >&2
        exit 1
      fi
      if ! [[ "$2" =~ ^[0-9]+$ ]]; then
        echo "Error: --max-iterations must be a positive integer, got: $2" >&2
        exit 1
      fi
      MAX_ITERATIONS="$2"
      shift 2
      ;;
    --budget)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --budget requires a level (conservative, moderate, aggressive)" >&2
        exit 1
      fi
      BUDGET="$2"
      shift 2
      ;;
    *)
      TOPIC_PARTS+=("$1")
      shift
      ;;
  esac
done

# Resolve budget to threshold percentage
case "${BUDGET:-moderate}" in
  conservative) THRESHOLD="0.4"; THRESHOLD_PCT=40 ;;
  moderate)     THRESHOLD="0.6"; THRESHOLD_PCT=60 ;;
  aggressive)   THRESHOLD="0.8"; THRESHOLD_PCT=80 ;;
  *)
    echo "Error: Unknown budget level: $BUDGET" >&2
    echo "   Valid levels: conservative, moderate, aggressive" >&2
    exit 1
    ;;
esac

# Join topic parts
TOPIC="${TOPIC_PARTS[*]:-}"

# If no topic provided, try to auto-select from user-interests.md
if [[ -z "$TOPIC" ]]; then
  INTERESTS_FILE="$HOME/.claude/user-interests.md"
  if [[ -f "$INTERESTS_FILE" ]]; then
    # Extract first numbered suggestion from Suggested Next Directions
    TOPIC=$(python -c "
import re, sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    content = f.read()
in_section = False
for line in content.split('\n'):
    if 'Suggested Next Directions' in line:
        in_section = True
        continue
    if in_section and re.match(r'^\d+\.', line.strip()):
        suggestion = re.sub(r'^\d+\.\s*', '', line.strip())
        if suggestion and 'No suggestions yet' not in suggestion:
            print(suggestion)
            break
" "$INTERESTS_FILE" 2>/dev/null || echo "")
  fi

  if [[ -z "$TOPIC" ]]; then
    echo "Error: No topic provided and no suggestions found in user-interests.md" >&2
    echo "" >&2
    echo "   Provide a topic:" >&2
    echo "     /auto-explore Rust async programming" >&2
    echo "     /auto-explore --budget conservative WebAssembly" >&2
    echo "" >&2
    echo "   Or start a few conversations first to build up interest suggestions." >&2
    exit 1
  fi

  echo "Auto-selected topic from your interests: $TOPIC"
  echo ""
fi

# Check for ralph-loop conflict
if [[ -f ".claude/ralph-loop.local.md" ]]; then
  echo "Warning: Ralph Loop is currently active!" >&2
  echo "   Running both loops simultaneously is not supported." >&2
  echo "   Use /cancel-ralph first, then try again." >&2
  exit 1
fi

# Check for existing auto-explorer session
if [[ -f ".claude/auto-explorer.local.md" ]]; then
  echo "Warning: An auto-explorer session is already active!" >&2
  echo "   Use /cancel-explore to stop it first, then try again." >&2
  exit 1
fi

# Create slug and auto-detect mode in a single Python call
SLUG_AND_MODE=$(python -c "
import re, sys, unicodedata, hashlib
topic = sys.argv[1]
# --- Slug ---
normalized = unicodedata.normalize('NFKD', topic).encode('ascii', 'ignore').decode('ascii')
slug = re.sub(r'[^a-z0-9]+', '-', normalized.lower().strip()).strip('-')
if not slug:
    slug = 'topic-' + hashlib.md5(topic.encode('utf-8')).hexdigest()[:8]
if len(slug) > 50:
    slug = slug[:50].rstrip('-')
# --- Mode ---
mode = 'research'
lower_topic = topic.lower().strip()
build_patterns = [
    r'^(build|implement|create|develop|fix|refactor|add|make|write|set\s*up|deploy|migrate|convert|port|upgrade)',
    r'^(設計|建立|開發|實作|修復|重構|新增|部署|撰寫|建置)',
]
for pat in build_patterns:
    if re.search(pat, lower_topic):
        mode = 'build'
        break
print(slug + '\t' + mode)
" "$TOPIC")

IFS=$'\t' read -r TOPIC_SLUG MODE <<< "$SLUG_AND_MODE"

# Create output directory
OUTPUT_DIR="auto-explore-findings/$TOPIC_SLUG"
mkdir -p "$OUTPUT_DIR"

# Create state file
mkdir -p .claude
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ "$MODE" == "build" ]]; then
  STATE_BODY="Build: $TOPIC

Write working code in the working directory. Log progress to $OUTPUT_DIR/.
First iteration: write 00-plan.md with architecture plan and task breakdown.
Subsequent iterations: write NN-<task-slug>.md with brief progress logs.

Always end your response with:
<explore-next>specific next sub-task to implement</explore-next>"
else
  STATE_BODY="Explore the topic: $TOPIC

Write your findings to the $OUTPUT_DIR/ directory. Start with 00-overview.md for a broad overview of the topic.

Each iteration, explore a different sub-topic in depth and write a numbered file (01-<subtopic>.md, 02-<subtopic>.md, etc.).

On the final iteration, also write summary.md with a comprehensive summary of all findings.

Always end your response with:
<explore-next>specific sub-topic to explore next</explore-next>"
fi

cat > .claude/auto-explorer.local.md <<EOF
---
active: true
iteration: 1
max_iterations: $MAX_ITERATIONS
threshold: $THRESHOLD
mode: $MODE
topic: "$TOPIC"
topic_slug: "$TOPIC_SLUG"
output_dir: "$OUTPUT_DIR"
started_at: "$STARTED_AT"
---

$STATE_BODY
EOF

# Record session in history log
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python "$SCRIPT_DIR/history.py" add "$TOPIC" "$MODE" "$TOPIC_SLUG" "${BUDGET:-moderate}" "$THRESHOLD" "$STARTED_AT" "$OUTPUT_DIR" 2>/dev/null || true

# Format display strings
if [[ $MAX_ITERATIONS -gt 0 ]]; then
  ITER_DISPLAY="$MAX_ITERATIONS (hard cap)"
else
  ITER_DISPLAY="unlimited (rate limit controlled)"
fi

# Output setup message
cat <<EOF
Auto-Explorer activated!

Topic: $TOPIC
Mode: $MODE
Output: $OUTPUT_DIR/
Budget: ${BUDGET:-moderate} (stop at ${THRESHOLD_PCT}% account usage)
Max iterations: $ITER_DISPLAY
Iteration: 1

The stop hook checks your account usage each round.
Exploration stops when usage reaches ${THRESHOLD_PCT}% of any rate limit window.
Rate limits configured in: ~/.claude/auto-explorer-limits.json

To monitor: head -15 .claude/auto-explorer.local.md
To cancel:  /cancel-explore

Starting exploration of: $TOPIC
EOF
