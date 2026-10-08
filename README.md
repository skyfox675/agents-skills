# agents-skills

A toolbox of skills, slash commands, and agents for AI coding assistants. It runs in Claude Code, Cursor, GitHub Copilot, Kiro, and OpenCode.

Four kinds of thing live here:

- **Skills** load themselves when your task matches. Set them up once and forget about them.
- **Commands** are shortcuts you type, like `/gh-issue the login button does nothing`. Each one runs a fixed workflow.
- **Agents** are the specialized workers those commands spawn, already wired up. A locator, an implementer, a reviewer, and a dozen more.
- **MCPs** are optional connectors for Jira, AWS, a browser, or Figma. Install only the ones your flows need.

The whole set is tuned to get an accurate answer for as few tokens as it can manage. It talks in a terse "caveman" mode and pushes cheap work down to cheap models. The model policy lives in [`MODEL-DEFAULTS.md`](MODEL-DEFAULTS.md) and [`CLAUDE.md`](CLAUDE.md).

Do the Quickstart for whichever tool you use. The full inventory is under [What's included](#whats-included).

## Install as a plugin

This repo is its own plugin marketplace for both Claude Code and Cursor, so on either tool you get every skill, agent, and command without copying files.

On Claude Code, two lines:

```
/plugin marketplace add skyfox675/agents-skills
/plugin install agents-skills@agents-skills
```

On Cursor, install `agents-skills` from the plugin marketplace, or point Cursor at this repository. It carries a `.cursor-plugin/marketplace.json` at the root, so Cursor can source the plugin straight from git.

Every [release](https://github.com/skyfox675/agents-skills/releases) attaches both plugins, `agents-skills-plugin.zip` for Claude Code and `agents-skills-cursor-plugin.zip` for Cursor, plus one zip per skill. The per-skill zips exist for Claude Desktop, where you upload them under Settings, then Capabilities, then Skills. Releases are versioned `YYYY.M.D.N` and tagged `v<version>`.

For any other tool, or if you would rather copy the raw files into your own project, use the Quickstart.

## Quickstart

1. **Get the files.** Clone this repo and open the folder in your tool. Skills, commands, and agents are already set up inside `.claude/`, and mirrored to `.cursor/`, `.github/`, `.kiro/`, and `.opencode/`. To use them in your own project instead, copy your tool's folders (named below) into your project root.

   ```bash
   git clone https://github.com/skyfox675/agents-skills.git
   ```

2. **Install the helper skills.** The small pointer skills (caveman, humanizer, docx, and the rest) only record a name and a link to a tool maintained elsewhere, so you install the current version from the source. Paste the prompt from your tool's section below and let your assistant run it.

3. **Add the MCPs you need.** Optional. The Jira, AWS, browser, and Figma commands each need a matching MCP. Install only the ones for the flows you actually use, and register each under the server key shown in [MCPs and external tools](#mcps-and-external-tools).

4. **Use it.** Type `/` in the chat to list the commands, or just describe your task and let the skills and agents pick themselves.

Open your tool's section and ignore the rest.

<details>
<summary><b>Claude Code</b></summary>

&nbsp;

Skills, commands, and agents load automatically from the `.claude/` folder, so if you opened this repo they already work. Type `/` to see the commands. To use them in your own project, copy this repo's `.claude/` folder into your project root. For the Jira, AWS, browser, and Figma flows, add the matching MCP (see [MCPs and external tools](#mcps-and-external-tools)).

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

The short path is the plugin: install `agents-skills` from Cursor's plugin marketplace, or point Cursor at this repository, which carries its own `.cursor-plugin/marketplace.json`. That gets you every skill, agent, and command at once.

To wire it up by hand instead: Cursor reads skills from `.claude/skills/`, commands from `.cursor/commands/`, and agents from `.cursor/agents/`, all of which are already in this repo. To use them in your own project, copy this repo's `.cursor/` and `.claude/skills/` folders into your project root. Type `/` in chat to see the commands. For the Jira, AWS, browser, and Figma flows, add the matching MCP (see [MCPs and external tools](#mcps-and-external-tools)).

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

Copilot reads skills from `.claude/skills/`, commands (prompt files) from `.github/prompts/`, and agents from `.github/agents/`, all of which are already in this repo. To use them in your own project, copy this repo's `.github/` and `.claude/skills/` folders into your project root. Type `/` in Copilot Chat to see the commands. For the Jira, AWS, browser, and Figma flows, add the matching MCP (see [MCPs and external tools](#mcps-and-external-tools)).

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

<details>
<summary><b>Kiro</b></summary>

&nbsp;

Kiro reads agents from `.kiro/agents/` and skills from `.kiro/skills/`, both of which are already in this repo. Kiro uses the same Agent Skills format as Claude, so `.kiro/skills` is a symlink to `.claude/skills` rather than a second copy. That means you need both folders: copy this repo's `.kiro/` and `.claude/skills/` into your project root, or the link will dangle.

Slash commands are not mirrored to Kiro yet. Skills and agents are.

Install the helper skills by pasting this to Kiro:

```text
Install these skills into .kiro/skills/ (or ~/.kiro/skills/ for every project). Each skill is a folder with a SKILL.md inside it:
1. Anthropic skills (docx, pdf, pptx, xlsx, skill-creator, doc-coauthoring, mcp-builder): copy each skills/<name>/ folder from github.com/anthropics/skills
2. caveman: run its official installer from github.com/JuliusBrussee/caveman
3. humanizer: git clone github.com/blader/humanizer
Then tell me what you installed.
```

</details>

<details>
<summary><b>OpenCode</b></summary>

&nbsp;

OpenCode reads agents from `.opencode/agents/` and skills from `.opencode/skills/`, both of which are already in this repo. Like Kiro, it uses the standard Agent Skills format, so `.opencode/skills` is a symlink to `.claude/skills`. Copy both `.opencode/` and `.claude/skills/` into your project root so the link resolves.

Slash commands are not mirrored to OpenCode yet. Skills and agents are.

Install the helper skills by pasting this to OpenCode:

```text
Install these skills into .opencode/skills/ (or ~/.opencode/skills/ for every project). Each skill is a folder with a SKILL.md inside it:
1. Anthropic skills (docx, pdf, pptx, xlsx, skill-creator, doc-coauthoring, mcp-builder): copy each skills/<name>/ folder from github.com/anthropics/skills
2. caveman: run its official installer from github.com/JuliusBrussee/caveman
3. humanizer: git clone github.com/blader/humanizer
Then tell me what you installed.
```

</details>

One note on caveman. It installs by running a script (`curl ... | bash`), which runs code on your machine. That is normal for installers, but read [`install.sh`](https://raw.githubusercontent.com/JuliusBrussee/caveman/main/install.sh) first if you want to know what it does.

## What's included

### Commands (you type these)

A common flow: groom a vague ticket, size it with recon, build it with dispatch, unstick it with rescue. Or skip straight to a ready-to-build ticket with `/gh-issue`. Every `gh-issue-*` command has a `jira-issue-*` twin, so use whichever tracker you run.

| Command (GitHub / Jira) | What it does |
|---|---|
| `/gh-issue` · `/jira-issue` | Files a fully groomed bug or feature ticket from a one-line description. It reads the code, verifies evidence, checks for duplicates, and labels it. |
| `/gh-issue-use-aws` · `/jira-issue-use-aws` | Same, plus a read-only AWS dig (logs, config, CloudTrail) so the ticket carries a cloud-traced root cause. |
| `/gh-issue-use-browser` · `/jira-issue-use-browser` | Same, plus a live browser repro on whatever browser MCP is connected (Chrome, Playwright, or Cypress). It watches network, console, and DOM. |
| `/…-use-chrome` · `/…-use-playwright` · `/…-use-cypress` | Same as `use-browser`, but pinned to one engine when you want to pick. Each has a `gh-issue-` and a `jira-issue-` form. |
| `/gh-issue-use-aws-browser` · `/jira-issue-use-aws-browser` | Browser and AWS together, correlated, for when nobody knows which layer is failing. |
| `/…-use-aws-chrome` · `/…-use-aws-playwright` · `/…-use-aws-cypress` | The same full-stack dive, browser phase pinned to one engine. |
| `/gh-issue-groom` · `/jira-issue-groom` | Takes a vague existing ticket and asks you questions until the story is clear (90 percent or better). It leaves approved acceptance criteria alone unless you say otherwise. |
| `/gh-issue-recon` · `/jira-issue-recon` | Reads the code and adds an implementation plan, an effort estimate, and the risks to a groomed ticket, so you can size work before building it. |
| `/spelunking-init-spec` | Digs through an unfamiliar codebase and writes living spec docs that describe how it actually works. |
| `/spelunking-refresh-spec` | Updates those specs after the code moves. |
| `/figma-init-spec` | Snapshots a Figma file into living design specs anchored to stable IDs, so they survive a reorganization. |
| `/figma-refresh-spec` | Diffs Figma against the design specs and reports drift, separating real changes from pure moves. |
| `/dispatch` | Runs an N-agent loop that picks up ready tickets, builds them, and drives the PRs to merge. |
| `/rescue` | Unsticks a stuck PR or a failing environment: red CI, merge conflict, blocked review. |
| `/kill` | Emergency brake. Kills runaway agents when the machine is overloaded, then salvages their work. |

### Skills (load automatically)

These power the commands above, plus the `/loop` watcher and CI-hunter lanes, so you rarely call them by hand.

| Skill | What it does |
|---|---|
| `dispatching-subagents` | Turns a ready ticket into a running implementation agent and a PR. |
| `driving-prs-to-merge` | Gets an opened PR all the way to merged: CI triage, review threads, conflicts, merge queue. |
| `pr-comments` · `pr-checks` · `pr-cleanup` | Single-lane interval watchers. One drives review threads to resolved and arms auto-merge, one keeps CI green and the merge queue healthy, one tidies up after PRs close. |
| `deploy-watching` | Interval watcher for the integration environment's deploy. Tells a transient red from a real one, re-runs the first, and fixes the second forward. Never reverts. |
| `ci-speed-hunting` · `ci-flake-hunting` | Continuous CI lanes. One mines timing to cut wall-clock latency without losing coverage. The other root-causes flakes and fixes them forward. Both exist to raise merge-queue throughput. |
| `fast-forwarding-branches` | Keeps the primary checkout fast-forwarded on a loop, so every worktree an agent cuts starts from a current base. When the pull is blocked it alerts and changes nothing. |
| `orchestrating-slots` | The N-slot loop that keeps a fixed number of agents working the queue. |
| `gh-issue-filing` · `jira-issue-filing` | How to write a ticket an agent can build without asking a single follow-up question. |
| `gh-issue-locking` · `jira-issue-locking` | Claims and locks tickets so two people never double-work the same one. |
| `gh-issue-labels` · `jira-issue-fields` | The label and field control plane: priority, model tier, do-not-touch holds. |
| `grooming-issues` | Clarifies a vague ticket's intent to 90 percent before any work starts. |
| `technical-recon` | Sizes a groomed ticket: implementation approach, effort, risks. |
| `spelunking-specs` | Digs a codebase into living, versioned spec docs. |
| `browser-diagnosis` | Reproduces a front-end bug in whichever browser MCP is connected (Chrome, Playwright, or Cypress) and captures the evidence. |
| `figma-specs` | Tracks Figma design drift using stable IDs and a repo-owned design-to-code map, so a file reorganization does not trigger needless re-touches. |

The helper skills below point at tools maintained elsewhere. You install them in the Quickstart.

| Skill | What it does |
|---|---|
| `caveman` | Terse mode. Roughly 75 percent fewer tokens at the same accuracy. |
| `humanizer` | Strips the tell-tale signs of AI writing out of prose. |
| `skill-creator` | Builds, tests, and tunes your own skills. |
| `docx` · `pdf` · `pptx` · `xlsx` | Read and create Word, PDF, PowerPoint, and Excel files. |
| `doc-coauthoring` | Co-writes docs, specs, and proposals with a structured workflow. |
| `mcp-builder` | Builds MCP servers that connect AI tools to outside services. |
| `figma` | Points at Figma's official plugin and Dev Mode MCP for design context, tokens, and design-to-code. It powers the `figma-*` commands. |

### Agents

These are the workers the commands spawn, plus the single-lane watchers and CI hunters you run continuously with `/loop`. Each one runs on the cheapest model that fits, which is how heavy work stays cheap. The canonical agents live in `.claude/agents/`. Running `make sync-agents` generates the Cursor (`.cursor/agents/`), Copilot (`.github/agents/`), Kiro (`.kiro/agents/`), and OpenCode (`.opencode/agents/`) copies, so every supported tool gets them.

| Agent | Tier | Backs | What it does |
|---|---|---|---|
| `scout` | cheap | every command | Read-only `file:line` locator, the mechanical-offload worker. |
| `builder` | workhorse | small dispatches | Surgical one- or two-file edits. Refuses bigger scope. |
| `reviewer` | workhorse | `/dispatch`, pre-merge | Adversarial diff review, tagged by severity. |
| `implementer` | workhorse | `/dispatch` dev slots | Builds one issue, writes tests, opens a PR. |
| `pr-dispatcher` | workhorse | `/loop` dev lane | Keeps dev slots full. Claims groomed issues, spawns `implementer`, hands the PR off at open. |
| `pr-rescuer` | workhorse | `/rescue` | Unsticks stuck PRs and red CI. |
| `pr-comments` | workhorse | `/loop` review lane | Drives bot and human review threads to resolved, then arms auto-merge. |
| `pr-checks` | workhorse | `/loop` CI lane | Keeps checks green and the merge queue healthy. Head-green is not queue-green. |
| `pr-cleanup` | workhorse | `/loop` cleanup lane | Post-merge janitor. Closes issues, releases locks, reclaims local disk. |
| `deploy-watcher` | workhorse | `/loop` deploy lane | Keeps the integration deploy green by fixing forward. Re-runs transients, opens fix PRs for real breaks, hands them to the PR lanes. |
| `ci-speed-hunter` | workhorse | `/loop` CI-speed lane | Mines CI timing and cuts wall-clock latency without losing coverage. |
| `ci-flake-hunter` | workhorse | `/loop` CI-flake lane | Root-causes flaky jobs and fixes them forward. Never masks. |
| `branch-ff` | workhorse | `/loop` fast-forward lane | Keeps the primary checkout current with `pull --ff-only`. Alerts, never clobbers. |
| `diagnostician` | workhorse | `use-aws`, `use-chrome`, recon | Read-only AWS and browser repro that returns evidence. |
| `verifier` | workhorse | dispatch, recon, spelunking | Verify-then-trust gate. Trusts no claim unchecked. |
| `spelunker` | workhorse | `/spelunking-init-spec` | Maps one domain of a codebase into specs. |
| `design-mapper` | workhorse | `/figma-init-spec` | Maps one Figma domain into drift-resistant design specs. |

## MCPs and external tools

Most commands need nothing extra. These add capabilities for specific command families, so install only what you use.

| Tool / MCP | Powers | Required? | Install |
|---|---|---|---|
| GitHub `gh` CLI | the `gh-issue-*` commands, `/dispatch`, `/rescue` | yes, for the GitHub flow | install the GitHub CLI, then `gh auth login` |
| Atlassian (Jira) MCP | the `jira-issue-*` commands | yes, for the Jira flow | add Atlassian's official MCP under server key `atlassian`, then authenticate |
| AWS CLI | the `*-use-aws*` commands | optional (cloud-traced diagnosis) | install the AWS CLI and configure read-only credentials |
| A browser MCP (pick one) | the `*-use-browser`, `-chrome`, `-playwright`, and `-cypress` commands | optional (front-end diagnosis) | Playwright: `claude mcp add playwright npx @playwright/mcp@latest`. Cypress: `npx cypress-mcp --project .` (server key `cypress`, needs Cypress 12 or newer plus `npx playwright install chromium`). Chrome: the claude-in-chrome extension. Chrome DevTools: `chrome-devtools-mcp`. |
| Figma MCP | the `figma-*` commands | optional (design drift) | register the Figma Dev Mode MCP under server key `figma`, per Figma's setup docs, then authenticate. `/plugin install figma@claude-plugins-official` also works, but it exposes `mcp__plugin_figma_figma__*`, so allowlist that prefix if you use it. |

Register each MCP under the server key shown: `playwright`, `cypress`, `chrome-devtools`, `figma`, `atlassian`. The bundled command `allowed-tools` and agent `tools` pre-approve `mcp__<key>__*`. A different key means permission prompts on commands and missing access for agents, so either match the key or allowlist your prefix in `.claude/settings.json`.

Which model each tool uses per platform is in [`MODEL-DEFAULTS.md`](MODEL-DEFAULTS.md). The helper skills (caveman, humanizer, docx, and the rest) install in the Quickstart above.

## Git hooks

[`hooks/`](hooks) holds portable git hooks and matching CI workflows you can drop into any repo. They are templates, not wired to this repo. Plain POSIX `sh`, no husky and no Node. Every external tool they call is optional and skips when it is absent.

| File | Kind | Does |
|---|---|---|
| `commit-msg` | local | Enforces Conventional Commits format on the message. |
| `pre-commit` | local | Scans staged changes for secrets with gitleaks. |
| `pre-push` | local | The lint gate: your project's own check, plus Claude artifact frontmatter, markdownlint, and actionlint. |
| `pr-title.yml` | CI | Server-side PR-title format check. Mirrors `commit-msg`. |
| `gitleaks.yml` | CI | Server-side secret scan on every push and PR. |
| `claude-code-pretooluse.sh` | harness | Optional Claude Code `PreToolUse` bridge. Runs the same checks before the model's `git commit` or `git push`, and cannot be skipped with `--no-verify`. |

To install, run `sh hooks/install.sh`, which points `core.hooksPath` at `hooks/`. Then copy the CI templates into `.github/workflows/`. For the optional Claude Code harness layer, merge `hooks/claude-settings.hooks.json` into `.claude/settings.json`. Details and customization live in [`hooks/README.md`](hooks/README.md).

## Going deeper

- [`GLOSSARY.md`](GLOSSARY.md) defines the words this repo uses in a specific way: slot, dispatcher, watcher, hunting, ci-speed, flake. Read it first if the lane names look interchangeable, because they are not.
- [`MODEL-DEFAULTS.md`](MODEL-DEFAULTS.md) covers which model each task uses, per platform, and how to save tokens.
- [`CLAUDE.md`](CLAUDE.md) and [`AGENTS.md`](AGENTS.md) cover the conventions, the model policy, and how the five tools stay in sync.
- [`.claude/skills/`](.claude/skills) holds every skill. The pointer skills list their own install steps.
- To edit a command or agent, change it in `.claude/commands/` or `.claude/agents/`, then run `make sync` to regenerate the Cursor, Copilot, Kiro, and OpenCode copies.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) explains how to add skills, commands, and agents, and the sync rule that keeps the mirrors honest. [`SECURITY.md`](SECURITY.md) explains how to report a security issue.

## License

MIT. See [LICENSE](LICENSE). That covers the skills, commands, agents, and docs written here.

The pointer skills (caveman, humanizer, docx, pdf, pptx, xlsx, skill-creator, doc-coauthoring, mcp-builder, figma) only record a name and an upstream link. The upstream projects carry their own licenses, some permissive and some not, and those apply once you install them.
