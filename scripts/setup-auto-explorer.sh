#!/bin/bash

# Auto-Explorer Setup Script
# Creates state file and output directory for autonomous exploration sessions
# Budget controls rate limit threshold (account usage %), not iteration count.

set -euo pipefail

# Verify Python 3.6+ is available (required for f-strings, datetime.timezone)
if ! python -c "import sys; assert sys.version_info >= (3, 6), f'Python 3.6+ required, got {sys.version}'" 2>/dev/null; then
  echo "Error: Python 3.6+ is required but not found in PATH." >&2
  echo "   Install Python 3 or ensure it is in your PATH." >&2
  exit 1
fi

# Non-whitespace delimiter for Python→bash data passing (see developer_guide.md Problem 4)
SEP=$'\x1f'

# Parse arguments
TOPIC_PARTS=()
MAX_ITERATIONS=0
BUDGET=""
THRESHOLD=""
FORCE_MODE=""

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
  --mode <mode>           Force mode: research or build (default: auto-detect)
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
    --mode)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --mode requires a value (research or build)" >&2
        exit 1
      fi
      if [[ "$2" != "research" && "$2" != "build" ]]; then
        echo "Error: --mode must be 'research' or 'build', got: $2" >&2
        exit 1
      fi
      FORCE_MODE="$2"
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

# Auto-create rate limits config if missing (first-use experience)
LIMITS_FILE="$HOME/.claude/auto-explorer-limits.json"
if [[ ! -f "$LIMITS_FILE" ]]; then
  mkdir -p "$HOME/.claude"
  cat > "$LIMITS_FILE" <<'LIMITS_EOF'
{
  "threshold": 0.6,
  "rate_limits": {
    "4h":     { "tokens": 700000 },
    "daily":  { "tokens": 4100000 },
    "weekly": { "tokens": 29000000 }
  }
}
LIMITS_EOF
  echo "Created default rate limits config: $LIMITS_FILE"
  echo "   Edit this file to match your Claude plan's quota."
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
    r'^(build|implement|create|develop|fix|refactor|add|make|write|set\s*up|deploy|migrate|convert|port|upgrade|improve|optimize|update|configure|install|redesign|integrate|automate|extract|remove|delete|replace|move|rename|split|merge|clean\s*up|debug|patch|scaffold|generate|wire\s*up)',
    r'^(設計|建立|開發|實作|修復|重構|新增|部署|撰寫|建置|優化|更新|設定|安裝|改善|整合|自動化|提取|刪除|替換|移動|合併|清理|除錯|修補|產生|升級|進化)',
]
for pat in build_patterns:
    if re.search(pat, lower_topic):
        mode = 'build'
        break
sep = sys.argv[2]
print(slug + sep + mode)
" "$TOPIC" "$SEP")

IFS="$SEP" read -r TOPIC_SLUG MODE <<< "$SLUG_AND_MODE"

# Override mode if --mode flag was used
if [[ -n "$FORCE_MODE" ]]; then
  MODE="$FORCE_MODE"
fi

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

# Detect first-ever session for welcome message
HISTORY_FILE="auto-explore-findings/.history.json"
IS_FIRST_SESSION=false
if [[ ! -f "$HISTORY_FILE" ]]; then
  IS_FIRST_SESSION=true
fi

python "$SCRIPT_DIR/history.py" add "$TOPIC" "$MODE" "$TOPIC_SLUG" "${BUDGET:-moderate}" "$THRESHOLD" "$STARTED_AT" "$OUTPUT_DIR" 2>/dev/null || true

# Format display strings
if [[ $MAX_ITERATIONS -gt 0 ]]; then
  ITER_DISPLAY="$MAX_ITERATIONS (hard cap)"
else
  ITER_DISPLAY="unlimited (rate limit controlled)"
fi

# First-use welcome message
if [[ "$IS_FIRST_SESSION" == true ]]; then
  cat <<'WELCOME_EOF'
Welcome to Auto-Explorer! Here's what will happen:

  1. Claude will work autonomously, iteration after iteration
  2. Each round produces output in auto-explore-findings/
  3. The stop hook monitors your rate limits and stops when budget is reached
  4. Use /explore-status to check progress, /cancel-explore to stop early

Tip: Run with --budget aggressive to use more quota, or conservative to save it.

WELCOME_EOF
fi

# Output setup message
cat <<EOF
Auto-Explorer activated!

Topic: $TOPIC
Mode: $MODE
Output: $OUTPUT_DIR/
Budget: ${BUDGET:-moderate} (stop at ${THRESHOLD_PCT}% usage)
Max iterations: $ITER_DISPLAY

Check progress: /explore-status
Cancel:         /cancel-explore
EOF
