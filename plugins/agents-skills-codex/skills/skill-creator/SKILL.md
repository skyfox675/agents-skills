---
name: skill-creator
description: "Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy."
---

# skill-creator (pointer skill)

Pointer skill — the implementation is **not** stored here. The `name` above is the stable local contract; the body lives upstream and is fetched/installed from source so consumers always get the latest version.

- **Canonical source:** https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md
- **Raw SKILL.md:** https://raw.githubusercontent.com/anthropics/skills/main/skills/skill-creator/SKILL.md
- **What it does:** Guides building Claude skills iteratively — capture intent, draft, run evals against test cases, refine on feedback, optimize the triggering description, package.
- **License:** see the anthropics/skills repo LICENSE.

## Installing this skill

- **Claude Code (recommended):** `/plugin marketplace add anthropics/skills`, then `/plugin install example-skills@anthropic-agent-skills` — this skill ships in the **example-skills** plugin.
- **Claude.ai (paid plans):** already available, no install.
- **Claude API:** upload/enable via the Skills API.
- **Cursor / GitHub Copilot:** copy `skills/skill-creator/` from anthropics/skills into your skills dir (`.cursor/skills/`, `.github/skills/`, or the shared `.claude/skills/`).

Do not copy the upstream body into this file; that would freeze the version and defeat the pointer.
