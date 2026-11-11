#!/usr/bin/env python3
"""Assemble the publishable plugin payloads from the canonical sources.

This repo doubles as its own plugin marketplace for two ecosystems:

  plugins/agents-skills/         Claude Code   (.claude-plugin/plugin.json)
  plugins/agents-skills-cursor/  Cursor        (.cursor-plugin/plugin.json)
  plugins/agents-skills-codex/   Codex/ChatGPT (plugin.json at the plugin root)

All take the same skills, because the Agent Skills format is identical. Agents and
commands differ per tool, so each payload pulls from that tool's generated mirror:

  payload            skills            agents            commands
  Claude             .claude/skills    .claude/agents    .claude/commands
  Cursor             .claude/skills    .cursor/agents    .cursor/commands
  Codex              .claude/skills    -                 -

Codex plugins carry skills, MCP servers, hooks and apps, but not agents or commands,
so the Codex payload is skills only. Its agents ship as .codex/agents/ instead.

The mirrors are produced by sync-agents.py and sync-commands.py, so run those first
(the Makefile's `sync` target already orders them ahead of this script).

Payloads are real files, never symlinks: each tool installs the plugin directory on
its own, and a link escaping that directory would dangle. The payload dirs are wiped
and rebuilt so deletions and renames propagate. The three plugin manifests are hand
maintained and version stamped by scripts/set-version.py; this script never touches
them.

  python3 scripts/build-plugin.py          # rebuild every payload
  python3 scripts/build-plugin.py --check  # exit 1 if any is out of date
"""
import filecmp, os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# plugin dir -> {payload subdir: (source dir, kind)}
PLUGINS = {
    "agents-skills": {
        "skills": (".claude/skills", "skill-dirs"),
        "agents": (".claude/agents", "md-files"),
        "commands": (".claude/commands", "md-files"),
    },
    "agents-skills-cursor": {
        "skills": (".claude/skills", "skill-dirs"),
        "agents": (".cursor/agents", "md-files"),
        "commands": (".cursor/commands", "md-files"),
    },
    "agents-skills-codex": {
        "skills": (".claude/skills", "skill-dirs"),
    },
}


def collect(payload):
    """Return {relpath-under-plugin: absolute-source-path} for one payload."""
    files = {}
    for sub, (rel_src, kind) in payload.items():
        src = os.path.join(ROOT, rel_src)
        if not os.path.isdir(src):
            continue
        if kind == "md-files":
            for f in sorted(os.listdir(src)):
                if f.endswith(".md"):
                    files[os.path.join(sub, f)] = os.path.join(src, f)
        else:  # a skill is a directory containing a SKILL.md
            for name in sorted(os.listdir(src)):
                d = os.path.join(src, name)
                if not os.path.isdir(d) or not os.path.isfile(os.path.join(d, "SKILL.md")):
                    continue  # skips helper dirs like _evals
                for dirpath, _, filenames in os.walk(d):
                    for f in sorted(filenames):
                        full = os.path.join(dirpath, f)
                        files[os.path.join(sub, os.path.relpath(full, src))] = full
    return files


def existing(plugin_dir, payload):
    out = set()
    for sub in payload:
        base = os.path.join(plugin_dir, sub)
        for dirpath, _, filenames in os.walk(base):
            for f in filenames:
                out.add(os.path.relpath(os.path.join(dirpath, f), plugin_dir))
    return out


def counts(want):
    skills = len({r.split(os.sep)[1] for r in want if r.startswith("skills" + os.sep)})
    agents = sum(1 for r in want if r.startswith("agents" + os.sep))
    cmds = sum(1 for r in want if r.startswith("commands" + os.sep))
    return skills, agents, cmds


def main():
    check = "--check" in sys.argv
    stale = []

    for name, payload in PLUGINS.items():
        plugin_dir = os.path.join(ROOT, "plugins", name)
        want = collect(payload)
        if not want:
            print(f"build-plugin FAILED: no sources found for {name}")
            sys.exit(1)

        if check:
            have = existing(plugin_dir, payload)
            missing = sorted(set(want) - have)
            extra = sorted(have - set(want))
            changed = sorted(
                rel for rel in set(want) & have
                if not filecmp.cmp(os.path.join(plugin_dir, rel), want[rel], shallow=False)
            )
            if missing or extra or changed:
                stale.append(name)
                print(f"plugin payload OUT OF DATE: plugins/{name}")
                for rel in missing:
                    print("   missing:", rel)
                for rel in extra:
                    print("   stale:  ", rel)
                for rel in changed:
                    print("   changed:", rel)
            else:
                s, a, c = counts(want)
                print(f"plugins/{name} in sync ({s} skills, {a} agents, {c} commands)")
            continue

        for sub in payload:
            shutil.rmtree(os.path.join(plugin_dir, sub), ignore_errors=True)
        for rel, src in want.items():
            dst = os.path.join(plugin_dir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        s, a, c = counts(want)
        print(f"built plugins/{name} ({s} skills, {a} agents, {c} commands)")

    if check and stale:
        print("run: python3 scripts/build-plugin.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
