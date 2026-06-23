---
name: humanizer
description: "Remove signs of AI-generated writing from text. Use when editing or reviewing text to make it sound more natural and human-written. Based on Wikipedia's comprehensive 'Signs of AI writing' guide. Detects and fixes patterns including: inflated symbolism, promotional language, superficial -ing analyses, vague attributions, em dash overuse, rule of three, AI vocabulary words, passive voice, negative parallelisms, and filler phrases."
---

# humanizer (pointer skill)

Pointer skill — the implementation is **not** stored here. The `name` above is the stable local contract; the body lives upstream and is fetched/installed from source so consumers always get the latest version.

- **Canonical source:** https://github.com/blader/humanizer/blob/main/SKILL.md
- **Raw SKILL.md:** https://raw.githubusercontent.com/blader/humanizer/main/SKILL.md
- **What it does:** Identifies and rewrites statistical patterns common to LLM output, replacing them with natural alternatives while preserving meaning and the writer's voice.
- **License:** MIT (upstream). Upstream declares `allowed-tools` (Read, Write, Edit, Grep, Glob, AskUserQuestion) and compatibility with claude-code / opencode.

## Installing this skill

Recommended: git clone into your skills directory (gets `SKILL.md` plus bundled assets and stays updatable via `git pull`).

- **Claude Code:** `git clone https://github.com/blader/humanizer.git ~/.claude/skills/humanizer` (Cursor & Copilot also read `~/.claude/skills/`).
- **Project scope / other tools:** clone into `.cursor/skills/humanizer`, `.github/skills/humanizer`, or `.claude/skills/humanizer`. OpenCode: `~/.config/opencode/skills/humanizer`.

Do not copy the upstream body into this file; that would freeze the version and defeat the pointer.
