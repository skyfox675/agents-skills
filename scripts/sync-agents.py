#!/usr/bin/env python3
"""Regenerate the Cursor and Copilot agent mirrors from the canonical Claude agents,
so the same worker agent is available in all three tools and can't drift.

Canonical source : .claude/agents/<name>.md     (frontmatter: name, description, tools, model)
Generated mirrors:
  .cursor/agents/<name>.md            Cursor  — name, description, model (fast|inherit), readonly
  .github/agents/<name>.agent.md      Copilot — name, description, model (a model id)

Frontmatter is transformed per platform; the body is copied verbatim (it points at the
skills, which are platform-neutral). Tools that imply writing (Edit/Write) map to Cursor
readonly:false; otherwise readonly:true. The cheap tier (model: haiku) maps to Cursor
'fast' and Copilot 'Claude Haiku 4.5'; everything else to Cursor 'inherit' and Copilot
'Claude Sonnet 4.6' (see MODEL-DEFAULTS.md).

  python3 scripts/sync-agents.py          # regenerate (and prune stale mirrors)
  python3 scripts/sync-agents.py --check  # exit 1 if any mirror is out of date
"""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, ".claude", "agents")
CURSOR = os.path.join(ROOT, ".cursor", "agents")
COPILOT = os.path.join(ROOT, ".github", "agents")


def parse(path):
    fm, body = "", open(path).read()
    if body.startswith("---"):
        _, fm, body = body.split("---", 2)
    return fm, body.lstrip("\n")


def raw_line(fm, key):
    for ln in fm.splitlines():
        if re.match(rf"\s*{re.escape(key)}\s*:", ln):
            return ln.rstrip()
    return None


def val(fm, key):
    ln = raw_line(fm, key)
    return ln.split(":", 1)[1].strip().strip('"').strip("'") if ln else ""


def writes(fm):
    t = val(fm, "tools")
    return "Edit" in t or "Write" in t


def render_cursor(fm, body):
    model = "fast" if val(fm, "model") == "haiku" else "inherit"
    head = [raw_line(fm, "name"), raw_line(fm, "description"),
            f"model: {model}", f"readonly: {'false' if writes(fm) else 'true'}"]
    return "---\n" + "\n".join(head) + "\n---\n\n" + body


def render_copilot(fm, body):
    model = "Claude Haiku 4.5" if val(fm, "model") == "haiku" else "Claude Sonnet 4.6"
    head = [raw_line(fm, "name"), raw_line(fm, "description"), f"model: {model}"]
    return "---\n" + "\n".join(head) + "\n---\n\n" + body


def main():
    check = "--check" in sys.argv
    srcs = sorted(glob.glob(os.path.join(SRC, "*.md")))
    names = {os.path.basename(p)[:-3] for p in srcs}
    if not check:
        os.makedirs(CURSOR, exist_ok=True)
        os.makedirs(COPILOT, exist_ok=True)
    drift = []
    for path in srcs:
        name = os.path.basename(path)[:-3]
        fm, body = parse(path)
        for target, content in ((os.path.join(CURSOR, name + ".md"), render_cursor(fm, body)),
                                (os.path.join(COPILOT, name + ".agent.md"), render_copilot(fm, body))):
            existing = open(target).read() if os.path.exists(target) else None
            if check:
                if existing != content:
                    drift.append(os.path.relpath(target, ROOT))
            elif existing != content:
                open(target, "w").write(content)
    stale = []
    for f in glob.glob(os.path.join(CURSOR, "*.md")):
        if os.path.basename(f)[:-3] not in names:
            stale.append(os.path.relpath(f, ROOT)); (None if check else os.remove(f))
    for f in glob.glob(os.path.join(COPILOT, "*.agent.md")):
        if os.path.basename(f)[:-len(".agent.md")] not in names:
            stale.append(os.path.relpath(f, ROOT)); (None if check else os.remove(f))
    if check:
        if drift or stale:
            print("agent mirrors OUT OF DATE — run: python3 scripts/sync-agents.py")
            for p in drift + stale:
                print("  ", p)
            sys.exit(1)
        print(f"agent mirrors in sync ({len(srcs)} agents)")
    else:
        print(f"synced {len(srcs)} agents -> .cursor/agents + .github/agents"
              + (f"; pruned {len(stale)} stale" if stale else ""))


if __name__ == "__main__":
    main()
