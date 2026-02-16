#!/usr/bin/env python
"""
Auto-Explorer History Manager

Manages session history in auto-explore-findings/.history.json

Subcommands:
  add <topic> <mode> <slug> <budget> <threshold> <started_at> <output_dir>
  end <slug> <iterations> <status> [reason]
  show
"""

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HISTORY_FILE = Path("auto-explore-findings/.history.json")


def load_history():
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_history(history):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def fix_stale_sessions(history):
    """Mark any 'running' sessions as 'error' if no state file exists.

    This handles cases where a session crashed without proper cleanup.
    Called from both cmd_add (at startup) and cmd_show (on dashboard).
    """
    state_file = Path(".claude/auto-explorer.local.md")
    if state_file.exists():
        return False  # There's an active session, don't touch running entries
    dirty = False
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for entry in history:
        if entry.get("status") == "running":
            entry["status"] = "error"
            entry["reason"] = "Session ended unexpectedly"
            entry["ended_at"] = now_str
            dirty = True
    return dirty


def cmd_add(args):
    """Add a new session record."""
    if len(args) < 7:
        print("Usage: history.py add <topic> <mode> <slug> <budget> <threshold> <started_at> <output_dir>", file=sys.stderr)
        sys.exit(1)
    history = load_history()
    # Fix any stale sessions from previous crashes before adding new one
    if fix_stale_sessions(history):
        save_history(history)
        history = load_history()  # Re-read after fix
    history.append({
        "topic": args[0],
        "mode": args[1],
        "slug": args[2],
        "budget": args[3],
        "threshold": float(args[4]),
        "started_at": args[5],
        "output_dir": args[6],
        "iterations": 1,
        "status": "running",
        "ended_at": None,
        "reason": None,
    })
    save_history(history)


def cmd_end(args):
    """Mark the most recent matching session as ended."""
    if len(args) < 3:
        print("Usage: history.py end <slug> <iterations> <status> [reason]", file=sys.stderr)
        sys.exit(1)
    slug = args[0]
    iterations = int(args[1])
    status = args[2]
    reason = args[3] if len(args) > 3 else ""

    history = load_history()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Find the most recent entry with matching slug that is still running
    for entry in reversed(history):
        if entry.get("slug") == slug and entry.get("status") == "running":
            entry["iterations"] = iterations
            entry["status"] = status
            entry["reason"] = reason
            entry["ended_at"] = now_str
            break

    save_history(history)


