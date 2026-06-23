# Contributing

Thanks for improving this toolbox. It is a shareable set of **skills, slash commands, and agents** for Claude Code, Cursor, and GitHub Copilot. A few rules keep it clean and consistent.

## The one hard rule: no private data

This repo is public and is meant to drop into anyone's project. Never commit:

- Names, emails, employers, internal URLs, ticket IDs, secrets, or private file paths.
- Anything that only makes sense inside one company or codebase.

Keep examples generic and invented (`acme/widgets`, `PROJ-123`, "Settings > Billing > Invoice row"). Phrase learnings so they apply anywhere. Full convention: [`CLAUDE.md`](CLAUDE.md).

## Repo layout and the sync rule

Canonical sources live under `.claude/`:

- Skills: `.claude/skills/<name>/SKILL.md`
- Commands: `.claude/commands/<name>.md`
- Agents: `.claude/agents/<name>.md`

Commands and agents are **generated** into the Cursor and Copilot homes (`.cursor/`, `.github/prompts/`, `.github/agents/`). **Never hand-edit those mirrors.** After editing a command or agent:

```
make sync     # regenerate the Cursor + Copilot mirrors
make check    # fails if anything drifted — run this in CI
```

Skills are read directly from `.claude/skills/` by all three tools, so they have no mirror.

## Adding things

- **A skill** — `SKILL.md` with YAML frontmatter (`name`, `description`). The `name` is a public API; renaming it breaks consumers, so keep it stable. Make the `description` action-oriented; it is what each tool uses to decide when to trigger. A **pointer skill** records a name and an upstream link only — never inline upstream content. Ship triggering evals at `<skill>/evals/triggering.json` (8–10 should-trigger queries plus 8–10 should-not-trigger near-misses, per the skill-creator method).
- **A command** — add it to `.claude/commands/`, then run `make sync`.
- **An agent** — add it to `.claude/agents/`, then run `make sync`. Keep it thin: point at the relevant skill and pick the right model tier (see [`MODEL-DEFAULTS.md`](MODEL-DEFAULTS.md)).

## House style

- **Token discipline.** Orchestration artifacts operate in **caveman** mode (terse working output) and write durable, human-read prose — issue and ticket bodies, PR descriptions — through **humanizer**. Machine-precise content (labels, JQL, `gh` and MCP commands, `file:line`, code blocks, output contracts) stays byte-exact.
- **Models** are tiered: the cheapest capable model per task, premium operator-gated. See [`MODEL-DEFAULTS.md`](MODEL-DEFAULTS.md).
- **Docs** are tool-neutral with sentence-case headings; run README and doc prose through humanizer so it does not read as AI-generated.

## Before you open a PR

- [ ] No private, secret, or prior-project data (grep your diff).
- [ ] `make check` passes (mirrors in sync).
- [ ] New skills have `evals/triggering.json`, and every frontmatter parses.
- [ ] Branch off `main`; describe what changed and why.

Security issues: see [`SECURITY.md`](SECURITY.md) — report privately, never in a public issue.
