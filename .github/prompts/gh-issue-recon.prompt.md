---
description: Technical recon of groomed-but-unvetted GitHub issue(s) — drop one or more issue numbers and dispatch a read-only sub-agent per issue (in parallel) to trace the ask into the codebase, produce a verified implementation approach, assert a level-of-effort estimate with confidence, surface risks/dependencies, recommend a split when too big, and post findings back + move the issue to a dev-vetted state. For an eng/project lead sizing accepted work before any code is written. Example — /gh-issue-recon 412 415 418 model:opus
argument-hint: <issue#> [issue# ...] [model:sonnet|opus|fable] [effort:low|medium|high|max]
agent: agent
---

# /gh-issue-recon — technically scope, size, and de-risk groomed issues

> Operate in caveman mode (load the `caveman` skill) — recon fans out and tokens compound. Keep `gh` commands, labels, `file:line` refs, and the `TECH-RECON` contract line byte-exact; the findings comment is the exception (humanizer — see below).

Arguments: `${input:args}`

Parse them as:

- One or more **issue numbers** (with or without `#`). Each is a separately groomed, stakeholder-accepted issue that the dev team has not yet technically reviewed or sized. A lead may drop several at once.
- Optional `model:<tier>` and `effort:<level>` tokens, anywhere — these pin the **recon agent's** tier (default `sonnet`; escalate to `opus` for deep or cross-cutting asks). They are NOT the implementation tier — recon *recommends* that separately in its findings. The cheap tier is never used here (technical judgement on real code needs a capable model; see the technical-recon skill).

Example: `/gh-issue-recon 412 415 418 model:opus`

The **technical-recon** skill is the protocol — the read-only sandbox, the findings-comment anatomy (implementation approach, verified `file:line`, LoE + confidence, risks/unknowns, dependencies, split recommendation, dispatch recommendation), the verdict states, and the output contract all come from it. This is the deeper dev-side pass, distinct from the cheap intake-triage recon in the gh-issue-filing skill. Consult it before dispatching.

## Steps

1. **Resolve the batch.** Collect the issue numbers from the args. Strip the `model:`/`effort:` tokens first. For each, confirm it exists and is open (`gh issue view <N> --json title,body,labels,state`). Skip and report any that are closed or carry an operator hold (`do-not-dispatch`, per gh-issue-labels).

2. **Fan out, one read-only recon agent per issue, in parallel** (single message, per the dispatching-subagents skill). Each agent runs at the resolved tier, briefed with the technical-recon sandbox verbatim: it first reads any prior recon questions + answers already on the issue (a rerun resumes, it does not restart), then reads the repo and the issue — but **writes no code, opens no PR, and never claims/assigns the issue** (claiming is dispatch-time). Pass each agent the conflict-zone list (files other operators' open PRs touch) so its approach avoids them.

3. **Clarify direction to ≥90% before sizing.** Each agent investigates first, then for any ambiguity that materially changes approach/scope/LoE, gets the lead's direction until ≥90% confident (per the technical-recon skill). A fanned-out sub-agent has no interactive question tool, so it asks via **emoji-answerable comments** — one comment per question, each option tagged with a reaction emoji the lead clicks, within GitHub's eight allowed reactions (👍 👎 😄 🎉 😕 ❤️ 🚀 👀), and a one-line legend at the bottom of each comment saying which emoji does what. It then sets `needs-spec-input` and stops **without guessing an LoE**. The lead reacts (or replies) and reruns this command to continue; on rerun the agent reads those reactions and resumes. (If the run does have an interactive ask-question tool, it asks there and continues in the same pass.)

4. **When ≥90%, each agent posts findings and verdicts its issue**: one findings comment via `gh issue comment`, then set the LoE field and one verdict via the gh-issue-labels taxonomy — `ready-to-dispatch` (dev-vetted) or `blocked` (a dependency is open). It also applies the recommended `agent-model:`/`agent-effort:`/lane labels for the eventual implementation dispatch — but a premium model stays a recommendation unless the lead authorizes it (premium labels are operator-gated).

5. **Verify, don't trust.** For each returned `TECH-RECON` line, confirm the comment and labels actually landed (`gh issue view <N> --json labels,comments`) — agents can report a verdict without performing the mutation.

6. **Report one summary table to the lead**: issue #, LoE, confidence, verdict (flagging the **awaiting-answers** ones that need the lead to react/reply and rerun), recommended model/effort, and any split proposals — surfacing the XLs and the blocked/awaiting ones first. Recon proposes splits; it does not create the child issues (that is `/gh-issue` or the lead's call).

If an issue turns out not to be groomed enough to recon (no clear ask), do not guess an estimate — set `needs-spec-input` with the gap named, and say so in the summary.
