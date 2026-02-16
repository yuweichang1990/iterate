#!/usr/bin/env python
"""
Auto-Explorer Helpers

Shared utility functions used by stop-hook.sh and setup-auto-explorer.sh.
Extracted from inline Python blocks for testability and deduplication.

CLI subcommands:
  parse-frontmatter <file> <sep>          Parse state file frontmatter
  make-slug-and-mode <topic> <sep>        Generate slug and detect mode
  extract-tags <sep>                      Extract explore-* tags from stdin
  active-info <state_file> <sep>          Get topic, mode, iteration, duration from active session
  validate-limits <limits_file>           Validate rate limits JSON config
  check-stale <state_file>                Check if session is stale (>24h)
  stale-info <state_file> <sep>           Get topic, slug, iteration from stale session
  suggest-topic <interests_file>          Auto-select topic from interests
  session-stats <transcript> <output_dir> <sep>  Get token count, file count, output KB
  format-duration <started_at>            Format duration from timestamp to now
  format-rate-summary <sep>               Parse rate check JSON from stdin
  extract-json-field <field>              Extract a field from JSON on stdin
  load-template <name> <dir> [sep]       Load exploration template by name
  list-templates <dir>                   List available exploration templates
  budget-iterations [threshold]          Map threshold to budget iterations
  compute-quality-signals <iter> <threshold> <output_kb> [sep]  Compute quality signals
  extract-topic-words <topic> [min_len]  Extract topic words for repeat detection
  append-telemetry <jsonl> <slug> <iter> <mode> <tokens> <kb> <subtopic>  Append JSONL telemetry
  json-output <reason> <system_message>   Output stop hook JSON response
"""

import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone


# --- Frontmatter parsing ---

def parse_frontmatter(content):
    """Parse YAML-like frontmatter from a state file.

    Returns dict of key-value pairs from the --- delimited block.
    """
    fields = {}
    in_fm = False
    for line in content.split('\n'):
        if line.strip() == '---':
            if in_fm:
                break
            in_fm = True
            continue
        if in_fm and ':' in line:
            key, val = line.split(':', 1)
            fields[key.strip()] = val.strip().strip('"')
    return fields


# --- Slug generation ---

def make_slug(topic):
    """Generate a URL-safe slug from a topic string.

    Handles Unicode (including CJK) by normalizing to ASCII.
    Falls back to MD5 hash prefix if no ASCII chars remain.
    """
    normalized = unicodedata.normalize('NFKD', topic).encode('ascii', 'ignore').decode('ascii')
    slug = re.sub(r'[^a-z0-9]+', '-', normalized.lower().strip()).strip('-')
    if not slug:
        slug = 'topic-' + hashlib.md5(topic.encode('utf-8')).hexdigest()[:8]
    if len(slug) > 50:
        slug = slug[:50].rstrip('-')
    return slug


# --- Mode detection ---

BUILD_PATTERNS = [
    r'^(build|implement|create|develop|fix|refactor|add|make|write|set\s*up|deploy|migrate|convert|port|upgrade|improve|optimize|update|configure|install|redesign|integrate|automate|extract|remove|delete|replace|move|rename|split|merge|clean\s*up|debug|patch|scaffold|generate|wire\s*up)',
    r'^(設計|建立|開發|實作|修復|重構|新增|部署|撰寫|建置|優化|更新|設定|安裝|改善|整合|自動化|提取|刪除|替換|移動|合併|清理|除錯|修補|產生|升級|進化)',
]

# Polite prefixes stripped before build pattern matching.
# Ordered longest-first to prevent partial matches (e.g., "請協助我" before "請").
POLITE_PREFIXES_EN = [
    "i'd like to ", "i want to ", "i need to ",
    "could you ", "can you ", "help me ",
    "let's ", "please ",
]
POLITE_PREFIXES_CJK = [
    '請協助我', '請自我', '請幫我', '請協助', '請幫忙',
    '協助我', '幫我', '協助', '幫忙', '自我', '請',
]


