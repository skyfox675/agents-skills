#!/usr/bin/env python3
"""Expose the canonical Claude skills to Kiro and OpenCode.

Claude, Kiro, and OpenCode all read the same Anthropic Agent Skills format — a
per-skill directory holding a `SKILL.md` with `name` + `description` frontmatter —
but each looks in its own directory. The format is byte-identical, so rather than
fork copies (which drift and bloat the repo) we symlink each platform's skills dir
at the canonical one. One source of truth:

  .kiro/skills      -> ../.claude/skills
  .opencode/skills  -> ../.claude/skills

(Cursor and Copilot read `.claude/skills` directly, so they need no link.)

  python3 scripts/sync-skills.py          # create/repair the symlinks
  python3 scripts/sync-skills.py --check  # exit 1 if a link is missing or wrong
"""
import os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANONICAL = os.path.join(".claude", "skills")
# link path (relative to ROOT) -> symlink target (relative to the link's own dir)
LINKS = {
    os.path.join(".kiro", "skills"): os.path.join("..", ".claude", "skills"),
    os.path.join(".opencode", "skills"): os.path.join("..", ".claude", "skills"),
}


def main():
    check = "--check" in sys.argv
    problems = []

    if not os.path.isdir(os.path.join(ROOT, CANONICAL)):
        print(f"skill sync FAILED — canonical source {CANONICAL} is missing")
        sys.exit(1)

    for rel, target in LINKS.items():
        link = os.path.join(ROOT, rel)
        if os.path.islink(link) and os.readlink(link) == target:
            continue
        if check:
            problems.append(rel)
            continue
        os.makedirs(os.path.dirname(link), exist_ok=True)
        if os.path.islink(link) or os.path.isfile(link):
            os.remove(link)
        elif os.path.isdir(link):
            shutil.rmtree(link)
        os.symlink(target, link)

    if check:
        if problems:
            print("skill links OUT OF DATE — run: python3 scripts/sync-skills.py")
            for p in problems:
                print("  ", p)
            sys.exit(1)
        print(f"skill links in sync ({len(LINKS)} platforms)")
    else:
        print("linked skills -> .kiro/skills + .opencode/skills")


if __name__ == "__main__":
    main()
