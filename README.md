# agents-skills

A toolbox of skills, slash commands, and agents for AI coding assistants: Claude Code, Cursor, and GitHub Copilot.

It gives you four things:

- **Skills** — knowledge the assistant loads on its own when your task matches; set up once and forget.
- **Commands** — shortcuts you type, like `/gh-issue the login button does nothing`, that run a set workflow.
- **Agents** — the cheap, specialized workers the commands spawn (locator, implementer, reviewer, and more), already wired up.
- **MCPs** — optional connectors (Jira, AWS, a browser, Figma) that power specific commands; install only what you use.

The whole set is built to get an accurate result for as few tokens as possible: it talks in a terse "caveman" mode and sends cheap work to cheap models. The model policy lives in [`MODEL-DEFAULTS.md`](MODEL-DEFAULTS.md) and [`CLAUDE.md`](CLAUDE.md).

Do the Quickstart for your tool. The full list is under [What's included](#whats-included).

## Quickstart

1. **Get the files.** Clone this repo and open the folder in your tool. Skills, commands, and agents are already set up inside `.claude/` (and mirrored to `.cursor/` and `.github/`). To use them in your own project instead, copy your tool's folders (named below) into your project root.

   ```bash
   git clone https://github.com/skyfox675/agents-skills.git
   ```

2. **Install the helper skills.** The small pointer skills (caveman, humanizer, docx, and the rest) point to tools maintained elsewhere, so you install the current version from the source. Paste the prompt from your tool's section below and let your assistant run it.

3. **Add the MCPs you need (optional).** The Jira, AWS, browser, and Figma commands each need a matching MCP. Install only the ones for the flows you use, and register each under the server key shown — see [MCPs and external tools](#mcps-and-external-tools).

4. **Use it.** Type `/` in the chat to list the commands, or describe your task and let the skills and agents kick in.

Open your tool's section below and ignore the other two.

<details>
<summary><b>Claude Code</b></summary>

&nbsp;

Skills, commands, and agents load automatically from the `.claude/` folder, so if you opened this repo they already work. Type `/` to see the commands. To use them in your own project, copy this repo's `.claude/` folder into your project root. For the Jira / AWS / browser / Figma flows, add the matching MCP (see [MCPs and external tools](#mcps-and-external-tools)).

Install the helper skills by pasting this to Claude Code:

```text
Install these skills and put each where Claude Code looks (~/.claude/skills/ for every project, or .claude/skills/ for this one):
1. Anthropic skills: run /plugin marketplace add anthropics/skills, then /plugin install document-skills@anthropic-agent-skills and /plugin install example-skills@anthropic-agent-skills
2. caveman: run its official installer from github.com/JuliusBrussee/caveman
3. humanizer: git clone github.com/blader/humanizer into the skills folder
Then tell me what you installed.
```

Try it: `/gh-issue the export button on the reports page does nothing`.

</details>

<details>
<summary><b>Cursor</b></summary>

&nbsp;

Cursor reads skills from `.claude/skills/`, commands from `.cursor/commands/`, and agents from `.cursor/agents/` — all already in this repo. To use them in your own project, copy this repo's `.cursor/` and `.claude/skills/` folders into your project root. Type `/` in chat to see the commands. For the Jira / AWS / browser / Figma flows, add the matching MCP (see [MCPs and external tools](#mcps-and-external-tools)).

Install the helper skills by pasting this to Cursor:

```text
Install these skills into .cursor/skills/ (or ~/.cursor/skills/ for every project):
1. Anthropic skills (docx, pdf, pptx, xlsx, skill-creator, doc-coauthoring, mcp-builder): copy each skills/<name>/ folder from github.com/anthropics/skills
2. caveman: run its official installer from github.com/JuliusBrussee/caveman
3. humanizer: git clone github.com/blader/humanizer
Then tell me what you installed.
```

Try it: `/gh-issue the export button on the reports page does nothing`.

</details>

<details>
<summary><b>GitHub Copilot (VS Code)</b></summary>

&nbsp;

Copilot reads skills from `.claude/skills/`, commands (prompt files) from `.github/prompts/`, and agents from `.github/agents/` — all already in this repo. To use them in your own project, copy this repo's `.github/` and `.claude/skills/` folders into your project root. Type `/` in Copilot Chat to see the commands. For the Jira / AWS / browser / Figma flows, add the matching MCP (see [MCPs and external tools](#mcps-and-external-tools)).

Custom commands work in VS Code Copilot. The Copilot CLI does not support them yet.

Install the helper skills by pasting this to Copilot:

```text
Install these skills into .github/skills/ (or ~/.copilot/skills/ for every project):
1. Anthropic skills (docx, pdf, pptx, xlsx, skill-creator, doc-coauthoring, mcp-builder): copy each skills/<name>/ folder from github.com/anthropics/skills
2. caveman: run its official installer from github.com/JuliusBrussee/caveman
3. humanizer: git clone github.com/blader/humanizer
Then tell me what you installed.
```

Try it: `/gh-issue the export button on the reports page does nothing`.

</details>

One note on caveman: it installs by running a script (`curl ... | bash`), which runs code on your machine. That is normal, but read [`install.sh`](https://raw.githubusercontent.com/JuliusBrussee/caveman/main/install.sh) first if you want to see what it does.

## What's included

### Commands (you type these)

A common flow: groom a vague ticket, size it with recon, build it with dispatch, unstick it with rescue. Or file a ready-to-build ticket with `/gh-issue`. Every `gh-issue-*` command has a `jira-issue-*` twin, so use whichever tracker you run.

| Command (GitHub / Jira) | What it does |
|---|---|
| `/gh-issue` · `/jira-issue` | Files a fully groomed bug or feature ticket from a one-line description. It reads the code, verifies evidence, checks for duplicates, and labels it. |
| `/gh-issue-use-aws` · `/jira-issue-use-aws` | Same, plus a read-only AWS dig (logs, config, CloudTrail) so the ticket carries a cloud-traced root cause. |
| `/gh-issue-use-browser` · `/jira-issue-use-browser` | Same, plus a live browser repro on whatever browser MCP is connected (Chrome, Playwright, or Cypress): watches network, console, and DOM. |
| `/…-use-chrome` · `/…-use-playwright` · `/…-use-cypress` | Same as `use-browser`, but pinned to one engine when you want to choose (each has a `gh-issue-` and `jira-issue-` form). |
| `/gh-issue-use-aws-browser` · `/jira-issue-use-aws-browser` | Full stack: browser and AWS together, correlated, to find which layer fails when nobody knows. |
| `/…-use-aws-chrome` · `/…-use-aws-playwright` · `/…-use-aws-cypress` | Same full-stack dive, browser phase pinned to one engine. |
| `/gh-issue-groom` · `/jira-issue-groom` | Takes a vague existing ticket and asks you questions until the story is clear (90 percent or better). It leaves approved acceptance criteria untouched unless you say otherwise. |
| `/gh-issue-recon` · `/jira-issue-recon` | Reads the code and adds an implementation plan, an effort estimate, and the risks to a groomed ticket, so the team can size work before building. |
| `/spelunking-init-spec` | Deep dives an unfamiliar codebase and writes living spec docs that describe how it actually works. |
| `/spelunking-refresh-spec` | Updates those specs after the code changes. |
| `/figma-init-spec` | Snapshots a Figma file into living design specs anchored to stable IDs, so they survive reorganization. |
| `/figma-refresh-spec` | Diffs Figma against the design specs and reports drift: a re-touch list that separates real changes from pure moves. |
| `/dispatch` | Runs an N-agent loop that picks up ready tickets, builds them, and drives the PRs to merge. |
| `/rescue` | Unsticks a stuck PR or a failing environment: red CI, merge conflict, blocked review. |
| `/kill` | Emergency brake. Kills runaway agents when the machine is overloaded, then salvages their work. |

### Skills (load automatically)

These power the commands above, so you rarely call them by hand.

| Skill | What it does |
|---|---|
| `dispatching-subagents` | Turns a ready ticket into a running implementation agent and a PR. |
| `driving-prs-to-merge` | Gets an opened PR all the way to merged: CI triage, review threads, conflicts, merge queue. |
| `pr-comments` · `pr-checks` · `pr-cleanup` | Single-lane interval watchers: one drives review threads to resolved and arms auto-merge, one keeps CI green and the merge queue healthy, one tidies up after PRs close. |
| `ci-speed-hunting` · `ci-flake-hunting` | Continuous CI lanes: one mines timing to cut wall-clock latency without losing coverage, one root-causes flakes and fixes them forward — both to raise merge-queue throughput. |
| `orchestrating-slots` | The N-slot loop that keeps a fixed number of agents working the queue. |
| `gh-issue-filing` · `jira-issue-filing` | How to write a ticket an agent can build with no follow-up questions. |
| `gh-issue-locking` · `jira-issue-locking` | Claims and locks tickets so two people never double-work the same one. |
| `gh-issue-labels` · `jira-issue-fields` | The label and field control plane: priority, model tier, do-not-touch holds. |
| `grooming-issues` | Clarifies a vague ticket's intent to 90 percent before any work starts. |
| `technical-recon` | Sizes a groomed ticket: implementation approach, effort, risks. |
| `spelunking-specs` | Deep dives a codebase into living, versioned spec docs. |
| `browser-diagnosis` | Reproduces a front-end bug in whichever browser MCP is connected (Chrome, Playwright, or Cypress) and captures the evidence. |
| `figma-specs` | Tracks Figma design drift via stable IDs and a repo-owned design→code map, so a file reorganization doesn't trigger needless re-touches. |

The helper skills below point to tools maintained elsewhere. You install them in the Quickstart.

| Skill | What it does |
|---|---|
| `caveman` | Terse mode. Roughly 75 percent fewer tokens at the same accuracy. |
| `humanizer` | Strips the tell-tale signs of AI writing from prose. |
| `skill-creator` | Builds, tests, and tunes your own skills. |
| `docx` · `pdf` · `pptx` · `xlsx` | Read and create Word, PDF, PowerPoint, and Excel files. |
| `doc-coauthoring` | Co-writes docs, specs, and proposals with a structured workflow. |
| `mcp-builder` | Builds MCP servers that connect AI tools to outside services. |
| `figma` | Pointer to Figma's official plugin / Dev Mode MCP — design context, tokens, and design-to-code; powers the `figma-*` commands. |

### Agents

These are the workers the commands spawn. Each one runs on the cheapest model that fits, so heavy work stays cheap. The canonical agents live in `.claude/agents/`; `make sync-agents` generates the Cursor (`.cursor/agents/`) and Copilot (`.github/agents/`) copies, so all three tools get them.

| Agent | Tier | Backs | What it does |
|---|---|---|---|
| `scout` | cheap | every command | Read-only `file:line` locator, the mechanical-offload worker. |
| `builder` | workhorse | small dispatches | Surgical one- or two-file edits. Refuses bigger scope. |
| `reviewer` | workhorse | `/dispatch`, pre-merge | Adversarial diff review, tagged by severity. |
| `implementer` | workhorse | `/dispatch` dev slots | Builds one issue, writes tests, opens a PR. |
| `pr-rescuer` | workhorse | `/rescue` | Unsticks stuck PRs and red CI. |
| `pr-comments` | workhorse | `/loop` review lane | Drives bot + human review threads to resolved, then arms auto-merge. |
| `pr-checks` | workhorse | `/loop` CI lane | Keeps checks green and the merge queue healthy (head-green ≠ queue-green). |
| `pr-cleanup` | workhorse | `/loop` cleanup lane | Post-merge janitor: closes issues, releases locks, reclaims local disk. |
| `ci-speed-hunter` | workhorse | `/loop` CI-speed lane | Mines CI timing and cuts wall-clock latency without losing coverage. |
| `ci-flake-hunter` | workhorse | `/loop` CI-flake lane | Root-causes flaky jobs and fixes them forward; never masks. |
| `diagnostician` | workhorse | `use-aws`, `use-chrome`, recon | Read-only AWS and browser repro that returns evidence. |
| `verifier` | workhorse | dispatch, recon, spelunking | Verify-then-trust gate. Trusts no claim unchecked. |
| `spelunker` | workhorse | `/spelunking-init-spec` | Maps one domain of a codebase into specs. |
| `design-mapper` | workhorse | `/figma-init-spec` | Maps one Figma domain into drift-resistant design specs. |

## MCPs and external tools

Most commands need nothing extra. These add capabilities for specific command families — install only what you use.

| Tool / MCP | Powers | Required? | Install |
|---|---|---|---|
| GitHub `gh` CLI | the `gh-issue-*` commands, `/dispatch`, `/rescue` | yes, for the GitHub flow | install the GitHub CLI, then `gh auth login` |
| Atlassian (Jira) MCP | the `jira-issue-*` commands | yes, for the Jira flow | add Atlassian's official MCP under server key `atlassian`, then authenticate |
| AWS CLI | the `*-use-aws*` commands | optional (cloud-traced diagnosis) | install the AWS CLI and configure read-only credentials |
| A browser MCP (pick one) | the `*-use-browser` / `-chrome` / `-playwright` / `-cypress` commands | optional (front-end diagnosis) | Playwright: `claude mcp add playwright npx @playwright/mcp@latest`. Cypress: `npx cypress-mcp --project .` (server key `cypress`, needs Cypress ≥ 12 + `npx playwright install chromium`). Chrome: the claude-in-chrome extension. Chrome DevTools: `chrome-devtools-mcp`. |
| Figma MCP | the `figma-*` commands | optional (design drift) | register the Figma Dev Mode MCP under server key `figma` (per Figma's setup docs), then authenticate. `/plugin install figma@claude-plugins-official` also works but exposes `mcp__plugin_figma_figma__*` — allowlist that prefix if you use it. |

**Register each MCP under the server key shown** (`playwright`, `cypress`, `chrome-devtools`, `figma`, `atlassian`). The bundled command `allowed-tools` and agent `tools` pre-approve `mcp__<key>__*`; a different key means permission prompts on commands and missing access for agents — so match the key or allowlist your prefix in `.claude/settings.json`.

Which model each tool uses per platform is in [`MODEL-DEFAULTS.md`](MODEL-DEFAULTS.md). The helper skills (caveman, humanizer, docx, and the rest) install in the Quickstart above.

## Git hooks

[`hooks/`](hooks) holds portable, dependency-free git hooks and matching CI workflows you can drop into any repo — they are templates, not wired to this repo. Plain POSIX `sh`, no husky or Node; every external tool is optional and skips when absent.

| File | Kind | Does |
|---|---|---|
| `commit-msg` | local | Enforces Conventional Commits format on the message. |
| `pre-commit` | local | Scans staged changes for secrets with gitleaks. |
| `pre-push` | local | Lint gate: your project's own check + Claude artifact frontmatter + markdownlint + actionlint. |
| `pr-title.yml` | CI | Server-side PR-title format check; mirrors `commit-msg`. |
| `gitleaks.yml` | CI | Server-side secret scan on every push and PR. |
| `claude-code-pretooluse.sh` | harness | Optional Claude Code `PreToolUse` bridge: runs the same checks before the model's `git commit`/`git push`, and can't be `--no-verify`'d. |

Install: `sh hooks/install.sh` (points `core.hooksPath` at `hooks/`), then copy the CI templates into `.github/workflows/`. For the optional Claude Code harness layer, merge `hooks/claude-settings.hooks.json` into `.claude/settings.json`. Details and customization in [`hooks/README.md`](hooks/README.md).

## Going deeper

- [`MODEL-DEFAULTS.md`](MODEL-DEFAULTS.md) covers which model each task uses, per platform, and how to save tokens.
- [`CLAUDE.md`](CLAUDE.md) and [`AGENTS.md`](AGENTS.md) cover the conventions, the model policy, and how the three tools stay in sync.
- [`.claude/skills/`](.claude/skills) holds every skill. The pointer skills list their own install steps.
- To edit a command or agent, change it in `.claude/commands/` or `.claude/agents/`, then run `make sync` to update the Cursor and Copilot copies.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to add skills/commands/agents and the sync rule. [`SECURITY.md`](SECURITY.md) — how to report a security issue.

## License

MIT — see [LICENSE](LICENSE). This covers the skills, commands, agents, and docs authored here. The **pointer skills** (caveman, humanizer, docx, pdf, pptx, xlsx, skill-creator, doc-coauthoring, mcp-builder, figma) only record a name and an upstream link — the upstream projects carry their own licenses (some permissive, some proprietary), which apply when you install them.
