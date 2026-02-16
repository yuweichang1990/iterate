#!/usr/bin/env python
"""
Auto-Explorer Helpers

Shared utility functions used by stop-hook.sh and setup-auto-explorer.sh.
Extracted from inline Python blocks for testability and deduplication.

CLI subcommands:
  parse-frontmatter <file> <sep>          Parse state file frontmatter
  make-slug-and-mode <topic> <sep>        Generate slug and detect mode
  extract-tags <sep>                      Extract explore-* tags from stdin
  check-stale <state_file>                Check if session is stale (>24h)
  stale-info <state_file> <sep>           Get topic, slug, iteration from stale session
  suggest-topic <interests_file>          Auto-select topic from interests
  format-duration <started_at>            Format duration from timestamp to now
  format-rate-summary <sep>               Parse rate check JSON from stdin
  extract-json-field <field>              Extract a field from JSON on stdin
  json-output <reason> <system_message>   Output stop hook JSON response
"""

import hashlib
import json
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


# --- Stale session detection ---

def check_stale_session(state_file, max_hours=24):
    """Check if a session state file is stale (older than max_hours).

    Returns True if stale, False otherwise. Returns False on any error.
    """
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            content = f.read()
        fields = parse_frontmatter(content)
        started = fields.get('started_at', '')
        if not started:
            return False
        start = datetime.fromisoformat(started.replace('Z', '+00:00'))
        hours = (datetime.now(timezone.utc) - start).total_seconds() / 3600
        return hours > max_hours
    except Exception:
        return False


def get_stale_info(state_file, sep):
    """Get topic, slug, and iteration from a stale session state file.

    Returns sep-joined string: topic<sep>slug<sep>iteration
    """
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            content = f.read()
        fields = parse_frontmatter(content)
        topic = fields.get('topic', 'unknown')
        slug = fields.get('topic_slug', 'unknown')
        iteration = fields.get('iteration', '0')
        return sep.join([topic, slug, iteration])
    except Exception:
        return sep.join(['unknown', 'unknown', '0'])


# --- Topic suggestion ---

def suggest_topic(interests_file):
    """Extract first numbered suggestion from user-interests.md.

    Returns the suggestion text, or empty string if none found.
    """
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
                    return suggestion
    except Exception:
        pass
    return ''


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

    elif cmd == 'check-stale':
        print('yes' if check_stale_session(sys.argv[2]) else 'no')

    elif cmd == 'stale-info':
        print(get_stale_info(sys.argv[2], sys.argv[3]))

    elif cmd == 'suggest-topic':
        print(suggest_topic(sys.argv[2]))

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
