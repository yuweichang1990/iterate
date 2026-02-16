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

# Resolve script directory early (used for helpers.py calls throughout)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse arguments
TOPIC_PARTS=()
MAX_ITERATIONS=0
BUDGET=""
THRESHOLD=""
FORCE_MODE=""
TEMPLATE_NAME=""
RESUME_MODE=false
RESUME_SLUG=""

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
  --compare               Shorthand for --template comparison (structured
                            side-by-side comparison with evaluation and verdict)
  --template <name>       Use an exploration template (deep-dive, quickstart,
                            architecture-review, security-audit, comparison)
  --max-iterations <n>    Optional hard cap on iterations (default: unlimited)
  --resume [slug]         Resume a previous session that was rate-limited,
                            max-iterations, cancelled, or errored.
                            If slug is omitted, resumes the most recent one.
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
  /auto-explore --compare React vs Vue vs Svelte
  /auto-explore --template deep-dive Kubernetes
  /auto-explore --template quickstart FastAPI
  /auto-explore                              (auto-select from interests)
  /auto-explore --resume                     (resume most recent session)
  /auto-explore --resume rust-async          (resume specific session)

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
    --compare)
      TEMPLATE_NAME="comparison"
      shift
      ;;
    --template)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --template requires a template name" >&2
        echo "   Available templates: deep-dive, quickstart, architecture-review, security-audit, comparison" >&2
        exit 1
      fi
      TEMPLATE_NAME="$2"
      shift 2
      ;;
    --resume)
      RESUME_MODE=true
      # Optional slug argument (next arg that doesn't start with --)
      if [[ -n "${2:-}" ]] && [[ ! "$2" =~ ^-- ]]; then
        RESUME_SLUG="$2"
        shift 2
      else
        shift
      fi
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

# --- Resume flow ---
if [[ "$RESUME_MODE" == true ]]; then
  # Cannot combine --resume with a topic
  if [[ -n "$TOPIC" ]]; then
    echo "Error: Cannot use --resume with a topic. The topic comes from the previous session." >&2
    exit 1
  fi
  # Cannot combine --resume with --template
  if [[ -n "$TEMPLATE_NAME" ]]; then
    echo "Error: Cannot use --resume with --template. Templates only apply to new sessions." >&2
    exit 1
  fi

  # Check for active session first
  if [[ -f ".claude/auto-explorer.local.md" ]]; then
    echo "Error: An auto-explorer session is already active." >&2
    echo "   Use /cancel-explore first, then retry --resume." >&2
    exit 1
  fi

  # Check for ralph-loop conflict
  if [[ -f ".claude/ralph-loop.local.md" ]]; then
    echo "Error: Ralph Loop is currently active. Use /cancel-ralph first." >&2
    exit 1
  fi

  # Find resumable session via history.py
  if [[ -n "$RESUME_SLUG" ]]; then
    RESUME_INFO=$(python "$SCRIPT_DIR/history.py" resume "$RESUME_SLUG" "$SEP" 2>/dev/null || echo "")
  else
    RESUME_INFO=$(python "$SCRIPT_DIR/history.py" resume "$SEP" 2>/dev/null || echo "")
  fi

  if [[ -z "$RESUME_INFO" ]]; then
    echo "Error: No resumable session found." >&2
    if [[ -n "$RESUME_SLUG" ]]; then
      echo "   No session with slug '$RESUME_SLUG' is available for resume." >&2
    fi
    echo "   Resumable statuses: rate-limited, max-iterations, cancelled, error." >&2
    echo "   Use /explore-status to see recent sessions." >&2
    exit 1
  fi

  IFS="$SEP" read -r R_TOPIC R_MODE R_SLUG R_OUTPUT_DIR R_THRESHOLD R_ITERATIONS R_BUDGET <<< "$RESUME_INFO"

  # Use session values (--budget flag can override threshold)
  TOPIC="$R_TOPIC"
  MODE="$R_MODE"
  TOPIC_SLUG="$R_SLUG"
  OUTPUT_DIR="$R_OUTPUT_DIR"
  PREV_ITERATIONS="${R_ITERATIONS:-1}"

  # Use --budget override if provided, else use original session's values
  if [[ -z "$BUDGET" ]]; then
    BUDGET="$R_BUDGET"
    THRESHOLD="$R_THRESHOLD"
    case "$BUDGET" in
      conservative) THRESHOLD_PCT=40 ;;
      aggressive)   THRESHOLD_PCT=80 ;;
      *)            THRESHOLD_PCT=60 ;;
    esac
  fi

  # Override mode if --mode flag was used
  if [[ -n "$FORCE_MODE" ]]; then
    MODE="$FORCE_MODE"
  fi

  # Ensure output dir exists
  mkdir -p "$OUTPUT_DIR"

  # Read _index.md for context injection
  INDEX_CONTENT=""
  INDEX_FILE="$OUTPUT_DIR/_index.md"
  if [[ -f "$INDEX_FILE" ]]; then
    INDEX_CONTENT=$(cat "$INDEX_FILE" 2>/dev/null || echo "")
  fi

  # Create state file with resume context
  mkdir -p .claude
  STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  if [[ "$MODE" == "build" ]]; then
    STATE_BODY="RESUMED SESSION: $TOPIC

