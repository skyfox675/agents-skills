#!/usr/bin/env python3
"""Regenerate the Cursor and Copilot command mirrors from the canonical Claude
commands, so the same slash command registers in all three tools and can't drift.

Canonical source : .claude/commands/<name>.md   (frontmatter + $ARGUMENTS)
Generated mirrors:
  .cursor/commands/<name>.md          Cursor   — plain markdown, no frontmatter
  .github/prompts/<name>.prompt.md    Copilot  — frontmatter (description/argument-hint/agent) + ${input:args}

Usage:
  python3 scripts/sync-commands.py          # regenerate the mirrors (and prune stale ones)
  python3 scripts/sync-commands.py --check  # exit 1 if any mirror is out of date (for CI / a pre-commit hook)
"""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, ".claude", "commands")
CURSOR = os.path.join(ROOT, ".cursor", "commands")
COPILOT = os.path.join(ROOT, ".github", "prompts")

ARG = re.compile(r"`?\$ARGUMENTS`?")          # the Claude argument token, with or without backticks
KEEP_FM = re.compile(r"\s*(description|argument-hint)\s*:")


def split_frontmatter(text):
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[1], parts[2].lstrip("\n")
    return "", text


def render(path):
    """Return (name, cursor_content, copilot_content) for one source command."""
    name = os.path.basename(path)[:-3]
    fm, body = split_frontmatter(open(path).read())
    # Cursor: no frontmatter; the typed text after the command is the input.
    cursor = ARG.sub("the text you type after the command", body)
    # Copilot: keep description + argument-hint verbatim (preserves quoting), drop
    # the Claude-only allowed-tools, add agent mode; ${input:args} is Copilot's input var.
    keep = [ln.rstrip() for ln in fm.splitlines() if KEEP_FM.match(ln)]
    keep.append("agent: agent")
    copilot = "---\n" + "\n".join(keep) + "\n---\n\n" + body.replace("$ARGUMENTS", "${input:args}")
    return name, cursor, copilot


def main():
    check = "--check" in sys.argv
    srcs = sorted(glob.glob(os.path.join(SRC, "*.md")))
    names = {os.path.basename(p)[:-3] for p in srcs}
    if not check:
        os.makedirs(CURSOR, exist_ok=True)
        os.makedirs(COPILOT, exist_ok=True)
    drift = []
    for path in srcs:
        name, cursor, copilot = render(path)
        for target, content in ((os.path.join(CURSOR, name + ".md"), cursor),
                                (os.path.join(COPILOT, name + ".prompt.md"), copilot)):
            existing = open(target).read() if os.path.exists(target) else None
            if check:
                if existing != content:
                    drift.append(os.path.relpath(target, ROOT))
            elif existing != content:
                open(target, "w").write(content)
    # stale mirrors (a command was renamed/deleted in the source)
    stale = []
    for f in glob.glob(os.path.join(CURSOR, "*.md")):
        if os.path.basename(f)[:-3] not in names:
            stale.append(os.path.relpath(f, ROOT)); (None if check else os.remove(f))
    for f in glob.glob(os.path.join(COPILOT, "*.prompt.md")):
        if os.path.basename(f)[:-len(".prompt.md")] not in names:
            stale.append(os.path.relpath(f, ROOT)); (None if check else os.remove(f))
    if check:
        if drift or stale:
            print("command mirrors OUT OF DATE — run: python3 scripts/sync-commands.py")
            for p in drift + stale:
                print("  ", p)
            sys.exit(1)
        print(f"command mirrors in sync ({len(srcs)} commands)")
    else:
        print(f"synced {len(srcs)} commands -> .cursor/commands + .github/prompts"
              + (f"; pruned {len(stale)} stale" if stale else ""))


if __name__ == "__main__":
    main()
