# Model defaults

This repo optimizes for **extreme token savings at the highest practical accuracy**. Two levers do the work: every authored skill operates in **caveman** mode (terse working output — see each skill's *Token discipline* section), and model spend is **tiered** — the cheapest capable model for each task, premium reserved only for where a mistake cascades.

Models change often. Treat the **task → tier** mapping as stable; treat the **tier → model** table as defaults to update per project and platform.

## Task → tier

| Task | Tier | Why |
|---|---|---|
| Local/mechanical ops — `ls`/`grep`/`git status`, file lookups, listing, log scans, fixed-command-and-parse | **cheap** (via subagent) | a wrong answer is obvious at a glance; never spend a reasoning model on plumbing |
| Dev implementation, issue filing/grooming, technical & spelunking recon, the orchestration loop, verification | **workhorse** | the bulk of real work; a Sonnet-class model handles it |
| Hard/cross-cutting reasoning the operator explicitly escalates (gnarly recon, a stuck verify, architecture calls) | **premium** (operator-gated) | only when accuracy genuinely needs it; never self-escalated (see the control-field skills) |

Default the loop **and** verification to **workhorse**; escalate to premium only on an explicit operator instruction or `agent-model:` label.

## Tier → model (defaults — update as availability shifts)

| Tier | Claude Code | GitHub Copilot | Cursor |
|---|---|---|---|
| premium *(gated)* | Opus 4.8 | Claude Opus 4.8 / GPT-5.5 | Premium mode (Opus 4.8) |
| workhorse *(default)* | Sonnet 4.6 | Claude Sonnet 4.6 | Sonnet 4.6 / Composer 2.5 |
| cheap / mechanical | Haiku 4.5 | Raptor Mini / GPT-5.4-mini / Haiku 4.5 | Auto *(free)* / Gemini 3.5 Flash / Grok Build 0.1 |

Reasoning tiers are **Anthropic-first** for consistent behaviour across tools; the **mechanical tier uses each platform's cheapest native model** — Copilot's Raptor Mini, Cursor's free Auto — for maximum savings. There is deliberately **no cheap-tier label**: the cheap model is a tool-task choice the orchestrator makes for mechanical sub-steps, never a knob to force code-writing onto a model that ships subtle bugs (see `gh-issue-labels` / `jira-issue-fields`).

## Offload mechanical work to a cheap-tier subagent

The orchestrator's context is the expensive one. Don't run `ls`, `grep`, `git status`, file lookups, log triage, or fixed-command-and-parse steps in the premium/workhorse session — **dispatch them to a cheap-tier subagent that returns only the distilled answer** (caveman-compressed), so the main thread spends a fraction of the tokens. The caveman plugin's `caveman:cavecrew-investigator` agent (read-only locator, caveman output) is one ready implementation; otherwise dispatch a sub-agent pinned to the cheap tier per the `dispatching-subagents` skill. Reserve the workhorse/premium model for judgement, not plumbing.

## Pinning a model per tool

- **Claude Code** — `model:` on the Agent/Task dispatch (subagents), the `agent-model:*` issue label, or the `model:` command token. Default = workhorse; omit to inherit it.
- **GitHub Copilot** — `model:` in a prompt file's frontmatter. Set it only where a fixed model genuinely helps; otherwise leave it out and let the user's model picker (or the cheap tier for mechanical prompts) choose.
- **Cursor** — no per-command model field; the user's model selector (or **Auto**) governs. State the intended tier in the command body so the user can match it.
