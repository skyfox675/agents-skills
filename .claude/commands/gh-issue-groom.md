---
description: Groom a not-yet-dev-ready GitHub issue (pre-technical-recon) — drop one or more issue numbers and dispatch an agent per issue to ask the engineering/project lead about intent, scope, and direction until ≥90% certain the written story reflects the ask, then fill the body to the six-section groomed anatomy. Never modifies existing acceptance criteria unless the operator explicitly asks. Asks via the interactive question tool when available, else emoji-answerable comments; rerun to continue after answers. Example — /gh-issue-groom 530 531
argument-hint: <issue#> [issue# ...] [model:sonnet|opus|fable] [effort:low|medium|high|max]
allowed-tools: Bash(gh issue view:*), Bash(gh issue edit:*), Bash(gh issue comment:*), Bash(gh issue list:*), Bash(gh label list:*)
---

# /gh-issue-groom — groom a story to ≥90% intent before tech review

> Operate in caveman mode (load the `caveman` skill) for working output. Keep `gh` commands, labels, the `GROOM` contract line, and any existing acceptance-criteria text byte-exact; the body prose you write is the exception (humanizer — see the grooming-issues skill).

Arguments: `$ARGUMENTS`

Parse them as:

- One or more **issue numbers** (with or without `#`). Each is a raw, vague, or half-written issue that is not yet ready for development. A lead may drop several at once.
- Optional `model:<tier>` / `effort:<level>`, anywhere — these pin the **grooming agent's** tier (default `sonnet`).

Example: `/gh-issue-groom 530 531`

The **grooming-issues** skill is the protocol — the ≥90%-intent bar, the question channels, what may and may not be written to the body, the verdict states, and the output contract all come from it. Grooming captures the *what* and *why*; the *how* and the LoE come later from `/gh-issue-recon`. Consult the skill before starting.

> **Hard rule (from grooming-issues): do not modify acceptance criteria already written in the issue unless the operator explicitly asks in this run.** Existing AC is an approved contract. If it looks wrong, raise it as a question — don't rewrite it.

## Steps

1. **Resolve the batch.** Collect the issue numbers (strip `model:`/`effort:` first). For each, `gh issue view <N> --json title,body,labels,state`; skip and report any closed or holding `do-not-dispatch`.

2. **Fan out, one grooming agent per issue, in parallel** (single message, per the dispatching-subagents skill). Each agent is briefed with the grooming-issues sandbox verbatim, including the AC-preservation hard rule. It first reads any prior grooming questions + answers on the issue (a rerun resumes, not restarts), reads the issue and its linked context (only light repo reading for context — deep tracing is recon's job), and **writes no code, asserts no LoE/technical approach, and never claims the issue**.

3. **Clarify intent to ≥90%.** Each agent asks the lead about intent, scope, success definition, and edge cases until ≥90% confident the written story reflects the ask. With an interactive question tool it asks there and continues the same pass; without one (the usual fanned-out case) it asks via **emoji-answerable comments** — one comment per question, options tagged with reactions within GitHub's eight (👍 👎 😄 🎉 😕 ❤️ 🚀 👀), a one-line legend at the bottom — then sets `needs-spec-input` and stops. The lead reacts/replies and reruns to continue.

4. **When ≥90%, write the groomed body.** Improve title, symptom/context, desired behaviour, out-of-scope, and traceability toward the six-section anatomy (issue-filing skill) — **preserving any existing acceptance criteria byte-for-byte** unless the operator authorized an edit this run (then note what changed). Draft AC only if none exists, and present it for confirmation. Then set `<groomed-state>` (a `groomed` label) — NOT `ready-to-dispatch` (that is recon's to earn).

5. **Verify, don't trust.** For each `GROOM` contract line, confirm via `gh issue view <N>` that the body changed, existing AC is byte-identical (unless `ac=operator-edited`), and the state moved.

6. **Report one summary table to the lead**: issue #, verdict (flagging **awaiting-answers** ones to react/rerun), whether AC was preserved/added/operator-edited, and the open questions. Groomed issues are ready for `/gh-issue-recon`.