Previous session ran $PREV_ITERATIONS iterations. Here is the progress so far:

$INDEX_CONTENT

Continue building from where the previous session left off. Work on the next most important sub-task.
Write progress to $OUTPUT_DIR/ and update $OUTPUT_DIR/_index.md.

Always end your response with:
<explore-next>specific next sub-task to implement</explore-next>"
  else
    STATE_BODY="RESUMED SESSION: $TOPIC

Previous session ran $PREV_ITERATIONS iterations. Here is the progress so far:

$INDEX_CONTENT

Continue exploring from where the previous session left off. Choose a sub-topic that wasn't covered or needs deeper investigation.
Write your findings to $OUTPUT_DIR/ and update $OUTPUT_DIR/_index.md.

Always end your response with:
<explore-next>specific sub-topic to explore next</explore-next>"
  fi

  cat > .claude/auto-explorer.local.md <<EOF
---
active: true
iteration: $PREV_ITERATIONS
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

  # Record new running entry in history
  python "$SCRIPT_DIR/history.py" add "$TOPIC" "$MODE" "$TOPIC_SLUG" "${BUDGET:-moderate}" "$THRESHOLD" "$STARTED_AT" "$OUTPUT_DIR" 2>/dev/null || true

  # Format display
  if [[ $MAX_ITERATIONS -gt 0 ]]; then
    ITER_DISPLAY="$MAX_ITERATIONS (hard cap)"
  else
    ITER_DISPLAY="unlimited (rate limit controlled)"
  fi

  cat <<EOF
Auto-Explorer RESUMED!

Topic: $TOPIC
Mode: $MODE
Output: $OUTPUT_DIR/
Budget: ${BUDGET:-moderate} (stop at ${THRESHOLD_PCT}% usage)
Max iterations: $ITER_DISPLAY
Previous iterations: $PREV_ITERATIONS

Continuing from where the previous session left off.
Check progress: /explore-status
Cancel:         /cancel-explore
EOF

  exit 0
fi

