# Contributing

Thanks for improving this toolbox. It is a shareable set of **skills, slash commands, and agents** for Claude Code, Cursor, GitHub Copilot, Kiro, OpenCode, and OpenAI Codex (whose skills also run in ChatGPT). A few rules keep it clean and consistent.

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

Commands and agents are **generated** into the Cursor, Copilot, Kiro, OpenCode, and Codex homes (`.cursor/`, `.github/prompts/`, `.github/agents/`, `.kiro/agents/`, `.opencode/agents/`, `.codex/agents/`, `.codex/prompts/`). **Never hand-edit those mirrors.** After editing a command or agent:

```
make sync     # regenerate every mirror and every plugin payload
make check    # fails if anything drifted — run this in CI
```

Skills are read directly from `.claude/skills/` by Claude Code, Cursor, and Copilot, so they need no mirror. Kiro, OpenCode, and Codex read the same Agent Skills format but from their own dirs, so `.kiro/skills`, `.opencode/skills`, and `.agents/skills` are symlinks to `.claude/skills` — `make sync-skills` creates them; `make check-skills` verifies. Still one source of truth.

Git hook templates live under `hooks/` (plain POSIX `sh` + CI workflow templates). They are shareable, not wired to this repo, and have no mirror — keep them dependency-free and generic, with every external tool optional (skip-if-absent). See [`hooks/README.md`](hooks/README.md).

`plugins/agents-skills/` (Claude Code), `plugins/agents-skills-cursor/` (Cursor), and `plugins/agents-skills-codex/` (Codex and ChatGPT) are the **published plugin payloads — generated, never hand-edited** (the manifests excepted). `make build-plugin` rebuilds all three. They share the same skills. The Claude and Cursor payloads take their agents and commands from that tool's mirror (`.claude/` or `.cursor/`); a Codex plugin cannot carry either, so its payload is skills only, because the frontmatter differs (real copies, not symlinks: Claude Code installs the plugin directory on its own, so a link escaping it would dangle); `make check-plugin` fails on drift. The `.claude-plugin/marketplace.json`, `.cursor-plugin/marketplace.json`, and `.agents/plugins/marketplace.json` files make this repo its own plugin marketplace in all three ecosystems. Releases are cut by `.github/workflows/release-plugin.yml` — CalVer `YYYY.M.D.N`, tagged `v<version>`, attaching the three plugin zips plus one zip per skill. Version numbers are stamped by the workflow; don't bump them by hand.

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
