#!/usr/bin/env python
"""
Auto-Explorer Interest Graph

Manages the structured interest graph in ~/.claude/interest-graph.json.
Provides concept CRUD, co-occurrence tracking, decay, Thompson Sampling
suggestions, and Markdown generation.

CLI subcommands:
  load                              Load and print graph summary
  add-concepts <json_str>           Add/update concepts from JSON
  record-session <keywords_json>    Record keyword co-occurrences
  suggest <n>                       Suggest top-n topics via Thompson Sampling
  decay                             Apply half-life decay to all weights
  generate-md                       Generate user-interests.md from graph
  graph-brief                       Compact brief for template injection
  migrate <md_path>                 One-time migration from user-interests.md
  update-bandit <id> <engaged>      Update bandit feedback (true/false)
"""

import json
import math
import random
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

GRAPH_FILE = Path.home() / ".claude" / "interest-graph.json"
MD_FILE = Path.home() / ".claude" / "user-interests.md"


def load_graph():
    """Load interest graph from disk. Auto-migrates from MD on first call."""
    if not GRAPH_FILE.exists():
        if MD_FILE.exists():
            return migrate_from_markdown(str(MD_FILE))
        return _empty_graph()
    try:
        with open(GRAPH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return _empty_graph()


def _empty_graph():
    return {
        "version": 1,
        "meta": {"totalSessions": 0, "lastUpdated": "", "halfLifeDays": 90},
        "concepts": {},
        "edges": [],
    }


def save_graph(graph):
    """Write interest graph to disk."""
    graph["meta"]["lastUpdated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    GRAPH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(GRAPH_FILE, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)


def add_concepts(graph, concepts_data):
    """Add or update concepts in the graph.

    concepts_data: list of dicts with keys:
      id (str), labels (dict), category (str),
      broader (list), narrower (list), related (list)
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for c in concepts_data:
        cid = c["id"]
        if cid in graph["concepts"]:
            existing = graph["concepts"][cid]
            existing["weight"] += 1.0
            existing["lastSeen"] = today
            existing["sessionCount"] += 1
            for rel in ("broader", "narrower", "related"):
                old = set(existing.get(rel, []))
                new = set(c.get(rel, []))
                existing[rel] = sorted(old | new)
            if c.get("labels"):
                existing["labels"].update(c["labels"])
        else:
            graph["concepts"][cid] = {
                "labels": c.get("labels", {"en": cid}),
                "category": c.get("category", "general"),
                "weight": 1.0,
                "lastSeen": today,
                "sessionCount": 1,
                "broader": c.get("broader", []),
                "narrower": c.get("narrower", []),
                "related": c.get("related", []),
                "bandit": {"alpha": 1, "beta": 1},
            }


def record_cooccurrences(graph, keywords):
    """Record keyword co-occurrences from a session.

    keywords: list of concept IDs that appeared together.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    edge_map = {}
    for i, e in enumerate(graph["edges"]):
        key = (min(e["src"], e["tgt"]), max(e["src"], e["tgt"]))
        edge_map[key] = i

    for a, b in combinations(sorted(set(keywords)), 2):
        key = (min(a, b), max(a, b))
        if key in edge_map:
            graph["edges"][edge_map[key]]["w"] += 1
            graph["edges"][edge_map[key]]["lastSeen"] = today
        else:
            graph["edges"].append(
                {"src": key[0], "tgt": key[1], "w": 1, "lastSeen": today}
            )
            edge_map[key] = len(graph["edges"]) - 1


def apply_decay(graph):
    """Apply half-life decay to all concept weights.

    Uses: decayed = weight * 2^(-days_elapsed / half_life)
    Prunes concepts with weight < 0.01 and sessionCount <= 1.
    """
    half_life = graph["meta"].get("halfLifeDays", 90)
    today = datetime.now(timezone.utc).date()

    to_remove = []
    for cid, concept in graph["concepts"].items():
        last_seen = concept.get("lastSeen", "")
        if not last_seen:
            continue
        try:
            last = datetime.strptime(last_seen, "%Y-%m-%d").date()
            days = (today - last).days
            if days <= 0:
                continue
            decay_factor = math.pow(2, -days / half_life)
            concept["weight"] *= decay_factor
            if concept["weight"] < 0.01 and concept["sessionCount"] <= 1:
                to_remove.append(cid)
        except ValueError:
            continue

    for cid in to_remove:
        del graph["concepts"][cid]
        graph["edges"] = [
            e for e in graph["edges"] if e["src"] != cid and e["tgt"] != cid
        ]


def suggest_topics(graph, n=5, recent_sessions=None, seed=None):
    """Suggest topics using Thompson Sampling with serendipity bonus.

    Returns: list of (concept_id, score, reason) tuples, sorted by score desc.
    """
    if seed is not None:
        random.seed(seed)

    recent = set(recent_sessions or [])
    half_life = graph["meta"].get("halfLifeDays", 90)
    today = datetime.now(timezone.utc).date()

    candidates = []
    for cid, concept in graph["concepts"].items():
        if concept["weight"] < 0.05:
            continue
        if cid in recent:
            continue

        alpha = concept.get("bandit", {}).get("alpha", 1)
        beta_val = concept.get("bandit", {}).get("beta", 1)
        ts_score = random.betavariate(max(alpha, 0.1), max(beta_val, 0.1))

        last_seen = concept.get("lastSeen", "")
        days = 0
        if last_seen:
            try:
                days = (today - datetime.strptime(last_seen, "%Y-%m-%d").date()).days
                decay = math.pow(2, -days / half_life)
            except ValueError:
                decay = 0.5
        else:
            decay = 0.5

        connection_count = (
            len(concept.get("broader", []))
            + len(concept.get("narrower", []))
            + len(concept.get("related", []))
        )
        serendipity = 1.0 / (1.0 + connection_count * 0.1)

        score = ts_score * decay * (1.0 + 0.3 * serendipity)

        if days > 60:
            reason = "revisit (not seen in a while)"
        elif connection_count == 0:
            reason = "unexplored connection"
        elif alpha > beta_val * 2:
            reason = "strong interest"
        else:
            reason = "balanced exploration"

        candidates.append((cid, score, reason))

    candidates.sort(key=lambda x: -x[1])
    return candidates[:n]


def update_bandit(graph, concept_id, engaged):
    """Update Thompson Sampling state for a concept.

    engaged: True = user explored (alpha++), False = suggested but ignored (beta++)
    """
    if concept_id not in graph["concepts"]:
        return
    bandit = graph["concepts"][concept_id].setdefault("bandit", {"alpha": 1, "beta": 1})
    if engaged:
        bandit["alpha"] = bandit.get("alpha", 1) + 1
    else:
        bandit["beta"] = bandit.get("beta", 1) + 1


def generate_markdown(graph):
    """Generate user-interests.md content from the interest graph.

    Produces the same format as the current file so CLAUDE.md instructions
    and any tools reading it continue to work.
    """
    lines = []
    lines.append("---")
    lines.append("version: 2")
    lines.append("created_at: 2026-02-14")
    lines.append(f"last_updated: {graph['meta'].get('lastUpdated', '')}")
    lines.append(f"session_count: {graph['meta'].get('totalSessions', 0)}")
    lines.append("source: auto-generated from interest-graph.json")
    lines.append("---")
    lines.append("")
    lines.append("# User Interests")
    lines.append("")

    categories = {}
    for cid, concept in graph["concepts"].items():
        cat = concept.get("category", "general")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((cid, concept))

    cat_order = sorted(k for k in categories if k != "general")
    if "general" in categories:
        cat_order.append("general")

    for cat in cat_order:
        items = categories[cat]
        items.sort(key=lambda x: -x[1]["weight"])

        cat_title = cat.replace("-", " ").title()
        if cat.lower() == "ai-ml":
            cat_title = "AI & ML"
        elif cat.lower() == "aiops-observability":
            cat_title = "AIOps & Observability"
        lines.append(f"## {cat_title}")

        keywords = [cid for cid, _ in items]
        lines.append(f"- **keywords**: [{', '.join(keywords)}]")

        top_labels = [c["labels"].get("en", cid) for cid, c in items[:5]]
        lines.append(
            f"- **description**: Topics related to {', '.join(top_labels)}"
        )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Suggested Next Directions")
    lines.append("")

    suggestions = suggest_topics(graph, n=10, seed=42)
    if suggestions:
        for i, (cid, score, reason) in enumerate(suggestions, 1):
            label = graph["concepts"][cid]["labels"].get("en", cid)
            lines.append(f"{i}. {label} ({reason})")
    else:
        lines.append("No suggestions yet — explore more topics to build your graph.")

    lines.append("")
    return "\n".join(lines)


def generate_brief(graph, max_concepts=15, max_communities=5, max_gaps=5):
    """Generate a compact text brief of the interest graph for template injection.

    Outputs: "Top Concepts", "Knowledge Communities", "Structural Gaps".
    Returns "(No interest graph data available)" on empty graph.
    """
    if not graph["concepts"]:
        return "(No interest graph data available)"

    lines = []

    # Top Concepts by weight
    sorted_concepts = sorted(
        graph["concepts"].items(), key=lambda x: -x[1]["weight"]
    )[:max_concepts]
    lines.append("Top Concepts:")
    for cid, concept in sorted_concepts:
        label = concept["labels"].get("en", cid)
        cat = concept.get("category", "general")
        lines.append(f"  - {label} (category: {cat}, weight: {concept['weight']:.1f})")

    # Knowledge Communities (use min_edge_weight=1 for inclusive brief)
    communities = detect_communities(graph, min_edge_weight=1)
    multi_member = {
        label: members
        for label, members in sorted(
            communities.items(), key=lambda x: -len(x[1])
        )
        if len(members) > 1
    }
    if multi_member:
        lines.append("")
        lines.append("Knowledge Communities:")
        for i, (label, members) in enumerate(multi_member.items()):
            if i >= max_communities:
                break
            display = ", ".join(sorted(members)[:8])
            if len(members) > 8:
                display += f", ... ({len(members)} total)"
            lines.append(f"  - [{label}] {display}")

    # Structural Gaps
    gaps = find_gaps(graph, n=max_gaps)
    if gaps:
        lines.append("")
        lines.append("Structural Gaps:")
        for a, b, shared_count, shared in gaps:
            suffix = ", ..." if shared_count > 3 else ""
            lines.append(f"  - {a} <-> {b} ({shared_count} shared: {', '.join(shared[:3])}{suffix})")

    return "\n".join(lines)


def migrate_from_markdown(md_path):
    """Parse existing user-interests.md and create interest-graph.json.

    Returns the populated graph (also saves it to disk).
    """
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    graph = _empty_graph()

    # Parse frontmatter
    in_fm = False
    for line in content.split("\n"):
        if line.strip() == "---":
            if in_fm:
                break
            in_fm = True
            continue
        if in_fm and ":" in line:
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if k == "session_count":
                try:
                    graph["meta"]["totalSessions"] = int(v)
                except ValueError:
                    pass

    # Parse categories and keywords
    current_category = "general"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for line in content.split("\n"):
        cat_match = re.match(r"^## (.+)", line)
        if cat_match:
            title = cat_match.group(1).strip()
            if title in (
                "Recently Explored",
                "Explored Topics Archive",
                "Suggested Next Directions",
                "User Interests",
            ):
                current_category = None
                continue
            current_category = (
                title.lower().replace(" & ", "-").replace(" ", "-")
            )
            continue

        if current_category is None:
            continue

        kw_match = re.match(r"^- \*\*keywords\*\*: \[(.+)\]", line)
        if kw_match:
            keywords_raw = kw_match.group(1)
            keywords = [k.strip() for k in keywords_raw.split(",")]

            for kw in keywords:
                slug = kw.lower().replace(" ", "-")
                if slug not in graph["concepts"]:
                    graph["concepts"][slug] = {
                        "labels": {"en": kw},
                        "category": current_category,
                        "weight": 1.0,
                        "lastSeen": today,
                        "sessionCount": 1,
                        "broader": (
                            [current_category]
                            if current_category != "general"
                            else []
                        ),
                        "narrower": [],
                        "related": [],
                        "bandit": {"alpha": 1, "beta": 1},
                    }

            # Build co-occurrence edges from adjacent keywords
            slugs = [k.lower().replace(" ", "-") for k in keywords]
            for i in range(len(slugs) - 1):
                a, b = min(slugs[i], slugs[i + 1]), max(slugs[i], slugs[i + 1])
                if a != b:
                    graph["edges"].append(
                        {"src": a, "tgt": b, "w": 1, "lastSeen": today}
                    )

    graph["meta"]["lastUpdated"] = today
    save_graph(graph)
    return graph


def detect_communities(graph, min_edge_weight=2):
    """Simple label propagation community detection.

    Groups concepts into communities based on co-occurrence edges.
    Returns dict: {community_label: [concept_ids]}.
    """
    adj = {}
    for e in graph["edges"]:
        if e["w"] < min_edge_weight:
            continue
        adj.setdefault(e["src"], []).append(e["tgt"])
        adj.setdefault(e["tgt"], []).append(e["src"])

    labels = {node: node for node in adj}

    for _ in range(10):
        changed = False
        for node in adj:
            if not adj[node]:
                continue
            neighbor_labels = [labels.get(n, n) for n in adj[node]]
            most_common = Counter(neighbor_labels).most_common(1)[0][0]
            if labels[node] != most_common:
                labels[node] = most_common
                changed = True
        if not changed:
            break

    communities = {}
    for node, label in labels.items():
        communities.setdefault(label, []).append(node)

    return communities


def find_gaps(graph, n=5, max_nodes=500):
    """Find structural gaps: concept pairs that share neighbors but aren't connected.

    Returns list of (node_a, node_b, shared_count, shared_list) tuples.
    Skips O(n^2) scan when the graph exceeds max_nodes to avoid slow execution.
    """
    adj = {}
    for e in graph["edges"]:
        adj.setdefault(e["src"], set()).add(e["tgt"])
        adj.setdefault(e["tgt"], set()).add(e["src"])
    for cid, c in graph["concepts"].items():
        for rel in ("broader", "narrower", "related"):
            for other in c.get(rel, []):
                adj.setdefault(cid, set()).add(other)
                adj.setdefault(other, set()).add(cid)

    nodes = list(adj.keys())

    # Safeguard: skip O(n^2) pairwise scan for very large graphs
    if len(nodes) > max_nodes:
        return []

    gaps = []
    seen = set()
    for i, node_a in enumerate(nodes):
        for node_b in nodes[i + 1:]:
            if node_b in adj.get(node_a, set()):
                continue
            key = (node_a, node_b)
            if key in seen:
                continue
            seen.add(key)

            shared = adj.get(node_a, set()) & adj.get(node_b, set())
            if len(shared) >= 2:
                gaps.append((node_a, node_b, len(shared), sorted(shared)))

    gaps.sort(key=lambda x: -x[2])
    return gaps[:n]


# --- CLI ---

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: interest_graph.py <load|add-concepts|record-session|suggest|decay|generate-md|migrate|update-bandit> [args...]",
            file=sys.stderr,
        )
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "load":
        graph = load_graph()
        n_concepts = len(graph["concepts"])
        n_edges = len(graph["edges"])
        sessions = graph["meta"].get("totalSessions", 0)
        print(f"Interest graph: {n_concepts} concepts, {n_edges} edges, {sessions} sessions")

    elif cmd == "add-concepts":
        if len(sys.argv) < 3:
            print("Usage: interest_graph.py add-concepts <json>", file=sys.stderr)
            sys.exit(1)
        graph = load_graph()
        concepts_data = json.loads(sys.argv[2])
        add_concepts(graph, concepts_data)
        save_graph(graph)
        print(f"Updated: {len(graph['concepts'])} concepts")

    elif cmd == "record-session":
        if len(sys.argv) < 3:
            print("Usage: interest_graph.py record-session <keywords_json>", file=sys.stderr)
            sys.exit(1)
        graph = load_graph()
        keywords = json.loads(sys.argv[2])
        record_cooccurrences(graph, keywords)
        graph["meta"]["totalSessions"] = graph["meta"].get("totalSessions", 0) + 1
        save_graph(graph)
        print(f"Recorded session: {len(keywords)} keywords, {len(graph['edges'])} edges")

    elif cmd == "suggest":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        graph = load_graph()
        suggestions = suggest_topics(graph, n=n)
        if suggestions:
            for cid, score, reason in suggestions:
                label = graph["concepts"][cid]["labels"].get("en", cid)
                print(f"  {label} ({reason}, score: {score:.3f})")
        else:
            print("No suggestions available — explore more topics first.")

    elif cmd == "decay":
        graph = load_graph()
        before = len(graph["concepts"])
        apply_decay(graph)
        after = len(graph["concepts"])
        save_graph(graph)
        pruned = before - after
        if pruned > 0:
            print(f"Decay applied: {pruned} concepts pruned, {after} remaining")
        else:
            print(f"Decay applied: {after} concepts (none pruned)")

    elif cmd == "generate-md":
        graph = load_graph()
        md = generate_markdown(graph)
        print(md)

    elif cmd == "graph-brief":
        graph = load_graph()
        print(generate_brief(graph))

    elif cmd == "migrate":
        md_path = sys.argv[2] if len(sys.argv) > 2 else str(MD_FILE)
        graph = migrate_from_markdown(md_path)
        print(f"Migrated: {len(graph['concepts'])} concepts, {len(graph['edges'])} edges")

    elif cmd == "communities":
        graph = load_graph()
        min_w = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        communities = detect_communities(graph, min_edge_weight=min_w)
        for label, members in sorted(communities.items(), key=lambda x: -len(x[1])):
            if len(members) > 1:
                print(f"  [{label}] {len(members)} concepts: {', '.join(sorted(members)[:10])}")

    elif cmd == "gaps":
        graph = load_graph()
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        gaps = find_gaps(graph, n=n)
        if gaps:
            for a, b, shared_count, shared in gaps:
                print(f"  {a} <-> {b} ({shared_count} shared: {', '.join(shared[:5])})")
        else:
            print("No structural gaps found.")

    elif cmd == "update-bandit":
        if len(sys.argv) < 4:
            print("Usage: interest_graph.py update-bandit <concept_id> <true|false>", file=sys.stderr)
            sys.exit(1)
        graph = load_graph()
        concept_id = sys.argv[2]
        engaged = sys.argv[3].lower() in ("true", "1", "yes")
        update_bandit(graph, concept_id, engaged)
        save_graph(graph)
        if concept_id in graph["concepts"]:
            b = graph["concepts"][concept_id]["bandit"]
            print(f"Updated {concept_id}: alpha={b['alpha']}, beta={b['beta']}")
        else:
            print(f"Concept not found: {concept_id}")

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
