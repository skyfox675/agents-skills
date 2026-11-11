#!/usr/bin/env python3
"""Regenerate the Cursor, Copilot, and Codex command mirrors from the canonical Claude
commands, so the same slash command registers in every tool and can't drift.

Canonical source : .claude/commands/<name>.md   (frontmatter + $ARGUMENTS)
Generated mirrors:
  .cursor/commands/<name>.md          Cursor   — plain markdown, no frontmatter
  .github/prompts/<name>.prompt.md    Copilot  — frontmatter (description/argument-hint/agent) + ${input:args}
  .codex/prompts/<name>.md            Codex    — frontmatter (description/argument-hint) + $ARGUMENTS

Codex reads custom prompts only from ~/.codex/prompts/ (no project-level home), so
users copy .codex/prompts/ there and invoke `/prompts:<name>`. Codex expands $1-$9 and
any uppercase $NAME, so every `$` token other than $ARGUMENTS is escaped as `$$`.
OpenAI has deprecated custom prompts in favour of skills; the mirror stays until
commands are recast as skills.

Usage:
  python3 scripts/sync-commands.py          # regenerate the mirrors (and prune stale ones)
  python3 scripts/sync-commands.py --check  # exit 1 if any mirror is out of date (for CI / a pre-commit hook)
"""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, ".claude", "commands")
CURSOR = os.path.join(ROOT, ".cursor", "commands")
COPILOT = os.path.join(ROOT, ".github", "prompts")
CODEX = os.path.join(ROOT, ".codex", "prompts")

ARG = re.compile(r"`?\$ARGUMENTS`?")          # the Claude argument token, with or without backticks
CODEX_DOLLAR = re.compile(r"\$(?!ARGUMENTS\b)(?=[A-Z0-9$])")  # a `$` Codex would expand
KEEP_FM = re.compile(r"\s*(description|argument-hint)\s*:")


def split_frontmatter(text):
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[1], parts[2].lstrip("\n")
    return "", text


def render(path):
    """Return (name, cursor_content, copilot_content, codex_content) for one source command."""
    name = os.path.basename(path)[:-3]
    fm, body = split_frontmatter(open(path).read())
    # Cursor: no frontmatter; the typed text after the command is the input.
    cursor = ARG.sub("the text you type after the command", body)
    # Copilot: keep description + argument-hint verbatim (preserves quoting), drop
    # the Claude-only allowed-tools, add agent mode; ${input:args} is Copilot's input var.
    keep = [ln.rstrip() for ln in fm.splitlines() if KEEP_FM.match(ln)]
    keep.append("agent: agent")
    copilot = "---\n" + "\n".join(keep) + "\n---\n\n" + body.replace("$ARGUMENTS", "${input:args}")
    # Codex: same two keys; $ARGUMENTS is native, every other `$` token is escaped.
    codex = "---\n" + "\n".join(keep[:-1]) + "\n---\n\n" + CODEX_DOLLAR.sub("$$", body)
    return name, cursor, copilot, codex


def main():
    check = "--check" in sys.argv
    srcs = sorted(glob.glob(os.path.join(SRC, "*.md")))
    names = {os.path.basename(p)[:-3] for p in srcs}
    if not check:
        os.makedirs(CURSOR, exist_ok=True)
        os.makedirs(COPILOT, exist_ok=True)
        os.makedirs(CODEX, exist_ok=True)
    drift = []
    for path in srcs:
        name, cursor, copilot, codex = render(path)
        for target, content in ((os.path.join(CURSOR, name + ".md"), cursor),
                                (os.path.join(COPILOT, name + ".prompt.md"), copilot),
                                (os.path.join(CODEX, name + ".md"), codex)):
            existing = open(target).read() if os.path.exists(target) else None
            if check:
                if existing != content:
                    drift.append(os.path.relpath(target, ROOT))
            elif existing != content:
                open(target, "w").write(content)
    # stale mirrors (a command was renamed/deleted in the source)
    stale = []
    for f in glob.glob(os.path.join(CURSOR, "*.md")) + glob.glob(os.path.join(CODEX, "*.md")):
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
        print(f"synced {len(srcs)} commands -> .cursor/commands + .github/prompts + .codex/prompts"
              + (f"; pruned {len(stale)} stale" if stale else ""))


if __name__ == "__main__":
    main()
