#!/usr/bin/env python
"""
Auto-Explorer Improvement Engine

Analyzes session history to provide adaptive recommendations:
template selection, budget adaptation, repeat detection, keyword extraction.

CLI subcommands:
  suggest-template <mode>           Thompson Sampling template recommendation
  suggest-budget <mode>             Learn preferred budget from history
  template-stats                    Show per-template performance stats
  detect-repeat <keywords_json>     Check if topic overlaps with past session
  extract-keywords <output_dir> [n] Extract keywords from output files via TF-IDF
  mode-accuracy                     Show mode auto-detection accuracy
"""

import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HISTORY_FILE = Path("auto-explore-findings/.history.json")


def load_completed_sessions():
    """Load sessions with usable quality signals."""
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []
    return [
        s for s in history
        if s.get("status") in ("completed", "rate-limited", "max-iterations")
    ]


def template_stats(sessions):
    """Compute per-template performance stats.

    Returns dict: template_name -> {count, avg_iterations,
    natural_completion_rate, avg_output_density, bandit}
    """
    stats = defaultdict(lambda: {
        "count": 0, "total_iters": 0, "natural": 0,
        "total_density": 0.0, "bandit": {"alpha": 1, "beta": 1},
    })
    for s in sessions:
        t = s.get("template") or "_none"
        stats[t]["count"] += 1
        stats[t]["total_iters"] += s.get("iterations", 0)
        qs = s.get("quality_signals", {})
        if qs.get("completion_type") == "natural":
            stats[t]["natural"] += 1
            stats[t]["bandit"]["alpha"] += 1
        else:
            stats[t]["bandit"]["beta"] += 1
        stats[t]["total_density"] += qs.get("output_density", 0)

    result = {}
    for t, d in stats.items():
        n = d["count"]
        result[t] = {
            "count": n,
            "avg_iterations": round(d["total_iters"] / n, 1) if n else 0,
            "natural_completion_rate": round(d["natural"] / n, 2) if n else 0,
            "avg_output_density": round(d["total_density"] / n, 1) if n else 0,
            "bandit": d["bandit"],
        }
    return result


def suggest_template(sessions, available_templates, mode=None, seed=None):
    """Thompson Sampling over templates: pick template most likely to succeed.

    'Success' = natural completion. Each template has Beta(alpha, beta) prior.
    Returns (template_name, score) tuple.
    """
    rng = random.Random(seed)
    stats = template_stats(sessions)

    if not available_templates:
        return None, 0.0

    best_score = -1
    best_template = available_templates[0]

    for t in available_templates:
        s = stats.get(t, {"bandit": {"alpha": 1, "beta": 1}})
        alpha = s["bandit"]["alpha"]
        beta_param = s["bandit"]["beta"]
        x = rng.gammavariate(max(alpha, 0.1), 1)
        y = rng.gammavariate(max(beta_param, 0.1), 1)
        score = x / (x + y) if (x + y) > 0 else 0.5
        if score > best_score:
            best_score = score
            best_template = t
    return best_template, round(best_score, 3)


def suggest_budget(sessions, mode):
    """Learn preferred budget from past sessions by mode.

    Returns "aggressive", "conservative", or None (keep current).
    """
    mode_sessions = [s for s in sessions if s.get("mode") == mode]
    if len(mode_sessions) < 3:
        return None

    qs_list = [s.get("quality_signals", {}) for s in mode_sessions[-10:]]
    ratios = [q.get("iterations_vs_budget", 0) for q in qs_list if q and q.get("iterations_vs_budget")]

    if not ratios:
        return None

    avg_ratio = sum(ratios) / len(ratios)
    if avg_ratio > 0.95:
        return "aggressive"
    elif avg_ratio < 0.4:
        return "conservative"
    return None


def mode_correction_rate(sessions):
    """Track how often auto-detected mode gets corrected.

    Returns (total, corrected) tuple.
    """
    total = corrected = 0
    for s in sessions:
        if "mode_corrected" in s:
            total += 1
            if s["mode_corrected"]:
                corrected += 1
    return total, corrected


def frequent_keywords(sessions, top_n=20):
    """Extract most frequent keywords across recent sessions.

    Returns list of (keyword, count) tuples.
    """
    counter = Counter()
    for s in sessions[-50:]:
        for kw in s.get("keywords", []):
            counter[kw] += 1
    return counter.most_common(top_n)


def session_similarity(session_a, session_b):
    """Jaccard similarity between two sessions' keyword sets."""
    kw_a = set(session_a.get("keywords", []))
    kw_b = set(session_b.get("keywords", []))
    if not kw_a or not kw_b:
        return 0.0
    return len(kw_a & kw_b) / len(kw_a | kw_b)


