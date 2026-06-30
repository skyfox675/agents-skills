# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A **public, shareable collection of AI toolchains** — Skills and Agents — meant to be consumed by others across multiple AI coding tools (Claude Code, GitHub Copilot, Cursor). It is a content/config repo: there is no application code, no build step, and no test runner. "Correctness" here means each artifact is valid for its target tool and works when dropped into a consumer's environment.

Because it is public and reusable, every artifact must be **clean of personal and prior-project data**. No employer names, internal URLs, ticket IDs, secrets, file paths from private repos, or learnings that only make sense inside one codebase. Keep learnings *isolated* — phrased generically so they apply anywhere.

**Primary goal: extreme token savings at the highest practical accuracy.** Every authored skill operates in **caveman** mode for terse working output, and model spend is **tiered** — the cheapest capable model per task, with mechanical work offloaded to a cheap-tier subagent and premium reserved for operator-gated hard reasoning. See [`MODEL-DEFAULTS.md`](MODEL-DEFAULTS.md).

## Repository layout

Skills and Agents are the two primary artifact types. The canonical homes are the directories Claude Code auto-discovers:

- `.claude/skills/<skill-name>/SKILL.md` — one directory per skill; `SKILL.md` holds YAML frontmatter (`name`, `description`) + the skill body. Supporting files (`references/`, scripts) live alongside it.
- `.claude/agents/<agent-name>.md` — one file per agent; frontmatter (`name`, `description`, `tools`, optional `model`) + system prompt. Ships 14 tiered worker agents (`scout` on the cheap tier; `builder`, `reviewer`, `implementer`, `pr-rescuer`, `diagnostician`, `verifier`, `spelunker`, `design-mapper` on workhorse — these the commands dispatch — plus the `pr-comments`, `pr-checks`, `pr-cleanup` single-lane PR watchers and the `ci-speed-hunter`, `ci-flake-hunter` continuous CI lanes, all run via `/loop`). Canonical agents live here; `make sync-agents` generates the Cursor (`.cursor/agents/`, `model`/`readonly` schema) and Copilot (`.github/agents/*.agent.md`) copies — never hand-edit those. Keep agents thin and point at the relevant skill for the protocol.
- `.claude/settings.json` — repo-level Claude Code config. Currently pins `model: opus` and `includeCoAuthoredBy: false` (commits authored without the Claude co-author trailer).

When adding the first artifacts, create these directories. Top-level `README.md` is the human entry point.

## Two kinds of skill

1. **Self-contained skills** — the full instructions live here.
2. **Pointer skills** — a thin `SKILL.md` that points to an upstream project's skill (e.g. a plugin or another repo) so the *latest* version is always used. For these, **the name defined here is the contract** — keep it stable even when the upstream target moves. Document the upstream source and what the local name maps to inside the body; don't inline the upstream content (that defeats the point of pointing).

When asked to add or rename a skill, treat the `name` as a public API: renaming breaks consumers who invoke it by name.

## Cross-tool consumability

The same artifact often needs to be reachable from three tools. Keep the content authored once (canonically under `.claude/`) and expose it to the others rather than forking copies:

- **Claude Code** — reads `CLAUDE.md`, `.claude/skills/`, `.claude/agents/` natively.
- **GitHub Copilot** — reads `.github/copilot-instructions.md` (and `AGENTS.md`).
- **Cursor** — reads `AGENTS.md` (and `.cursor/rules/*.mdc` if you add project rules).

Prefer a shared `AGENTS.md` (Copilot + Cursor both honor it) that mirrors or references this file, over maintaining divergent copies. If a new artifact only makes sense for one tool, say so in its body.

**Slash commands don't share a home or format** — each tool needs its own copy, so the canonical `.claude/commands/*.md` are mirrored:

- **Claude Code** — `.claude/commands/<name>.md` (YAML frontmatter: `description`, `argument-hint`, `allowed-tools`; body uses `$ARGUMENTS`).
- **Cursor** — `.cursor/commands/<name>.md` (plain markdown, **no frontmatter**; filename is the command; args = text typed after the command).
- **GitHub Copilot (VS Code)** — `.github/prompts/<name>.prompt.md` (frontmatter `description`/`argument-hint`/`agent`; body uses `${input:args}`). Copilot **CLI** does not support custom commands yet.

The Cursor and Copilot copies are **generated** from the Claude source — after editing any `.claude/commands/*.md`, run `make sync-commands` (or `python3 scripts/sync-commands.py`) to regenerate them; `make check-commands` exits non-zero if they've drifted (wire it into CI / a pre-commit hook). Never hand-edit the mirrors. The script also prunes mirrors whose source command was renamed or deleted.

## Model selection policy

Model spend is **tiered** and Anthropic-first for reasoning. Full task→tier matrix + per-platform model IDs: [`MODEL-DEFAULTS.md`](MODEL-DEFAULTS.md).

- **Cheap / mechanical** — `ls`/`grep`/`git status`, file lookups, listing, fixed-command runs. Haiku 4.5, or each platform's cheapest native model (Copilot Raptor Mini, Cursor's free Auto). Always **offloaded to a cheap-tier subagent** that returns a distilled, caveman-compressed answer — never run in the main session.
- **Workhorse (default)** — the orchestration loop, verification, dev work, filing/grooming/recon. Sonnet 4.6.
- **Premium (operator-gated)** — hard, cross-cutting reasoning only, never self-escalated. Opus 4.8.

Substitutes from other providers are acceptable **only if they match on both axes**: comparable context window (≈200K+, or 1M-class where the artifact needs it) and comparable reasoning tier — except the mechanical tier, which deliberately uses each platform's cheapest native model. State the substitution and why in the artifact when you make one.

## Conventions

- Write artifact bodies in plain, tool-neutral language. Avoid assuming a specific local environment.
- Keep frontmatter `description` action-oriented and specific — it is what each tool uses to decide when to trigger the skill/agent.
- Validate by structure (valid frontmatter, required keys present, name unique) since there is no test suite.
- **Token discipline for the orchestration family** (`dispatch`, `rescue`, `gh-issue-*`/`jira-issue-*` commands and their skills): operate in **caveman** mode to conserve tokens across the high-volume loop, but write the durable prose a human reads — issue/ticket bodies and PR descriptions — through **humanizer** so it doesn't read AI-generated. Under both, machine-precise content (labels/fields, JQL, `gh`/MCP commands, lock markers, the `RECON OK`/`RECON-ERROR` contract, `file:line` refs, code blocks, acceptance-criteria checklists) stays byte-exact.
