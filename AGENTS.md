# AGENTS.md

Shared instructions for AI coding tools (Cursor, GitHub Copilot, and any tool honoring `AGENTS.md`). Claude Code uses `CLAUDE.md`, which carries the same guidance — keep the two in sync; this file is the tool-neutral mirror.

## What this repository is

A **public, shareable collection of AI toolchains** — Skills and Agents — meant to be consumed by others across multiple AI coding tools (Claude Code, GitHub Copilot, Cursor). It is a content/config repo: no application code, no build step, no test runner. "Correctness" means each artifact is valid for its target tool and works when dropped into a consumer's environment.

Because it is public and reusable, every artifact must be **clean of personal and prior-project data**: no employer names, internal URLs, ticket IDs, secrets, private file paths, or learnings that only make sense inside one codebase. Keep learnings *isolated* — phrased generically so they apply anywhere.

**Primary goal: extreme token savings at the highest practical accuracy.** Every authored skill operates in **caveman** mode, and model spend is **tiered** (cheapest capable model per task, mechanical work offloaded to a cheap-tier subagent, premium reserved for operator-gated hard reasoning) — see [`MODEL-DEFAULTS.md`](MODEL-DEFAULTS.md).

## Repository layout

- `.claude/skills/<skill-name>/SKILL.md` — one directory per skill; YAML frontmatter (`name`, `description`) + body. Supporting files (`references/`, scripts) alongside.
- `.claude/agents/<agent-name>.md` — one file per agent; frontmatter (`name`, `description`, `tools`, optional `model`) + system prompt. Ships 14 tiered worker agents (`scout` cheap; `builder`/`reviewer`/`implementer`/`pr-rescuer`/`diagnostician`/`verifier`/`spelunker`/`design-mapper` workhorse — these the commands dispatch — plus the `pr-comments`/`pr-checks`/`pr-cleanup` single-lane PR watchers and the `ci-speed-hunter`/`ci-flake-hunter` continuous CI lanes, all run via `/loop`). Mirrored to Cursor (`.cursor/agents/`) and Copilot (`.github/agents/*.agent.md`) via `make sync-agents`; never hand-edit the mirrors.
- `.claude/settings.json` — Claude Code config (`model: opus`, `includeCoAuthoredBy: false`).
- `CLAUDE.md` — Claude Code's copy of this guidance.
- `README.md` — human entry point.

## Two kinds of skill

1. **Self-contained skills** — full instructions live here.
2. **Pointer skills** — a thin `SKILL.md` pointing to an upstream project's skill so the *latest* version is always used. The **name defined here is the contract** — keep it stable even when the upstream target moves. Don't inline upstream content.

Treat a skill/agent `name` as a public API: renaming breaks consumers who invoke it by name.

## Cross-tool consumability

Author content once (canonically under `.claude/`) and expose it to the other tools rather than forking copies:

- **Claude Code** — reads `CLAUDE.md`, `.claude/skills/`, `.claude/agents/`.
- **GitHub Copilot** — reads `.github/copilot-instructions.md` (points here) and this `AGENTS.md`.
- **Cursor** — reads this `AGENTS.md` (and `.cursor/rules/*.mdc` if you add project rules).

**Slash commands** don't share a home or format, so the canonical `.claude/commands/*.md` are mirrored per tool by `scripts/sync-commands.py` (`make sync-commands`; `make check-commands` for CI). Never hand-edit the mirrors — regenerate them. Filename = command name across all three:

- **Claude Code** — `.claude/commands/<name>.md` (frontmatter `description`/`argument-hint`/`allowed-tools`; `$ARGUMENTS`).
- **Cursor** — `.cursor/commands/<name>.md` (plain markdown, no frontmatter; args = text after the command).
- **GitHub Copilot (VS Code)** — `.github/prompts/<name>.prompt.md` (frontmatter `description`/`argument-hint`/`agent`; `${input:args}`). Copilot CLI does not support custom commands yet.

## Model selection policy

Model spend is **tiered** and Anthropic-first for reasoning — full task→tier matrix + per-platform model IDs in [`MODEL-DEFAULTS.md`](MODEL-DEFAULTS.md):

- **Cheap / mechanical** (`ls`/`grep`/`git status`, lookups, listing, fixed-command runs) — Haiku 4.5 or each platform's cheapest native model (Copilot Raptor Mini, Cursor free Auto), always **offloaded to a cheap-tier subagent** returning a distilled caveman answer — never the main session.
- **Workhorse (default)** — orchestration loop, verification, dev work, filing/grooming/recon: Sonnet 4.6.
- **Premium (operator-gated)** — hard cross-cutting reasoning only, never self-escalated: Opus 4.8.

Substitutes are acceptable only if they match context window (≈200K+, or 1M-class where needed) and reasoning tier — except the mechanical tier, which uses each platform's cheapest native model. State the substitution and why in the artifact.

## Conventions

- Write artifact bodies in plain, tool-neutral language; don't assume a specific local environment.
- Keep frontmatter `description` action-oriented and specific — tools use it to decide when to trigger.
- Validate by structure (valid frontmatter, required keys, unique name); there is no test suite.
- **Token discipline for the orchestration family** (`dispatch`, `rescue`, `gh-issue-*`/`jira-issue-*` commands and their skills): operate in **caveman** mode to conserve tokens across the high-volume loop, but write the durable prose a human reads — issue/ticket bodies and PR descriptions — through **humanizer** so it doesn't read AI-generated. Under both, machine-precise content (labels/fields, JQL, `gh`/MCP commands, lock markers, the `RECON OK`/`RECON-ERROR` contract, `file:line` refs, code blocks, acceptance-criteria checklists) stays byte-exact.
