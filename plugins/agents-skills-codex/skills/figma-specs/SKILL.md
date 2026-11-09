---
name: figma-specs
description: "Tame design drift with the Figma MCP — snapshot a Figma file into living design specs anchored to STABLE identity (node IDs and published component/style/variable keys) rather than page/frame names or position, so when designers reorganize the file the links still resolve. Each component is mapped to its code by a repo-owned design→code map (discovered by name-matching the codebase and confirmed once; Code Connect is an optional accelerator, never required). Refresh re-reads Figma, diffs against the snapshot by stable id, and emits a drift report that separates pure reorganization (no code change) from real token/size/state changes (a precise re-touch list pointing at the mapped code) — so tiny differences get caught and fixed once instead of accumulating. Use when designs or the Figma file organization keep changing and the code keeps needing re-touches, to establish or refresh the design spec set, or when asked to track Figma changes, detect design drift, or sync design to code. Domains are discovered from the file; git versions the specs."
---

# Figma Specs: track design drift without re-touching everything

The pain: designs change, and the Figma file's *organization* changes too — pages, sections, and frames get moved and renamed. Every move introduces tiny differences (a spacing tweak, a color shift, a renamed layer), they accumulate, and the team re-touches code constantly, often for changes that aren't really changes. This skill fixes that by tracking the design the way the design *actually* identifies itself, not by where it currently sits — and it does so **without depending on any paid Figma feature**.

## The key idea: anchor on stable identity, never on location

Figma **node IDs** and published **component / style / variable keys** are stable across moves, renames, and reorganization, and they come back from an ordinary Figma read. A frame dragged to another page keeps its node ID; a published component keeps its key wherever it lives. So **key every spec to those ids**, never to a page/section/frame name or a position — those are exactly what designers move. When something moves, its id is unchanged and the link holds; the only thing that changed is a human-readable locator, which the refresh updates without touching code.

## The design→code map is repo-owned (Code Connect optional)

Drift is only actionable if you know *which code* a changed component maps to. **Do not depend on Figma Code Connect for this** — it needs paid Dev Mode and a publishing step that may not be available or allowed. Instead the mapping lives in the spec itself and is built locally:

1. **Discover by name.** Dispatch the cheap `scout` agent to grep the codebase for the component/token whose name matches the Figma component or variable (e.g. Figma `Button/Primary` → `src/ui/Button.tsx`). Record the candidate `file:line` and a confidence.
2. **Confirm once.** For low-confidence or ambiguous matches, ask the operator (an emoji-answerable comment or interactive question, as the recon skills do) and record the answer. A confirmed mapping is permanent until the code moves.
3. **Optional accelerator:** if Code Connect *happens* to be set up, `get_code_connect_map` can seed/verify the mapping for free — use it when present, never require it.

The mapping is stored in each spec's frontmatter (`code:` + `code_source: discovered | operator | code-connect`) and in the index, so it is git-versioned and owned by you, not by a Figma plan.

## Figma MCP tools used

Read via the Figma MCP. **Register the Figma Dev Mode MCP under the server key `figma`** so these `mcp__figma__*` tools — and the `design-mapper` agent's tool grants — resolve. (The `figma@claude-plugins-official` plugin instead exposes them under `mcp__plugin_figma_figma__*`; if you use the plugin, allowlist that prefix in `.claude/settings.json` and re-key the `design-mapper` agent's `tools`.) All but the last tool work without Code Connect:

- **`get_variable_defs`** — the variables/styles in a selection (color, spacing, typography). These tokens are where the "tiny differences" live; diffing them is the core drift signal.
- **`get_code`** — the design's generated implementation, as a reference for what changed (not as the diff target).
- **`get_image`** — a screenshot for visual-fidelity confirmation when a property diff is ambiguous.
- **`get_code_connect_map`** — *optional*: node id → Code Connect component, only if Code Connect is configured. Skip silently if not.

If even variable reads aren't available (no Dev Mode at all), degrade to operator-exported tokens/screenshots and mark confidence low.

## The design spec set

Git-versioned, under `design-specs/`, keyed by stable id (git is the history — no version in the name):

- `design-specs/_index.md` — registry: stable id ⇄ human name ⇄ kind (token/component/screen) ⇄ mapped code path ⇄ last-synced.
- `tokens.spec.md` — variables/styles by **key**: name, value, and the code token it maps to.
- `component/<componentKey>-<slug>.spec.md` — per published component: its key, the mapped code `file:line`, the tokens/props/states it uses, and its current human locator (informational).
- `screen/<nodeId>-<slug>.spec.md` — per screen/flow: its node id, the components it composes (by key), and the locator.

Frontmatter carries `figma_id` / `figma_key`, `kind`, `code` + `code_source`, `last_synced`, and `locator` (the movable human path — informational). The id/key is canonical and never changes; the locator is allowed to drift.

## Init (`/figma-init-spec`)

Pull the design system via the Figma MCP and write the spec set anchored to ids/keys. Discover domains (component groups, screen flows) from the file. For each component, build the design→code map with `scout` (name discovery) + operator confirmation; seed from Code Connect only if it's already there. Report how many components are mapped vs unmapped.

## Refresh and the drift report (`/figma-refresh-spec`)

Re-read Figma, diff against the snapshot **by stable id**, and classify each entry:

| Drift | What it means | Action |
|---|---|---|
| **Moved / reorganized** | same id/key, different page/section/frame | update the `locator` only — **no code change**. This is the churn the team keeps wrongly re-touching; report it as "reorg, no-op". |
| **Renamed** | same id, new name | update the label; no code change. |
| **Changed** | a token/dimension/spacing/state value differs | record the exact **before → after** delta and the mapped code path → a line on the **re-touch list**. |
| **Added** | a new id/key | spec it; run `scout` to propose its code mapping. |
| **Removed** | an id/key is gone | mark the spec deprecated; flag the now-dead code. |
| **Code moved** | mapped `file:line` no longer matches | re-run `scout` to relocate it; update `code:`. |

The report is split into two lists: **"reorganization only — ignore"** and **"real changes — re-touch"**, the latter with each exact delta and the code file it maps to (or "unmapped — needs a code owner" when no mapping exists yet). That is the whole point: stop re-touching on moves, and act once on each genuine change instead of letting tiny diffs pile up.

## Anti-patterns

- **Keying a spec to a page/frame name or position.** It breaks the moment a designer moves it — the exact failure this skill exists to prevent. Key on the node id / component key.
- **Depending on Code Connect.** It's a paid, optional accelerator. The repo-owned map (scout + confirm) is the source of truth.
- **Re-touching code for a pure move.** Same id, same values, new location = no visual change = no code change. The report flags these so you don't.
- **Letting small token drifts accumulate.** The refresh surfaces every delta with its code target; fix each once, when it appears.
- **Trusting `get_code` output as the diff.** Diff the **variables/properties** (`get_variable_defs`) by id, not regenerated code, which varies run to run.

## Token discipline

Working output in caveman (load the `caveman` skill); ids, keys, token values, and before→after deltas stay byte-exact (they are the drift evidence). Durable prose written into the specs goes through the `humanizer` skill.
