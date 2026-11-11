---
name: doc-coauthoring
description: "Guide users through a structured workflow for co-authoring documentation. Use when user wants to write documentation, proposals, technical specs, decision docs, or similar structured content. This workflow helps users efficiently transfer context, refine content through iteration, and verify the doc works for readers. Trigger when user mentions writing docs, creating proposals, drafting specs, or similar documentation tasks."
---

# doc-coauthoring (pointer skill)

Pointer skill — the implementation is **not** stored here. The `name` above is the stable local contract; the body lives upstream and is fetched/installed from source so consumers always get the latest version.

- **Canonical source:** https://github.com/anthropics/skills/blob/main/skills/doc-coauthoring/SKILL.md
- **Raw SKILL.md:** https://raw.githubusercontent.com/anthropics/skills/main/skills/doc-coauthoring/SKILL.md
- **What it does:** Three-stage collaborative document creation — gather context, refine section-by-section, test comprehension with a fresh-reader pass before publication.
- **License:** see the anthropics/skills repo LICENSE.

## Installing this skill

- **Claude Code (recommended):** `/plugin marketplace add anthropics/skills`, then `/plugin install example-skills@anthropic-agent-skills` — this skill ships in the **example-skills** plugin.
- **Claude.ai (paid plans):** already available, no install.
- **Claude API:** upload/enable via the Skills API.
- **Cursor / GitHub Copilot:** copy `skills/doc-coauthoring/` from anthropics/skills into your skills dir (`.cursor/skills/`, `.github/skills/`, or the shared `.claude/skills/`).

Do not copy the upstream body into this file; that would freeze the version and defeat the pointer.