def detect_repeat_topic(sessions, new_topic_keywords, threshold=0.5):
    """Check if a new topic overlaps significantly with a past session.

    Returns the matching session dict or None.
    """
    new_set = set(new_topic_keywords)
    if not new_set:
        return None
    for s in reversed(sessions):
        kw_set = set(s.get("keywords", []))
        if not kw_set:
            continue
        union = new_set | kw_set
        if not union:
            continue
        sim = len(new_set & kw_set) / len(union)
        if sim >= threshold:
            return s
    return None


def extract_keywords_tfidf(output_dir, top_n=10):
    """Extract keywords from session output files using simple TF-IDF.

    Zero external dependencies.
    """
    output_path = Path(output_dir)
    if not output_path.is_dir():
        return []

    docs = []
    for f in sorted(output_path.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8").lower()
            words = re.findall(r"[a-z][a-z0-9-]{2,}", text)
            docs.append(Counter(words))
        except Exception:
            continue

    if not docs:
        return []

    df = Counter()
    for doc in docs:
        for word in doc:
            df[word] += 1

    n_docs = len(docs)
    combined = Counter()
    for doc in docs:
        for word, count in doc.items():
            idf = math.log(n_docs / df[word]) + 1
            combined[word] += count * idf

    stops = {
        "the", "and", "for", "with", "from", "that", "this", "are", "was",
        "will", "can", "has", "have", "been", "not", "but", "also", "its",
        "each", "how", "use", "used", "using", "all", "into", "when", "which",
        "more", "than", "other", "about", "would", "could", "should", "there",
        "what", "where", "why", "these", "those", "does", "you", "your",
        "they", "their", "them", "then", "some", "such", "most", "any",
    }
    return [
        (w, round(s, 1))
        for w, s in combined.most_common(top_n * 2)
        if w not in stops
    ][:top_n]


# --- CLI ---

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: improvement_engine.py <suggest-template|suggest-budget|template-stats|detect-repeat|extract-keywords|mode-accuracy> [args...]",
            file=sys.stderr,
        )
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "suggest-template":
        mode = sys.argv[2] if len(sys.argv) > 2 else "research"
        sessions = load_completed_sessions()
        templates = ["deep-dive", "quickstart", "architecture-review", "security-audit", "comparison"]
        tpl, score = suggest_template(sessions, templates, mode=mode)
        if tpl:
            stats = template_stats(sessions)
            s = stats.get(tpl, {})
            rate = s.get("natural_completion_rate", 0)
            count = s.get("count", 0)
            if count > 0:
                print(f"{tpl} ({rate*100:.0f}% success, {count} sessions)")
            else:
                print(tpl)
        else:
            print("")

    elif cmd == "suggest-budget":
        mode = sys.argv[2] if len(sys.argv) > 2 else "research"
        sessions = load_completed_sessions()
        result = suggest_budget(sessions, mode)
        print(result or "")

    elif cmd == "template-stats":
        sessions = load_completed_sessions()
        stats = template_stats(sessions)
        if stats:
            for t, s in sorted(stats.items()):
                rate = s["natural_completion_rate"]
                print(f"  {t:24s} {s['count']:3d} sessions  {rate*100:5.1f}% natural  avg {s['avg_iterations']:.0f} iters  {s['avg_output_density']:.1f} KB/iter")
        else:
            print("No session data yet.")

    elif cmd == "detect-repeat":
        if len(sys.argv) < 3:
            print("Usage: improvement_engine.py detect-repeat <keywords_json>", file=sys.stderr)
            sys.exit(1)
        sessions = load_completed_sessions()
        keywords = json.loads(sys.argv[2])
        match = detect_repeat_topic(sessions, keywords)
        if match:
            slug = match.get("slug", "?")
            topic = match.get("topic", "?")
            print(f"Similar to: {topic} ({slug})")
        else:
            print("")

    elif cmd == "extract-keywords":
        output_dir = sys.argv[2] if len(sys.argv) > 2 else ""
        top_n = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        if not output_dir:
            print("Usage: improvement_engine.py extract-keywords <output_dir> [n]", file=sys.stderr)
            sys.exit(1)
        keywords = extract_keywords_tfidf(output_dir, top_n)
        for word, score in keywords:
            print(f"  {word} ({score})")

    elif cmd == "mode-accuracy":
        sessions = load_completed_sessions()
        total, corrected = mode_correction_rate(sessions)
        if total > 0:
            print(f"Mode detection: {total - corrected}/{total} correct ({(total - corrected)/total*100:.0f}%)")
        else:
            print("No mode correction data yet.")

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
