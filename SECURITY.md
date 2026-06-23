# Security Policy

## What this repo is

A collection of AI **skills, slash commands, and agent definitions** (Markdown plus a couple of small scripts) for Claude Code, Cursor, and GitHub Copilot. There is no running service and no application code. The security surface is therefore about **what these artifacts instruct an AI agent to do**, and about keeping the repo free of sensitive data.

## Reporting a vulnerability

Report privately. Do **not** open a public issue for a security problem.

- Preferred: GitHub's private vulnerability reporting — the repo's **Security** tab, then **Report a vulnerability**.
- Or email **nick@greysky.me**.

Include the artifact involved, the risky behavior, and a repro or proof of concept. Expect an acknowledgement within a few days. There are no released versions; the supported version is the latest `main`, and fixes land there.

## In scope

- A command, skill, or agent that could lead an agent to take destructive or unintended action — an overly broad `allowed-tools` grant, a prompt that defeats a read-only or sandbox guarantee, or a mutation where a read was intended.
- The bundled scripts (`scripts/*.py`, `scripts/bootstrap-labels.sh`) — shell injection, unsafe execution, and similar.
- Secrets or personal / prior-project data committed to the repo.
- Tool grants that pre-approve more than the command actually needs.

## Out of scope (report upstream)

- The **pointer skills** (caveman, humanizer, docx, pdf, pptx, xlsx, skill-creator, doc-coauthoring, mcp-builder, figma) — their behavior lives in the upstream projects; report there.
- The **MCP servers** (Atlassian, Figma, Playwright, Cypress, Chrome DevTools, claude-in-chrome) and the `gh` / `aws` CLIs — report to their maintainers.
- Your model provider or agent runtime.

## Using these artifacts safely

- **Review before you run.** Read a command or skill before invoking it; you are granting an AI agent the tools it lists.
- **The allowlist is the boundary.** Commands pre-approve specific tools via `allowed-tools`. Keep them narrow; don't blanket-grant `Bash(*)` or `aws:*`. The read-only rule in the AWS diagnosis commands is enforced by a narrow allowlist plus convention — keep the grant tight.
- **Browser and AWS commands act in your real session.** They use your authenticated browser and cloud credentials. They are written to be read-only and careful, but treat them like any tool that holds your access.
- **`curl … | bash`.** The caveman pointer installs via a remote script. Read it first (the README links it) before running.
- **Secrets stay out of issues and specs.** The skills are written to redact tokens and cookies and to seal secrets. If you find one that doesn't, report it.