def _strip_polite_prefix(topic):
    """Strip common polite prefixes so the action verb is at position 0.

    Handles both English ("please build", "can you fix") and
    CJK ("請進化", "請自我進化", "幫我建立") prefixes.
    """
    for prefix in POLITE_PREFIXES_EN:
        if topic.startswith(prefix):
            return topic[len(prefix):].lstrip()
    for prefix in POLITE_PREFIXES_CJK:
        if topic.startswith(prefix):
            return topic[len(prefix):].lstrip()
    return topic


def detect_mode(topic):
    """Detect build vs research mode from topic wording.

    Returns 'build' if topic starts with an action verb, 'research' otherwise.
    Strips polite prefixes first (e.g., "please build" → "build").
    """
    lower_topic = _strip_polite_prefix(topic.lower().strip())
    for pat in BUILD_PATTERNS:
        if re.search(pat, lower_topic):
            return 'build'
    return 'research'


# --- Tag extraction ---

def extract_tags(text):
    """Extract <explore-done> and <explore-next> tags from text.

    Returns (done, next_topic) tuple. Whitespace is normalized.
    """
    done = next_t = ''
    done_match = re.search(r'<explore-done>(.*?)</explore-done>', text, re.DOTALL)
    if done_match:
        done = re.sub(r'\s+', ' ', done_match.group(1).strip())
    next_match = re.search(r'<explore-next>(.*?)</explore-next>', text, re.DOTALL)
    if next_match:
        next_t = re.sub(r'\s+', ' ', next_match.group(1).strip())
    return done, next_t


# --- State file reading ---

def _read_state_fields(state_file):
    """Read and parse frontmatter from a state file.

    Returns parsed fields dict, or None on any error.
    Single read point to avoid redundant file I/O when multiple
    functions need data from the same state file.
    """
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return parse_frontmatter(content)
    except Exception:
        return None


# --- Stale session detection ---

def check_stale_session(state_file, max_hours=24):
    """Check if a session state file is stale (older than max_hours).

    Returns True if stale, False otherwise. Returns False on any error.
    """
    fields = _read_state_fields(state_file)
    if not fields:
        return False
    started = fields.get('started_at', '')
    if not started:
        return False
    try:
        start = datetime.fromisoformat(started.replace('Z', '+00:00'))
        hours = (datetime.now(timezone.utc) - start).total_seconds() / 3600
        return hours > max_hours
    except Exception:
        return False


def get_active_info(state_file, sep):
    """Get topic, mode, iteration, and duration from an active session state file.

    Returns sep-joined string: topic<sep>mode<sep>iteration<sep>duration
    """
    fields = _read_state_fields(state_file)
    if not fields:
        return sep.join(['unknown', '?', '0', '?'])
    topic = fields.get('topic', 'unknown')
    mode = fields.get('mode', '?')
    iteration = fields.get('iteration', '0')
    started = fields.get('started_at', '')
    duration = format_duration(started) if started else '?'
    return sep.join([topic, mode, iteration, duration])


def get_stale_info(state_file, sep):
    """Get topic, slug, and iteration from a stale session state file.

    Returns sep-joined string: topic<sep>slug<sep>iteration
    """
    fields = _read_state_fields(state_file)
    if not fields:
        return sep.join(['unknown', 'unknown', '0'])
    topic = fields.get('topic', 'unknown')
    slug = fields.get('topic_slug', 'unknown')
    iteration = fields.get('iteration', '0')
    return sep.join([topic, slug, iteration])


# --- Topic suggestion ---

def suggest_topic(interests_file):
    """Extract first numbered suggestion from user-interests.md.

    Returns the suggestion text, or empty string if none found.
    """
    topics = suggest_topics(interests_file, max_count=1)
    return topics[0] if topics else ''


def suggest_topics(interests_file, max_count=3):
    """Extract up to max_count numbered suggestions from user-interests.md.

    Returns list of suggestion strings (may be empty).
    """
    results = []
    try:
        with open(interests_file, 'r', encoding='utf-8') as f:
            content = f.read()
        in_section = False
        for line in content.split('\n'):
            if 'Suggested Next Directions' in line:
                in_section = True
                continue
            if in_section and re.match(r'^\d+\.', line.strip()):
                suggestion = re.sub(r'^\d+\.\s*', '', line.strip())
                if suggestion and 'No suggestions yet' not in suggestion:
                    results.append(suggestion)
                    if len(results) >= max_count:
                        break
    except Exception:
        pass
    return results


