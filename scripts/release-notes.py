#!/usr/bin/env python3
"""Generate GitHub release notes from the built plugin payloads.

Reads the Claude payload for the inventory (both payloads carry the same skills, and
the agents and commands differ only in frontmatter) and emits markdown for
`gh release create --notes-file`.

  python3 scripts/release-notes.py 2026.7.11.0 > dist/notes.md
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(ROOT, "plugins", "agents-skills")
REPO = "skyfox675/agents-skills"


def frontmatter_description(path):
    """Pull the one-line `description:` out of a SKILL.md or agent frontmatter block."""
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return ""
    if not text.startswith("---"):
        return ""
    fm = text.split("---", 2)[1]
    for line in fm.splitlines():
        m = re.match(r"\s*description\s*:\s*(.+)", line)
        if m:
            desc = m.group(1).strip().strip('"').strip("'")
            return (desc[:117] + "…") if len(desc) > 118 else desc
    return ""


def listing(sub):
    base = os.path.join(PLUGIN, sub)
    return sorted(os.listdir(base)) if os.path.isdir(base) else []


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else "unreleased"
    manifest = json.load(open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json")))

    skills = [d for d in listing("skills")
              if os.path.isfile(os.path.join(PLUGIN, "skills", d, "SKILL.md"))]
    agents = [f[:-3] for f in listing("agents") if f.endswith(".md")]
    commands = [f[:-3] for f in listing("commands") if f.endswith(".md")]

    out = []
    out.append(f"**{manifest['name']} v{version}** with {len(skills)} skills, "
               f"{len(agents)} agents, and {len(commands)} slash commands.")
    out.append("")
    out.append("## Install")
    out.append("")
    out.append("Claude Code:")
    out.append("")
    out.append("```")
    out.append(f"/plugin marketplace add {REPO}")
    out.append(f"/plugin install {manifest['name']}@agents-skills")
    out.append("```")
    out.append("")
    out.append("Cursor: install `agents-skills` from the Cursor plugin marketplace, or point "
               f"Cursor at this repository ({REPO}), which carries its own "
               "`.cursor-plugin/marketplace.json`.")
    out.append("")
    out.append("Codex (CLI, IDE extension, and the ChatGPT desktop app):")
    out.append("")
    out.append("```")
    out.append(f"codex plugin marketplace add {REPO}")
    out.append(f"codex plugin add {manifest['name']}@agents-skills")
    out.append("```")
    out.append("")
    out.append("## Downloads")
    out.append("")
    out.append("- `agents-skills-plugin.zip` is the Claude Code plugin (manifest, skills, agents, commands).")
    out.append("- `agents-skills-cursor-plugin.zip` is the Cursor plugin (same skills, with Cursor's "
               "agent and command formats).")
    out.append("- `agents-skills-codex-plugin.zip` is the Codex/ChatGPT plugin (same skills; Codex "
               "plugins carry no agents or commands). ChatGPT workspace admins can upload it in the "
               "admin console.")
    out.append("- `<skill>.zip` is one zip per skill, for Claude Desktop (Settings, then Capabilities, "
               "then Skills) and ChatGPT (Skills, then Create, then Upload from your computer).")
    out.append("")

    out.append(f"## Skills ({len(skills)})")
    out.append("")
    out.append("| Skill | What it does |")
    out.append("|---|---|")
    for s in skills:
        out.append(f"| `{s}` | {frontmatter_description(os.path.join(PLUGIN, 'skills', s, 'SKILL.md'))} |")
    out.append("")

    out.append(f"## Agents ({len(agents)})")
    out.append("")
    out.append("| Agent | What it does |")
    out.append("|---|---|")
    for a in agents:
        out.append(f"| `{a}` | {frontmatter_description(os.path.join(PLUGIN, 'agents', a + '.md'))} |")
    out.append("")

    out.append(f"## Slash commands ({len(commands)})")
    out.append("")
    out.append(", ".join(f"`/{c}`" for c in commands))
    out.append("")

    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
