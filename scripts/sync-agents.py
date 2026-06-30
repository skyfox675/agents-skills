#!/usr/bin/env python3
"""Regenerate the Cursor, Copilot, Kiro, and OpenCode agent mirrors from the
canonical Claude agents, so the same worker agent is available in every tool and
can't drift.

Canonical source : .claude/agents/<name>.md     (frontmatter: name, description, tools, model)
Generated mirrors:
  .cursor/agents/<name>.md            Cursor   — name, description, model (fast|inherit), readonly
  .github/agents/<name>.agent.md      Copilot  — name, description, model (a model id)
  .kiro/agents/<name>.md              Kiro     — description, tools (category allowlist)
  .opencode/agents/<name>.md          OpenCode — description, mode: subagent, model?, permission

Frontmatter is transformed per platform; the body is copied verbatim (it points at
the skills, which are platform-neutral). Tools that imply writing (Edit/Write) map to
Cursor readonly:false, a Kiro `write` category, and an OpenCode writer (no edit-deny);
otherwise read-only. The cheap tier (model: haiku) maps to Cursor 'fast', Copilot
'Claude Haiku 4.5', and OpenCode 'anthropic/claude-haiku-4-5'; the workhorse tier
inherits each platform's default (see MODEL-DEFAULTS.md). Kiro inherits its configured
model (its model-id strings are environment-specific, so we don't pin one).

OpenCode and Kiro use PLURAL directory names (`.opencode/agents/`, `.kiro/agents/`);
OpenCode accepts the singular `agent/` only for back-compat.

  python3 scripts/sync-agents.py          # regenerate (and prune stale mirrors)
  python3 scripts/sync-agents.py --check  # exit 1 if any mirror is out of date
"""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, ".claude", "agents")
CURSOR = os.path.join(ROOT, ".cursor", "agents")
COPILOT = os.path.join(ROOT, ".github", "agents")
KIRO = os.path.join(ROOT, ".kiro", "agents")
OPENCODE = os.path.join(ROOT, ".opencode", "agents")


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


def has_bash(fm):
    return "Bash" in val(fm, "tools")


def has_mcp(fm):
    return "mcp__" in val(fm, "tools")


def render_cursor(fm, body):
    model = "fast" if val(fm, "model") == "haiku" else "inherit"
    head = [raw_line(fm, "name"), raw_line(fm, "description"),
            f"model: {model}", f"readonly: {'false' if writes(fm) else 'true'}"]
    return "---\n" + "\n".join(head) + "\n---\n\n" + body


def render_copilot(fm, body):
    model = "Claude Haiku 4.5" if val(fm, "model") == "haiku" else "Claude Sonnet 4.6"
    head = [raw_line(fm, "name"), raw_line(fm, "description"), f"model: {model}"]
    return "---\n" + "\n".join(head) + "\n---\n\n" + body


def render_kiro(fm, body):
    # Kiro IDE agent: description + a `tools` category allowlist. The allowlist IS the
    # restriction (read-only agents simply omit write/shell), so no separate permissions
    # block is needed. Model is left to Kiro's configured default.
    cats = ["read"]
    if writes(fm):
        cats.append("write")
    if has_bash(fm):
        cats.append("shell")
    if has_mcp(fm):
        cats.append("@mcp")
    # Quote entries — `@mcp` starts with a YAML-reserved indicator and is invalid bare.
    head = [raw_line(fm, "description"), "tools: [%s]" % ", ".join('"%s"' % c for c in cats)]
    return "---\n" + "\n".join(head) + "\n---\n\n" + body


def render_opencode(fm, body):
    # OpenCode subagent: description + mode, plus a permission map that denies edit (and
    # bash, when the agent has none) for read-only agents. Writers inherit the default
    # allow. The cheap tier pins the Haiku model; the workhorse inherits the global.
    head = [raw_line(fm, "description"), "mode: subagent"]
    if val(fm, "model") == "haiku":
        head.append("model: anthropic/claude-haiku-4-5")
    if not writes(fm):
        head.append("permission:")
        head.append("  edit: deny")
        if not has_bash(fm):
            head.append("  bash: deny")
    return "---\n" + "\n".join(head) + "\n---\n\n" + body


def main():
    check = "--check" in sys.argv
    srcs = sorted(glob.glob(os.path.join(SRC, "*.md")))
    names = {os.path.basename(p)[:-3] for p in srcs}
    if not check:
        for d in (CURSOR, COPILOT, KIRO, OPENCODE):
            os.makedirs(d, exist_ok=True)
    drift = []
    for path in srcs:
        name = os.path.basename(path)[:-3]
        fm, body = parse(path)
        targets = (
            (os.path.join(CURSOR, name + ".md"), render_cursor(fm, body)),
            (os.path.join(COPILOT, name + ".agent.md"), render_copilot(fm, body)),
            (os.path.join(KIRO, name + ".md"), render_kiro(fm, body)),
            (os.path.join(OPENCODE, name + ".md"), render_opencode(fm, body)),
        )
        for target, content in targets:
            existing = open(target).read() if os.path.exists(target) else None
            if check:
                if existing != content:
                    drift.append(os.path.relpath(target, ROOT))
            elif existing != content:
                open(target, "w").write(content)
    stale = []
    for d in (CURSOR, KIRO, OPENCODE):
        for f in glob.glob(os.path.join(d, "*.md")):
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
        print(f"synced {len(srcs)} agents -> .cursor + .github + .kiro + .opencode"
              + (f"; pruned {len(stale)} stale" if stale else ""))


if __name__ == "__main__":
    main()