# --- Duration formatting ---

def format_duration(started_at):
    """Format duration from a started_at timestamp to now.

    Returns human-readable string like '2h 15m' or '30m'.
    """
    try:
        start = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
        delta = datetime.now(timezone.utc) - start
        mins = int(delta.total_seconds() // 60)
        if mins >= 60:
            return f'{mins // 60}h {mins % 60}m'
        return f'{mins}m'
    except Exception:
        return '?'


# --- Rate summary formatting ---

def format_rate_summary(rate_json, sep):
    """Parse rate check JSON and format for display.

    Returns sep-joined string: allowed<sep>detail_lines<sep>summary
    """
    try:
        data = json.loads(rate_json)
        allowed = 'yes' if data.get('allowed', True) else 'no'
        detail_lines = []
        for d in data.get('details', []):
            if d.get('exceeded'):
                w, pct = d['window'], d['pct']
                used, limit = d['used'], d['limit']
                threshold = d['threshold']
                detail_lines.append(
                    f'  {w}: {used:,} / {limit:,} tokens ({pct}% >= {threshold*100:.0f}% threshold)'
                )
        detail = '\n'.join(detail_lines)
        parts = [
            f"{d['window']}:{d['pct']}%"
            for d in data.get('details', [])
            if 'window' in d and 'pct' in d
        ]
        summary = ' | '.join(parts) if parts else 'no limits configured'
        return f'{allowed}{sep}{detail}{sep}{summary}'
    except Exception:
        return f'yes{sep}{sep}'


# --- Rate limits validation ---

def validate_limits_config(filepath):
    """Validate rate limits JSON config file.

    Returns 'ok' if valid, or an error description string.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return f'invalid JSON: {e}'
    except FileNotFoundError:
        return 'file not found'
    except Exception as e:
        return f'read error: {e}'

    if not isinstance(data, dict):
        return 'expected a JSON object at top level'

    rate_limits = data.get('rate_limits')
    if rate_limits is None:
        return 'missing "rate_limits" key'
    if not isinstance(rate_limits, dict):
        return '"rate_limits" must be an object'

    for window in ('4h', 'daily', 'weekly'):
        entry = rate_limits.get(window)
        if entry is None:
            continue  # Missing windows are allowed (will use defaults)
        if not isinstance(entry, dict):
            return f'rate_limits.{window} must be an object'
        tokens = entry.get('tokens')
        if tokens is not None and (not isinstance(tokens, (int, float)) or tokens <= 0):
            return f'rate_limits.{window}.tokens must be a positive number'

    return 'ok'


# --- Number abbreviation ---

def abbreviate_number(n):
    """Abbreviate large numbers for display: 281140 → '281k', 4100000 → '4.1M'."""
    if n >= 1_000_000:
        val = n / 1_000_000
        return f'{val:.1f}M' if val != int(val) else f'{int(val)}M'
    if n >= 1_000:
        val = n / 1_000
        return f'{val:.0f}k'
    return str(n)


# --- Template loading ---

def load_template(template_name, templates_dir):
    """Load an exploration template by name.

    Templates are .md files in templates_dir with frontmatter (name, description,
    mode) and a body containing the exploration instructions. The body supports
    placeholders: {{TOPIC}}, {{OUTPUT_DIR}}.

    Returns dict with keys: name, description, mode, body.
    Raises FileNotFoundError if template not found.
    """
    # Try exact name, then with .md suffix
    candidates = [
        os.path.join(templates_dir, template_name),
        os.path.join(templates_dir, template_name + '.md'),
    ]
    filepath = None
    for c in candidates:
        if os.path.isfile(c):
            filepath = c
            break
    if filepath is None:
        raise FileNotFoundError(f'Template not found: {template_name}')

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    fields = parse_frontmatter(content)

    # Extract body (everything after the closing ---)
    body = ''
    lines = content.split('\n')
    in_fm = False
    body_start = 0
    for i, line in enumerate(lines):
        if line.strip() == '---':
            if in_fm:
                body_start = i + 1
                break
            in_fm = True
    body = '\n'.join(lines[body_start:]).strip()

    return {
        'name': fields.get('name', template_name),
        'description': fields.get('description', ''),
        'mode': fields.get('mode', ''),
        'body': body,
    }


def list_templates(templates_dir):
    """List available templates in the templates directory.

    Returns list of dicts with keys: name, description, mode.
    """
    templates = []
    if not os.path.isdir(templates_dir):
        return templates
    for fname in sorted(os.listdir(templates_dir)):
        if not fname.endswith('.md') or fname == 'README.md':
            continue
        try:
            tpl = load_template(fname, templates_dir)
            templates.append({
                'name': tpl['name'],
                'description': tpl['description'],
                'mode': tpl['mode'],
            })
        except Exception:
            continue
    return templates


# --- Session stats ---

def get_session_stats(transcript_path, output_dir):
    """Get session stats: estimated output tokens, files written, total output KB.

    Reads the transcript JSONL to count output_tokens, and scans the output
    directory for file count and total size.

    Returns (tokens, files_written, total_kb) tuple.
    """

    tokens = 0
    if transcript_path and os.path.isfile(transcript_path):
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        usage = entry.get('usage', {})
                        tokens += usage.get('output_tokens', 0)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass

    files_written = 0
    total_bytes = 0
    if output_dir and os.path.isdir(output_dir):
        for name in os.listdir(output_dir):
            fpath = os.path.join(output_dir, name)
            if os.path.isfile(fpath):
                files_written += 1
                try:
                    total_bytes += os.path.getsize(fpath)
                except OSError:
                    pass

    total_kb = round(total_bytes / 1024, 1)
    return tokens, files_written, total_kb


# --- Telemetry ---

def append_telemetry(jsonl_path, slug, iteration, mode, tokens_est, output_kb, next_subtopic):
    """Append a per-iteration telemetry line to a JSONL file.

    Each line records: slug, iteration, timestamp, mode, tokens_est, output_kb, next_subtopic.
    """
    line = {
        'slug': slug,
        'iteration': int(iteration),
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'mode': mode,
        'tokens_est': int(tokens_est),
        'output_kb': float(output_kb),
        'next_subtopic': next_subtopic,
    }
    with open(jsonl_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(line, ensure_ascii=False) + '\n')


# --- Quality signals ---

def compute_quality_signals(iteration, threshold, output_kb):
    """Compute quality signals for session history.

    Returns (budget_iters, iter_ratio, output_density) tuple.
    """
    # Map threshold to expected iteration count
    if threshold >= 0.75:
        budget_iters = 5
    elif threshold <= 0.55:
        budget_iters = 20
    else:
        budget_iters = 10

    iter_int = max(int(iteration), 1)
    iter_ratio = round(iter_int / max(budget_iters, 1), 2)
    output_density = round(float(output_kb) / iter_int, 1)
    return budget_iters, iter_ratio, output_density


# --- Topic word extraction ---

def extract_topic_words(topic, min_length=3):
    """Extract lowercase words from a topic string for repeat detection.

    Returns JSON string of words with length >= min_length.
    """
    words = [w.strip().lower() for w in topic.split() if len(w.strip()) >= min_length]
    return json.dumps(words)


# --- CLI interface ---

def main():
    if len(sys.argv) < 2:
        print('Usage: helpers.py <command> [args...]', file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'parse-frontmatter':
        filepath = sys.argv[2]
        sep = sys.argv[3]
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        fields = parse_frontmatter(content)
        keys = ['iteration', 'max_iterations', 'threshold', 'topic',
                'topic_slug', 'output_dir', 'mode', 'started_at']
        print(sep.join(fields.get(k, '') for k in keys))

    elif cmd == 'make-slug-and-mode':
        topic = sys.argv[2]
        sep = sys.argv[3]
        print(make_slug(topic) + sep + detect_mode(topic))

    elif cmd == 'extract-tags':
        sep = sys.argv[2]
        try:
            line = sys.stdin.read().strip()
            data = json.loads(line)
            content = data.get('message', {}).get('content', [])
            text = '\n'.join(
                item['text'] for item in content if item.get('type') == 'text'
            )
            done, next_t = extract_tags(text)
            print(done + sep + next_t)
        except Exception:
            print(sep)

    elif cmd == 'active-info':
        print(get_active_info(sys.argv[2], sys.argv[3]))

    elif cmd == 'validate-limits':
        print(validate_limits_config(sys.argv[2]))

    elif cmd == 'check-stale':
        print('yes' if check_stale_session(sys.argv[2]) else 'no')

    elif cmd == 'stale-info':
        print(get_stale_info(sys.argv[2], sys.argv[3]))

    elif cmd == 'suggest-topic':
        print(suggest_topic(sys.argv[2]))

    elif cmd == 'suggest-topics':
        max_count = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        sep = sys.argv[4] if len(sys.argv) > 4 else '\n'
        topics = suggest_topics(sys.argv[2], max_count=max_count)
        print(sep.join(topics))

    elif cmd == 'format-duration':
        print(format_duration(sys.argv[2]))

    elif cmd == 'format-rate-summary':
        print(format_rate_summary(sys.stdin.read().strip(), sys.argv[2]))

    elif cmd == 'extract-json-field':
        try:
            data = json.loads(sys.stdin.read())
            print(data.get(sys.argv[2], ''))
        except Exception:
            print('')

    elif cmd == 'session-stats':
        transcript_path = sys.argv[2] if len(sys.argv) > 2 else ''
        output_dir = sys.argv[3] if len(sys.argv) > 3 else ''
        sep = sys.argv[4] if len(sys.argv) > 4 else '\n'
        tokens, files, kb = get_session_stats(transcript_path, output_dir)
        print(f'{tokens}{sep}{files}{sep}{kb}')

    elif cmd == 'load-template':
        template_name = sys.argv[2]
        templates_dir = sys.argv[3]
        sep = sys.argv[4] if len(sys.argv) > 4 else '\n'
        try:
            tpl = load_template(template_name, templates_dir)
            # Output: name<sep>mode<sep>body
            print(f"{tpl['name']}{sep}{tpl['mode']}{sep}{tpl['body']}")
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)

    elif cmd == 'list-templates':
        templates_dir = sys.argv[2]
        sep = sys.argv[3] if len(sys.argv) > 3 else '\n'
        templates = list_templates(templates_dir)
        for tpl in templates:
            print(f"  {tpl['name']:20s} {tpl['description']}")

    elif cmd == 'budget-iterations':
        threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.6
        if threshold >= 0.75:
            print(5)    # conservative
        elif threshold <= 0.55:
            print(20)   # aggressive
        else:
            print(10)   # moderate

    elif cmd == 'compute-quality-signals':
        iteration = sys.argv[2] if len(sys.argv) > 2 else '1'
        threshold = sys.argv[3] if len(sys.argv) > 3 else '0.6'
        output_kb = sys.argv[4] if len(sys.argv) > 4 else '0'
        sep = sys.argv[5] if len(sys.argv) > 5 else '\n'
        budget_iters, iter_ratio, output_density = compute_quality_signals(
            iteration, float(threshold), output_kb
        )
        print(f'{budget_iters}{sep}{iter_ratio}{sep}{output_density}')

    elif cmd == 'extract-topic-words':
        topic = sys.argv[2] if len(sys.argv) > 2 else ''
        min_len = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        print(extract_topic_words(topic, min_len))

    elif cmd == 'append-telemetry':
        # args: jsonl_path slug iteration mode tokens_est output_kb next_subtopic
        if len(sys.argv) < 9:
            print('Usage: append-telemetry <jsonl_path> <slug> <iteration> <mode> <tokens_est> <output_kb> <next_subtopic>', file=sys.stderr)
            sys.exit(1)
        append_telemetry(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7], sys.argv[8])

    elif cmd == 'json-output':
        print(json.dumps({
            'decision': 'block',
            'reason': sys.argv[2],
            'systemMessage': sys.argv[3],
        }))

    else:
        print(f'Unknown command: {cmd}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
