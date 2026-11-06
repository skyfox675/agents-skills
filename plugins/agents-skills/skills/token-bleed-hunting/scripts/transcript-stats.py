#!/usr/bin/env python3
"""Aggregate token-bleed signals from Claude Code session transcripts (JSONL).

Prints counts, sizes, model and tool names, and repo-relative paths only. It
never prints prompt text, tool input or output, file contents or ids, so its
output is safe to reason over.

The transcript format is internal to Claude Code and changes between versions.
Field names here match recent versions; run with --keys first if numbers look
wrong, and adjust.

Usage:
  python3 -I transcript-stats.py [--root REPO] [--ttl SECONDS] FILE.jsonl [...]
  python3 -I transcript-stats.py --keys FILE.jsonl

Pass subagent transcripts (<session>/subagents/*.jsonl) too. Their requests
count as subagent work and stay out of the session count and the floor.
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime

PROMPT_FIELDS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")


def parse_ts(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def entries(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(e, dict):
                yield e


def key_shapes(path):
    """Key paths with counts, values stripped, for discovering the format."""
    shapes = Counter()

    def walk(node, prefix):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{prefix}.{k}" if prefix else k)
        elif isinstance(node, list):
            for v in node:
                walk(v, f"{prefix}[]")
        else:
            shapes[prefix] += 1

    for e in entries(path):
        walk(e, "")
    return shapes


def as_dict(value):
    return value if isinstance(value, dict) else {}


def blocks(message):
    content = message.get("content")
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def tokens(usage, field):
    try:
        return int(usage.get(field) or 0)
    except (TypeError, ValueError):
        return 0


def prompt_side(usage):
    return sum(tokens(usage, f) for f in PROMPT_FIELDS)


def size_of(value):
    return len(json.dumps(value, ensure_ascii=False).encode("utf-8"))


def p90(values):
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * 0.9))]


def relpath(path, cwd, root):
    """Repo-relative path, or None for anything outside the repo or unknown."""
    if not isinstance(path, str) or not path or not root:
        return None
    if not os.path.isabs(path):
        if not isinstance(cwd, str) or not cwd:
            return None
        path = os.path.join(cwd, path)
    path = os.path.realpath(path)
    if path == root or path.startswith(root + os.sep):
        return os.path.relpath(path, root)
    return None


def session_stats(path, root, ttl, seen):
    is_subagent = f"{os.sep}subagents{os.sep}" in path
    usage_by_msg = {}  # one API response spans several lines that repeat its usage; keep one
    model_by_msg = {}
    main_order = []  # (timestamp, key) of main-thread requests, for the floor and idle gaps
    sidechain = set()
    tool_names = {}
    tools = defaultdict(lambda: {"calls": 0, "errors": 0, "result_bytes": []})
    reads = Counter()
    boundaries = summaries = 0

    for e in entries(path):
        if e.get("type") == "system" and e.get("subtype") == "compact_boundary":
            boundaries += 1
        if e.get("isCompactSummary"):
            summaries += 1
        msg = as_dict(e.get("message"))
        if e.get("type") == "assistant":
            key = msg.get("id") or e.get("requestId") or e.get("uuid")
            usage = msg.get("usage")
            # Resumed and forked sessions copy earlier messages; count each response once overall.
            if isinstance(usage, dict) and key and (key in usage_by_msg or key not in seen):
                if key not in usage_by_msg:
                    seen.add(key)
                    if is_subagent or e.get("isSidechain"):
                        sidechain.add(key)
                    else:
                        main_order.append((parse_ts(e.get("timestamp")), key))
                usage_by_msg[key] = usage
                model_by_msg[key] = msg.get("model") or "?"
            for b in blocks(msg):
                if b.get("type") == "tool_use":
                    name = b.get("name") if isinstance(b.get("name"), str) else "?"
                    tool_names[b.get("id")] = name
                    tools[name]["calls"] += 1
                    if name == "Read":
                        target = relpath(as_dict(b.get("input")).get("file_path"), e.get("cwd"), root)
                        if target:
                            reads[target] += 1
        elif e.get("type") == "user":
            for b in blocks(msg):
                if b.get("type") == "tool_result":
                    name = tool_names.get(b.get("tool_use_id"), "?")
                    tools[name]["result_bytes"].append(size_of(b.get("content")))
                    if b.get("is_error"):
                        tools[name]["errors"] += 1

    def total(field):
        return sum(tokens(u, field) for u in usage_by_msg.values())

    main_order.sort(key=lambda item: (item[0] is None, item[0] or datetime.min))
    floor = None
    gaps = 0
    if main_order:
        floor = prompt_side(usage_by_msg[main_order[0][1]])
        for (prev, _), (cur, key) in zip(main_order, main_order[1:]):
            if prev and cur and (cur - prev).total_seconds() > ttl:
                usage = usage_by_msg[key]
                # A rewrite after an expired cache writes most of the prefix, not just the new turn.
                if tokens(usage, "cache_creation_input_tokens") * 2 >= prompt_side(usage) > 0:
                    gaps += 1

    by_model = defaultdict(lambda: {"requests": 0, "prompt_tokens": 0, "output": 0})
    for key, usage in usage_by_msg.items():
        m = by_model[model_by_msg.get(key, "?")]
        m["requests"] += 1
        m["prompt_tokens"] += prompt_side(usage)
        m["output"] += tokens(usage, "output_tokens")

    inp, out = total("input_tokens"), total("output_tokens")
    cread, cwrite = total("cache_read_input_tokens"), total("cache_creation_input_tokens")
    side = inp + cread + cwrite
    return {
        "subagent": is_subagent,
        "requests": len(usage_by_msg),
        "sidechain_requests": len(sidechain),
        "input": inp,
        "output": out,
        "cache_read": cread,
        "cache_write": cwrite,
        "cache_hit_ratio": round(cread / side, 3) if side else None,
        "floor": floor,
        "idle_gap_rewrites": gaps,
        # Each compaction writes a boundary marker and a summary entry; count it once.
        "compactions": boundaries or summaries,
        "by_model": dict(by_model),
        "tools": {
            name: {
                "calls": t["calls"],
                "errors": t["errors"],
                "result_bytes": sum(t["result_bytes"]),
                "result_bytes_p90": p90(t["result_bytes"]),
            }
            for name, t in sorted(tools.items(), key=lambda kv: -sum(kv[1]["result_bytes"]))
        },
        "repeat_reads": {p: n for p, n in reads.most_common(10) if n >= 3},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--root", help="repo root; only Read paths inside it are named")
    ap.add_argument("--ttl", type=int, default=300, help="cache TTL in seconds for idle-gap detection (default 300)")
    ap.add_argument("--keys", action="store_true", help="print key paths and counts only, then exit")
    args = ap.parse_args()

    if args.keys:
        shapes = Counter()
        for f in args.files:
            try:
                shapes.update(key_shapes(f))
            except OSError:
                continue
        for k, n in shapes.most_common(80):
            print(f"{n:8d}  {k}")
        return

    root = os.path.realpath(args.root) if args.root else None
    seen = set()
    unreadable = 0
    results = []
    # Main transcripts first, so a message copied into a subagent or later file is credited to its origin.
    for f in sorted(args.files, key=lambda p: f"{os.sep}subagents{os.sep}" in p):
        try:
            stats = session_stats(f, root, args.ttl, seen)
        except OSError:
            unreadable += 1
            continue
        if stats["requests"]:
            results.append(stats)

    mains = [s for s in results if not s["subagent"]]
    if not results:
        print(json.dumps({"sessions": 0, "subagent_files": 0, "unreadable": unreadable}))
        return
    floors = sorted(s["floor"] for s in mains if s["floor"] is not None) or [0]
    totals = {f: sum(s[f] for s in results) for f in
              ("requests", "sidechain_requests", "input", "output", "cache_read", "cache_write",
               "idle_gap_rewrites", "compactions")}
    side = totals["input"] + totals["cache_read"] + totals["cache_write"]
    totals["cache_hit_ratio"] = round(totals["cache_read"] / side, 3) if side else None
    totals["floor_p50"] = floors[len(floors) // 2]
    totals["floor_p90"] = floors[min(len(floors) - 1, int(len(floors) * 0.9))]
    model_tot = defaultdict(lambda: {"requests": 0, "prompt_tokens": 0, "output": 0})
    tool_tot = defaultdict(lambda: {"calls": 0, "errors": 0, "result_bytes": 0})
    for s in results:
        for name, m in s["by_model"].items():
            for k in m:
                model_tot[name][k] += m[k]
        for name, t in s["tools"].items():
            for k in ("calls", "errors", "result_bytes"):
                tool_tot[name][k] += t[k]
    totals["by_model"] = dict(model_tot)
    totals["tools_by_result_bytes"] = dict(sorted(tool_tot.items(), key=lambda kv: -kv[1]["result_bytes"])[:12])
    # Files are named by session id; number them instead so no identifier leaves this script.
    per_file = {}
    for prefix, group in (("s", mains), ("a", [s for s in results if s["subagent"]])):
        for i, s in enumerate(group):
            per_file[f"{prefix}{i + 1}"] = s
    print(json.dumps({"sessions": len(mains), "subagent_files": len(results) - len(mains),
                      "unreadable": unreadable, "totals": totals, "per_file": per_file}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
