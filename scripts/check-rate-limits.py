#!/usr/bin/env python
"""
Auto-Explorer Rate Limit Checker

Reads token usage from stats-cache.json and current session transcript,
compares against configured limits in auto-explorer-limits.json.

Output: JSON with { "allowed": true/false, "details": [...] }
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
LIMITS_FILE = CLAUDE_DIR / "auto-explorer-limits.json"
STATS_FILE = CLAUDE_DIR / "stats-cache.json"
STATE_FILE = Path(".claude") / "auto-explorer.local.md"


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def get_daily_tokens(stats):
    """Extract daily token counts from stats-cache.json."""
    result = {}
    for entry in stats.get("dailyModelTokens", []):
        date_str = entry.get("date", "")
        total = sum(entry.get("tokensByModel", {}).values())
        result[date_str] = total
    return result


def get_session_tokens(transcript_path):
    """Count tokens used in the current session from transcript JSONL."""
    total = 0
    if not transcript_path or not os.path.isfile(transcript_path):
        return 0
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    usage = entry.get("usage", {})
                    # Count output tokens as the primary metric
                    total += usage.get("output_tokens", 0)
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return total


def get_session_start_time():
    """Get session start time from auto-explorer state file."""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        in_frontmatter = False
        for line in content.split("\n"):
            if line.strip() == "---":
                if in_frontmatter:
                    break
                in_frontmatter = True
                continue
            if in_frontmatter and line.startswith("started_at:"):
                ts = line.split(":", 1)[1].strip().strip('"')
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        pass
    return None


def check_limits(transcript_path=None, threshold_override=None):
    limits_config = load_json(LIMITS_FILE)
    if not limits_config:
        # No limits configured — allow
        return {"allowed": True, "details": [{"window": "config", "status": "no limits file found, allowing"}]}

    stats = load_json(STATS_FILE)
    if not stats:
        # No stats available — allow (can't check)
        return {"allowed": True, "details": [{"window": "stats", "status": "no stats file found, allowing"}]}

    # Use override from --budget flag if provided, else fall back to config file
    threshold = threshold_override if threshold_override is not None else limits_config.get("threshold", 0.6)
    rate_limits = limits_config.get("rate_limits", {})
    daily_tokens = get_daily_tokens(stats)

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    details = []
    allowed = True

    # Compute session tokens once (avoids re-reading transcript for each window)
    session_tokens = get_session_tokens(transcript_path) if transcript_path else 0

    # --- Daily check ---
    if "daily" in rate_limits:
        daily_limit = rate_limits["daily"].get("tokens", 0)
        if daily_limit > 0:
            today_usage = daily_tokens.get(today_str, 0)
            today_total = today_usage + session_tokens
            pct = today_total / daily_limit
            exceeded = pct >= threshold
            if exceeded:
                allowed = False
            details.append({
                "window": "daily",
                "used": today_total,
                "limit": daily_limit,
                "threshold": threshold,
                "pct": round(pct * 100, 1),
                "exceeded": exceeded
            })

    # --- Weekly check ---
    if "weekly" in rate_limits:
        weekly_limit = rate_limits["weekly"].get("tokens", 0)
        if weekly_limit > 0:
            week_total = sum(
                daily_tokens.get((now - timedelta(days=i)).strftime("%Y-%m-%d"), 0)
                for i in range(7)
            )
            week_total += session_tokens
            pct = week_total / weekly_limit
            exceeded = pct >= threshold
            if exceeded:
                allowed = False
            details.append({
                "window": "weekly",
                "used": week_total,
                "limit": weekly_limit,
                "threshold": threshold,
                "pct": round(pct * 100, 1),
                "exceeded": exceeded
            })

    # --- 4-hour check ---
    if "4h" in rate_limits:
        four_h_limit = rate_limits["4h"].get("tokens", 0)
        if four_h_limit > 0:
            start_time = get_session_start_time()
            hours_running = 0
            if start_time:
                hours_running = (now - start_time).total_seconds() / 3600

            pct = session_tokens / four_h_limit
            exceeded = pct >= threshold
            if exceeded:
                allowed = False
            details.append({
                "window": "4h",
                "used": session_tokens,
                "limit": four_h_limit,
                "threshold": threshold,
                "pct": round(pct * 100, 1),
                "hours_running": round(hours_running, 1),
                "exceeded": exceeded
            })

    return {"allowed": allowed, "details": details}


if __name__ == "__main__":
    # Args: [transcript_path] [threshold_override]
    transcript_path = sys.argv[1] if len(sys.argv) > 1 else None
    threshold_override = None
    if len(sys.argv) > 2:
        try:
            threshold_override = float(sys.argv[2])
        except ValueError:
            pass
    result = check_limits(transcript_path, threshold_override)
    print(json.dumps(result))