def format_duration(started_str, ended_str=None):
    """Format duration between two ISO timestamps."""
    try:
        start = datetime.fromisoformat(started_str.replace("Z", "+00:00"))
        end = datetime.fromisoformat(ended_str.replace("Z", "+00:00")) if ended_str else datetime.now(timezone.utc)
        delta = end - start
        total_mins = int(delta.total_seconds() // 60)
        hours = total_mins // 60
        mins = total_mins % 60
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"
    except Exception:
        return "?"


def status_icon(status):
    """Return a status indicator."""
    return {
        "running": ">>",
        "completed": "OK",
        "rate-limited": "$$",
        "cancelled": "--",
        "max-iterations": "##",
        "error": "!!",
    }.get(status, "??")


def cmd_show():
    """Display the dashboard."""
    history = load_history()
    state_file = Path(".claude/auto-explorer.local.md")

    # Check for active session
    active = None
    if state_file.exists():
        try:
            content = state_file.read_text(encoding="utf-8")
            in_fm = False
            fields = {}
            for line in content.split("\n"):
                if line.strip() == "---":
                    if in_fm:
                        break
                    in_fm = True
                    continue
                if in_fm and ":" in line:
                    k, v = line.split(":", 1)
                    fields[k.strip()] = v.strip().strip('"')
            active = fields
        except Exception:
            pass

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    print("=" * 62)
    print("  Auto-Explorer Dashboard")
    print("=" * 62)

    # Active session
    print()
    if active:
        topic = active.get("topic", "?")
        mode = active.get("mode", "?")
        iteration = active.get("iteration", "?")
        started = active.get("started_at", "")
        threshold = active.get("threshold", "0.6")
        duration = format_duration(started) if started else "?"

        print(f"  >> ACTIVE SESSION")
        print(f"     Topic:     {topic}")
        print(f"     Mode:      {mode}")
        print(f"     Iteration: {iteration}")
        print(f"     Running:   {duration}")
        print(f"     Threshold: {float(threshold)*100:.0f}%")
        print(f"     Started:   {started}")

        # Show rate limit usage if check-rate-limits.py is available
        try:
            script_dir = Path(__file__).parent
            spec = importlib.util.spec_from_file_location(
                "check_rate_limits", str(script_dir / "check-rate-limits.py")
            )
            crl = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(crl)
            result = crl.check_limits(threshold_override=float(threshold))
            details = result.get("details", [])
            usage_parts = []
            for d in details:
                if "window" in d and "pct" in d:
                    pct = d["pct"]
                    window = d["window"]
                    limit = d.get("limit", 0)
                    used = d.get("used", 0)
                    bar_len = 20
                    filled = min(int(pct / 100 * bar_len), bar_len)
                    bar = "#" * filled + "-" * (bar_len - filled)
                    exceeded = d.get("exceeded", False)
                    marker = " EXCEEDED" if exceeded else ""
                    usage_parts.append(f"     {window:>6}: [{bar}] {pct:5.1f}%  ({used:,} / {limit:,}){marker}")
            if usage_parts:
                print(f"     --- Rate Limits ---")
                for line in usage_parts:
                    print(line)
        except Exception:
            pass  # Don't crash dashboard if rate limit check fails

    else:
        print("  No active session.")
        print("  Start one: /auto-explore <topic>")

    # Auto-fix stale "running" entries (session ended without proper history update)
    if fix_stale_sessions(history):
        save_history(history)

    # Session history
    if not history:
        print()
        print("  No session history yet.")
        print("=" * 62)
        return

    # Split into today vs older
    today_sessions = []
    older_sessions = []
    for entry in reversed(history):
        started = entry.get("started_at", "")
        if started[:10] == today_str:
            today_sessions.append(entry)
        else:
            older_sessions.append(entry)

    def format_entry(entry, show_date=False):
        topic = entry.get("topic", "?")
        mode = entry.get("mode", "?")
        iters = entry.get("iterations", "?")
        status = entry.get("status", "?")
        reason = entry.get("reason", "")
        started = entry.get("started_at", "")
        ended = entry.get("ended_at", "")
        output_dir = entry.get("output_dir", "")
        icon = status_icon(status)
        duration = format_duration(started, ended) if started else "?"

        time_part = started[11:16] if len(started) >= 16 else "?"
        if show_date:
            time_part = started[:16].replace("T", " ") if len(started) >= 16 else "?"

        lines = [f"  [{icon}] {time_part}  {duration:>6}  {mode:<8}  {iters:>3} iters  {topic}"]
        if reason and status != "running":
            lines.append(f"       >> {reason}")
        if output_dir and status != "running":
            lines.append(f"       >> {output_dir}/")
        return "\n".join(lines)

    if today_sessions:
        print()
        print(f"  --- Today ({today_str}) ---")
        for entry in today_sessions:
            print(format_entry(entry))

    if older_sessions:
        print()
        print(f"  --- Earlier ---")
        for entry in older_sessions[:10]:
            print(format_entry(entry, show_date=True))
        if len(older_sessions) > 10:
            print(f"  ... and {len(older_sessions) - 10} more")

    # Summary stats
    total = len(history)
    running = sum(1 for e in history if e.get("status") == "running")
    completed = sum(1 for e in history if e.get("status") in ("completed", "max-iterations"))
    rate_limited = sum(1 for e in history if e.get("status") == "rate-limited")
    cancelled = sum(1 for e in history if e.get("status") == "cancelled")

    print()
    print(f"  --- Legend ---")
    print(f"  [>>] running  [OK] completed  [$$] rate-limited  [--] cancelled  [##] max-iters  [!!] error")
    print()
    print(f"  Total: {total} sessions | Completed: {completed} | Rate-limited: {rate_limited} | Cancelled: {cancelled}")
    print("=" * 62)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: history.py <add|end|show> [args...]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "add":
        cmd_add(sys.argv[2:])
    elif cmd == "end":
        cmd_end(sys.argv[2:])
    elif cmd == "show":
        cmd_show()
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
