---
name: figma
description: "Connect to Figma from your AI tool — read design context (layout, typography, colors), fetch variables/tokens, capture visual references, generate code from frames, and optionally map Figma components to code with Code Connect. Use whenever a task involves a Figma file, design tokens, a design-to-code translation, or the Figma MCP. This repo's figma-specs skill and /figma-init-spec / /figma-refresh-spec commands build on it (Figma MCP read tools required; Code Connect optional)."
---

# figma (pointer skill)

Pointer skill — the implementation is **not** stored here. The `name` above is the stable local contract; the figma capabilities live upstream in Figma's official Claude plugin (and its Dev Mode MCP server), installed from source.

- **Canonical source:** https://claude.com/plugins/figma
- **Figma MCP setup:** https://help.figma.com/hc/en-us/articles/39888612464151-Claude-Code-and-Figma-Set-up-the-MCP-server
- **MCP tool reference:** https://developers.figma.com/docs/figma-mcp-server/tools-and-prompts/
- **What it provides:** the Figma Dev Mode MCP (`get_variable_defs`, `get_code`, `get_image`, and `get_code_connect_map` when Code Connect is set up) plus skills such as `/implement-design`, `/create-design-system-rules`, and `/code-connect-components`.
- **Used by:** this repo's `figma-specs` skill and the `/figma-init-spec` / `/figma-refresh-spec` commands. They need the Figma MCP read tools; Code Connect is an optional accelerator, never required (the design→code map is repo-owned).

## Installing this skill / the Figma MCP

- **Claude Code:** `/plugin install figma@claude-plugins-official`, then run `/plugin`, open the figma server, and authenticate to your Figma account.
- **Cursor / GitHub Copilot:** add the Figma Dev Mode MCP server per Figma's setup docs above; its tools surface as `mcp__figma__*` (the prefix depends on your MCP config).

**Server key matters.** The bundled `figma-*` commands and the `design-mapper` agent pre-approve `mcp__figma__*`, which assumes the Figma Dev Mode MCP is registered under the server key **`figma`**. The plugin route (`figma@claude-plugins-official`) exposes the tools under `mcp__plugin_figma_figma__*` instead — in that case allowlist that prefix (and re-key the agent's `tools`). Register under `figma` for the bundled grants to work as-is.

Do not copy the upstream body into this file; that would freeze the version and defeat the pointer.