# If no topic provided, try to auto-select from user-interests.md
if [[ -z "$TOPIC" ]]; then
  INTERESTS_FILE="$HOME/.claude/user-interests.md"
  if [[ -f "$INTERESTS_FILE" ]]; then
    # Extract top suggestions to show the user, pick the first
    ALL_SUGGESTIONS=$(python "$SCRIPT_DIR/helpers.py" suggest-topics "$INTERESTS_FILE" 3 "$SEP" 2>/dev/null || echo "")
    if [[ -n "$ALL_SUGGESTIONS" ]]; then
      # First suggestion becomes the topic
      TOPIC=$(echo "$ALL_SUGGESTIONS" | head -c "$(echo "$ALL_SUGGESTIONS" | sed "s/$SEP.*//" | wc -c)" | tr -d '\n')
      IFS="$SEP" read -ra SUGGESTIONS <<< "$ALL_SUGGESTIONS"
      TOPIC="${SUGGESTIONS[0]}"

      # Show all suggestions so the user knows what was available
      if [[ ${#SUGGESTIONS[@]} -gt 1 ]]; then
        echo "Your suggested topics (from interest profile):"
        for i in "${!SUGGESTIONS[@]}"; do
          echo "  $((i + 1)). ${SUGGESTIONS[$i]}"
        done
        echo ""
      fi
    fi
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

# Validate rate limits config (catch malformed JSON before session starts)
LIMITS_VALID=$(python "$SCRIPT_DIR/helpers.py" validate-limits "$LIMITS_FILE" 2>/dev/null || echo "error")
if [[ "$LIMITS_VALID" != "ok" ]]; then
  echo "Warning: Rate limits config may be malformed: $LIMITS_FILE" >&2
  echo "   Issue: $LIMITS_VALID" >&2
  echo "   Rate limiting may not work correctly. See /explore-help for the expected format." >&2
  echo ""
fi

# Check for ralph-loop conflict
if [[ -f ".claude/ralph-loop.local.md" ]]; then
  echo "Warning: Ralph Loop is currently active!" >&2
  echo "   Running both loops simultaneously is not supported." >&2
  echo "   Use /cancel-ralph first, then try again." >&2
  exit 1
fi

# Check for existing auto-explorer session (with stale detection)
if [[ -f ".claude/auto-explorer.local.md" ]]; then
  # Check if the session is stale (>24h old) — auto-cleanup instead of blocking
  IS_STALE=$(python "$SCRIPT_DIR/helpers.py" check-stale ".claude/auto-explorer.local.md" 2>/dev/null || echo "no")

  if [[ "$IS_STALE" == "yes" ]]; then
    # Auto-cleanup stale session — get topic, slug, iteration in one call
    STALE_INFO=$(python "$SCRIPT_DIR/helpers.py" stale-info ".claude/auto-explorer.local.md" "$SEP" 2>/dev/null || echo "unknown${SEP}unknown${SEP}0")
    IFS="$SEP" read -r STALE_TOPIC STALE_SLUG STALE_ITER <<< "$STALE_INFO"
    echo "Auto-cleanup: Previous session on '$STALE_TOPIC' is >24h old."
    echo "   Cleaning up stale state file and proceeding with new session."
    echo ""
    # Record stale session in history before removing
    python "$SCRIPT_DIR/history.py" end "$STALE_SLUG" "$STALE_ITER" "error" "Stale session auto-cleaned (>24h)" 2>/dev/null || true
    rm -f ".claude/auto-explorer.local.md"
  else
    # Show active session details so the user knows what's running
    ACTIVE_INFO=$(python "$SCRIPT_DIR/helpers.py" active-info ".claude/auto-explorer.local.md" "$SEP" 2>/dev/null || echo "unknown${SEP}?${SEP}0${SEP}?")
    IFS="$SEP" read -r ACTIVE_TOPIC ACTIVE_MODE ACTIVE_ITER ACTIVE_DURATION <<< "$ACTIVE_INFO"
    echo "Warning: An auto-explorer session is already active!" >&2
    echo "   Topic:     $ACTIVE_TOPIC" >&2
    echo "   Mode:      $ACTIVE_MODE" >&2
    echo "   Iteration: $ACTIVE_ITER" >&2
    echo "   Running:   $ACTIVE_DURATION" >&2
    echo "" >&2
    echo "   Use /cancel-explore to stop it, or /explore-status for details." >&2
    exit 1
  fi
fi

# Create slug and auto-detect mode via helpers.py
SLUG_AND_MODE=$(python "$SCRIPT_DIR/helpers.py" make-slug-and-mode "$TOPIC" "$SEP")

IFS="$SEP" read -r TOPIC_SLUG MODE <<< "$SLUG_AND_MODE"

# Override mode if --mode flag was used
if [[ -n "$FORCE_MODE" ]]; then
  MODE="$FORCE_MODE"
fi

# --- Improvement engine suggestions (v1.9.0) ---
# Show template recommendation if user didn't specify --template
if [[ -z "$TEMPLATE_NAME" ]]; then
  TPL_SUGGESTION=$(python "$SCRIPT_DIR/improvement_engine.py" suggest-template "$MODE" 2>/dev/null || echo "")
  if [[ -n "$TPL_SUGGESTION" ]]; then
    echo "Suggested template: $TPL_SUGGESTION"
    echo "   (use --template <name> to apply)"
    echo ""
  fi
fi

# Show budget recommendation if data supports it
BUDGET_SUGGESTION=$(python "$SCRIPT_DIR/improvement_engine.py" suggest-budget "$MODE" 2>/dev/null || echo "")
if [[ -n "$BUDGET_SUGGESTION" ]]; then
  echo "Budget hint: history suggests '$BUDGET_SUGGESTION' for $MODE sessions"
  echo "   (use --budget $BUDGET_SUGGESTION to apply)"
  echo ""
fi

# Detect repeat topic — warn if this topic overlaps with a recent session
TOPIC_WORDS=$(python "$SCRIPT_DIR/helpers.py" extract-topic-words "$TOPIC" 2>/dev/null || echo "[]")
REPEAT_MATCH=$(python "$SCRIPT_DIR/improvement_engine.py" detect-repeat "$TOPIC_WORDS" 2>/dev/null || echo "")
if [[ -n "$REPEAT_MATCH" ]]; then
  echo "Note: $REPEAT_MATCH"
  echo "   Consider --resume to continue the previous session instead."
  echo ""
fi

# --- Template loading ---
TEMPLATE_BODY=""
if [[ -n "$TEMPLATE_NAME" ]]; then
  TEMPLATES_DIR="$SCRIPT_DIR/../templates"
  TPL_RESULT=$(python "$SCRIPT_DIR/helpers.py" load-template "$TEMPLATE_NAME" "$TEMPLATES_DIR" "$SEP" 2>/dev/null)
  if [[ -z "$TPL_RESULT" ]]; then
    echo "Error: Template '$TEMPLATE_NAME' not found." >&2
    echo "   Available templates:" >&2
    python "$SCRIPT_DIR/helpers.py" list-templates "$TEMPLATES_DIR" 2>/dev/null || true
    exit 1
  fi
  IFS="$SEP" read -r TPL_NAME TPL_MODE TEMPLATE_BODY <<< "$TPL_RESULT"
  # Template mode overrides auto-detection (but --mode flag overrides template)
  if [[ -z "$FORCE_MODE" ]] && [[ -n "$TPL_MODE" ]]; then
    MODE="$TPL_MODE"
  fi
  # Replace placeholders in template body
  TEMPLATE_BODY="${TEMPLATE_BODY//\{\{TOPIC\}\}/$TOPIC}"
fi

# Create output directory
OUTPUT_DIR="auto-explore-findings/$TOPIC_SLUG"
mkdir -p "$OUTPUT_DIR"

# Replace OUTPUT_DIR placeholder in template body (must happen after OUTPUT_DIR is set)
if [[ -n "$TEMPLATE_BODY" ]]; then
  TEMPLATE_BODY="${TEMPLATE_BODY//\{\{OUTPUT_DIR\}\}/$OUTPUT_DIR}"
fi

# Write .topic file for readability (especially useful for CJK hash-based slugs)
echo "$TOPIC" > "$OUTPUT_DIR/.topic"

# Create state file
mkdir -p .claude
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ -n "$TEMPLATE_BODY" ]]; then
  STATE_BODY="$TEMPLATE_BODY"
elif [[ "$MODE" == "build" ]]; then
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
Mode: $MODE$(if [[ -n "$TEMPLATE_NAME" ]]; then echo " (template: $TEMPLATE_NAME)"; fi)
Output: $OUTPUT_DIR/
Budget: ${BUDGET:-moderate} (stop at ${THRESHOLD_PCT}% usage)
Max iterations: $ITER_DISPLAY

Check progress: /explore-status
Cancel:         /cancel-explore
EOF
