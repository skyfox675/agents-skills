---
description: "Snapshot a Figma file into living design specs anchored to stable identity (node IDs, component/style keys) with a repo-owned design→code map, so reorganization doesn't break the links. Code Connect optional. For taming design drift. Optional scope arg. Example — /figma-init-spec, or /figma-init-spec \"Checkout flow\""
argument-hint: "[scope: page | flow | component set] [model:sonnet|opus]"
allowed-tools: mcp__figma__get_variable_defs, mcp__figma__get_code_connect_map, mcp__figma__get_code, mcp__figma__get_image, Read, Write, Edit, Glob, Grep, Bash(git rev-parse:*), Bash(git log:*)
---

# /figma-init-spec — snapshot the design system into living specs

> Operate in caveman mode (load the `caveman` skill). Keep ids, keys, token values, and mapped code paths byte-exact; spec prose through humanizer.

Arguments: `$ARGUMENTS` — an optional scope (a page, screen flow, or component set; none = the whole file). A `model:` token pins the tier (default `sonnet`).

The **figma-specs** skill is the protocol — stable-identity anchoring, the spec layout, the Figma MCP tools, and the repo-owned design→code map (Code Connect optional). Consult it first. Figma reads go through the Figma MCP — register the Dev Mode MCP under server key `figma` so the pre-approved `mcp__figma__*` tools resolve (plugin installs use `mcp__plugin_figma_figma__*`; allowlist that prefix if so). If it isn't connected, say so and ask the operator to export the variables/screens instead.

## Steps

1. **Discover the domains** (component groups, screen flows) from the file via the Figma MCP — not a fixed list.
2. **Fan out one `design-mapper` agent per domain** (parallel, per dispatching-subagents). Each pulls `get_variable_defs` (and `get_code_connect_map` only if Code Connect is already set up) and writes its specs anchored to the node id / component key. To map each component to code, it dispatches `scout` to grep the codebase for the matching component and records the `file:line` + confidence; ambiguous matches are confirmed with the operator.
3. **Write `design-specs/_index.md`**, set each spec's `last_synced` to the current Figma version / commit, and report: the domain map, plus how many components are mapped to code vs unmapped. Unmapped components make later re-touch lists imprecise — `scout` proposes a mapping for each and the operator confirms once.

Run spec prose through the `humanizer` skill; ids/keys/tokens stay byte-exact.
