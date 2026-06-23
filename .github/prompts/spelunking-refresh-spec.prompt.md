---
description: Refresh the living codebase specs after the code has moved — re-recon a spec reference, a domain, a path, or (no arg) the stalest specs; diff each against current code, update discovered behaviour and conventions in place, transition confidence with evidence, flag regressions as drift, append new references for newly-found domains/instances, and re-sync specs/_index.md. Git is the version history; references are never renumbered or deleted (deprecated instead). Example — /spelunking-refresh-spec 1.2, or /spelunking-refresh-spec src/auth
argument-hint: "[ref | domain | path ...] [model:sonnet|opus|fable] [effort:low|medium|high|max]"
agent: agent
---

# /spelunking-refresh-spec — forward-refine the spec set

> Operate in caveman mode (load the `caveman` skill). Keep references, `file:line`, frontmatter, and the `_index.md` table byte-exact; the spec prose is the exception (humanizer — see the spelunking-specs skill).

Arguments: `${input:args}`

Parse them as:

- Optional **scope**: a numeric reference (`1.2.3` or a prefix like `1.2` for a subtree), a domain name/number, or a path. No arg = refresh the specs whose `last_reviewed` is stalest or whose source files changed since (`git diff`/`git log`).
- Optional `model:<tier>` / `effort:<level>`, anywhere — pin the recon agents' tier (default `sonnet`).

Example: `/spelunking-refresh-spec 1.2` (the auth subtree) · `/spelunking-refresh-spec src/payments` · `/spelunking-refresh-spec` (stalest/changed)

The **spelunking-specs** skill is the protocol; this command is its forward-refining pass. Consult it before starting.

## Steps

1. **Resolve scope and read existing specs first.** From `_index.md`, select the in-scope specs. A refresh is a *resume*: read each spec and its cited `file:line` before changing anything — never rewrite from scratch.

2. **Diff understanding against current code** (fan out one agent per spec or per domain, per the dispatching-subagents skill). For each:
   - **Still accurate** → re-verify and update `last_reviewed`; `draft → verified`, or `verified → stable` if unchanged across passes.
   - **Code changed (intended)** → update Discovered behaviour and restate the convention as a *refinement*, with fresh evidence.
   - **Code contradicts the spec and looks like a regression** → do NOT rewrite the standard to match broken code; flag it in Drift & open questions as a candidate issue.
   - **New domain/subdomain/instance found** → append the next free number, add to `_index.md` (never reuse or renumber).
   - **Gone/dead** → mark `status: deprecated` with a pointer to the successor ref; do not delete the reference.

3. **Verify, don't trust.** Re-read cited `file:line` for the claims you touched before flipping any confidence upward; can't re-confirm ⇒ drop to `draft` with a note.

4. **Re-sync `_index.md` and report**: references added/deprecated, confidence transitions, and the new drift/regression candidates (which the operator may file as issues via the issue-filing skill). Recon writes only specs; it does not modify application code.

Run any rewritten prose through the `humanizer` skill; keep evidence, references, and frontmatter exact.
