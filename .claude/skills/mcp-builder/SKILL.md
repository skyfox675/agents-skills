---
name: mcp-builder
description: "Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate external APIs or services, whether in Python (FastMCP) or Node/TypeScript (MCP SDK)."
---

# mcp-builder (pointer skill)

Pointer skill — the implementation is **not** stored here. The `name` above is the stable local contract; the body lives upstream and is fetched/installed from source so consumers always get the latest version.

- **Canonical source:** https://github.com/anthropics/skills/blob/main/skills/mcp-builder/SKILL.md
- **Raw SKILL.md:** https://raw.githubusercontent.com/anthropics/skills/main/skills/mcp-builder/SKILL.md
- **What it does:** A structured four-phase process for building MCP servers that integrate external APIs/services, in Python (FastMCP) or Node/TypeScript (MCP SDK).
- **License:** see the anthropics/skills repo LICENSE.

## Installing this skill

- **Claude Code (recommended):** `/plugin marketplace add anthropics/skills`, then `/plugin install example-skills@anthropic-agent-skills` — this skill ships in the **example-skills** plugin.
- **Claude.ai (paid plans):** already available, no install.
- **Claude API:** upload/enable via the Skills API.
- **Cursor / GitHub Copilot:** copy `skills/mcp-builder/` from anthropics/skills into your skills dir (`.cursor/skills/`, `.github/skills/`, or the shared `.claude/skills/`).

Do not copy the upstream body into this file; that would freeze the version and defeat the pointer.
