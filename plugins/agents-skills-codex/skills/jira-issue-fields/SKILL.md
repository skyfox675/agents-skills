---
name: jira-issue-fields
description: "Defines and operates the field- and label-based control plane for multi-agent Jira orchestration — issue type (bug/story/task selection), the native Priority field (P0→Highest … P3→Lowest), agent-model-* labels (per-issue model override), agent-effort-* labels (effort directive carried in the dispatch prompt, not an API param), agent-claimed (active lock marker), do-not-dispatch (operator hold), do-not-rebase (auto-rebase opt-out, lives on the GitHub PR not the Jira issue), and ready-to-dispatch (advisory grooming signal). Use whenever you are selecting an issue to dispatch, resolving which model or effort tier a sub-agent should run at, deciding whether an issue may be claimed at all, applying or honoring an operator hold, breaking an auto-rebase starvation loop on a PR, or setting up these fields/labels in a new Jira project — even if the user never says \"labels\"; every dispatch or claim decision must consult this taxonomy first."
---

# Agent Control Fields (Jira)

A small set of Jira fields and labels forms the persistent, auditable control plane
between human operators and orchestrating agents. Fields and labels survive across
sessions, are visible to every concurrent operator, and are machine-readable in
pre-dispatch JQL filters — properties that chat instructions and issue comments do not
have. This skill defines the full taxonomy: what each field/label means, who sets it,
who consumes it, and the resolution rules when signals conflict.

All Jira reads and writes go through the **Atlassian MCP server** (the official
Atlassian Remote MCP). Operations are referenced below by their canonical logical
names (`getJiraIssue`, `editJiraIssue`, `searchJiraIssuesUsingJql`, etc.); the exact
tool names depend on the connected server. Adopters without the Atlassian MCP can
substitute the Jira REST v3 API or a Jira CLI for the same operations — the protocol
is identical, only the call surface changes. (Stated once here; assumed everywhere
below.)

Companion skills: issue selection and the dispatch brief live in the
dispatching-subagents skill; the claim/lock/release protocol behind `agent-claimed`
lives in the jira-issue-locking skill; the recon/triage and groomed-body protocol lives in
the jira-issue-filing skill; the slot loop that reads these fields every round lives in the
orchestrating-slots skill; PR-side mechanics behind `do-not-rebase` live in the
driving-prs-to-merge skill.

## Project bindings

Adopting projects define these values in their own CLAUDE.md. Refer to them by
placeholder everywhere below.

| Binding | Meaning | Example |
| --- | --- | --- |
| `<workhorse-model>` | Default model for all code-writing dispatches | `sonnet` |
| `<cheap-model>` | Model for narrow mechanical tasks only — deliberately has NO label | `haiku` |
| `<premium-models>` | Operator-gated high-attention models (one label each) | `opus`, `fable` |
| `<jira-project-key>` | Project key for JQL `project =` clauses and issue keys | `PROJ` |
| `<jira-site>` / cloudId | The Jira site/cloud the MCP is connected to | resolve dynamically |
| `<jira-done-status>` | Workflow status that closes an issue | `Done` |
| `<jira-inprogress-status>` | In-flight status set when work starts | `In Progress` |
| `<jira-ready-status>` | Status (or label fallback) marking a groomed, dispatchable issue | `Ready` / `triage-ready-to-dispatch` |
| `<integration-branch>` | Branch PRs target (affects close-on-merge, see jira-issue-locking) | `dev` |
| `<auto-rebase-automation>` | Whatever workflow/bot rebases open PRs onto `<integration-branch>` | a scheduled auto-rebase workflow |
| `<operator-logins>` | Operators running orchestrators concurrently — assignees set by accountId, resolved via `lookupJiraAccountId`; current user via `atlassianUserInfo` | resolve dynamically |
| `<lock-comment-format>` | Parseable lock-comment marker paired with `agent-claimed` — full spec in jira-issue-locking | a `claude-lock: ...` line in a comment |

There is **no bootstrap script** to create these — see "No `scripts/` directory" and
"Jira setup" below. The label *names* (`agent-model-*`, `agent-effort-*`,
`agent-claimed`, `do-not-dispatch`, `do-not-rebase`, `ready-to-dispatch`) are portable
as-is; only the model identifiers inside `agent-model-*` are project-specific.

**Label-name matching is case-sensitive.** Whatever casing you adopt for a label is
the only casing your JQL and your post-read checks may assume — e.g. a filter on
`do-not-dispatch` must match the exact stored token. Jira normalizes labels to the
first casing used, so pick one and keep it; a string comparison after `getJiraIssue`
is case-sensitive even where the JQL engine is lenient.

## The taxonomy

| Field / label | Lives on | Who sets it | Who consumes it | Effect |
| --- | --- | --- | --- | --- |
| **Issue type** (`Bug` / `Story` / `Task`) | Issue | Operator / triage | Orchestrator, at triage and dispatch | Classifies the work; picked via `getJiraProjectIssueTypesMetadata`. Replaces the GitHub bug/enhancement type-labels |
| **Priority** field (`Highest`/`High`/`Medium`/`Low`/`Lowest`) | Issue | Operator / triage | Orchestrator, at issue selection | Native Jira Priority. `P0→Highest`, `P1→High`, `P2→Medium`, `P3→Low` (`Lowest` reserved). Fallback `priority-P0` label only if the Priority field is locked down |
| `agent-model-<workhorse-model>` | Issue | Operator | Orchestrator, at dispatch | Pin this issue to the workhorse model (defends against future default changes) |
| `agent-model-<premium-model>` (one label per premium model) | Issue | Operator only | Orchestrator, at dispatch | Authorize AND force the premium model — counts as the operator's explicit instruction |
| `agent-effort-low\|medium\|high\|max` | Issue | Operator | Orchestrator, at dispatch | Effort level; translated into a prose directive inside the dispatch prompt (no API param exists) |
| `agent-claimed` | Issue | Orchestrator | Every orchestrator/operator | Active lock: this issue is being worked. Always paired with assignee + parseable lock comment (jira-issue-locking skill) |
| `do-not-dispatch` | Issue | Operator only | Every orchestrator | Hard hold: never claim, never dispatch, never recon-into-implementation. Operator removes it when the hold lifts |
| `do-not-rebase` | **GitHub PR** (not the Jira issue) | Orchestrator or operator | `<auto-rebase-automation>` | Skip auto-rebase for this PR to stop CI-cancellation starvation. Jira has no PR object; this label stays on the GitHub PR side |
| `ready-to-dispatch` (or `<jira-ready-status>`) | Issue | Triage/grooming pass | Orchestrator, at issue selection | Advisory "this issue is groomed and dispatchable" signal. Never authoritative — re-verify before locking |

How each maps onto the dispatch mechanics:

- `agent-model-*` maps **directly** to the `model` parameter on the `Agent`/`Task`
  tool call (`agent-model-opus` → `model: "opus"`). The hyphen replaces the GitHub
  `:` because Jira labels cannot contain `:` reliably and never contain spaces.
- `agent-effort-*` has **no** corresponding API parameter. If you do not translate it
  into prose inside the dispatch prompt, the operator's effort instruction is silently
  dropped. See "Effort labels" below for the verbatim directives.

## Reading fields/labels — and verifying writes

Read fields and labels at issue-selection time, before resolving model/effort:

```
getJiraIssue(issueKey="PROJ-123", fields=["labels","priority","issuetype","assignee","status"])
```

When *writing* fields or labels via `editJiraIssue`, do not trust a bare success
acknowledgement. A field can be rejected silently — a Priority value that is not in
the project's allowed set, a label normalized to a different casing, or a screen that
omits the field so the update is dropped server-side. Observed in practice on the
GitHub side: an edit reported success, printed a deprecation warning, and persisted
**nothing** — the whole mutation rolled back, leaving a required check red and
auto-merge silently disabled on a PR. The Jira analogue is just as quiet. After any
mutation that matters (a claim, a hold, a priority change), verify by reading it back:

```
getJiraIssue(issueKey="PROJ-123", fields=["labels","priority","assignee"])
# confirm the label is present and the Priority field holds the value you set
```

If a field write keeps failing, confirm the value exists in the project's
configuration (Priority values, issue types) and that the field is on the issue's
edit screen — a missing config value, not your call, is the usual cause.

## Model labels: resolution precedence

Resolve the model for every dispatch from three sources, highest precedence first:

1. **Explicit operator chat instruction for this dispatch** ("dispatch on opus",
   "use the cheap model for this") — always wins, even over labels.
2. **Issue labels** (`agent-model-*`) — the persistent per-issue control.
3. **Defaults** — `<workhorse-model>` for anything that writes or modifies code;
   `<cheap-model>` only for narrow mechanical tasks where errors are immediately
   visible (file-path lookups, running a fixed command and parsing output, listing
   issues, summarizing a diff).

If the choice is still ambiguous after all three sources, default to the workhorse
and **proceed** — pausing to ask the operator stalls the whole orchestration round on
a decision that has a safe default.

Why this shape: it gives the operator a transient knob (chat) and a persistent
per-issue knob (label) without the orchestrator ever exercising its own judgment
about model spend. The label is deliberate, auditable, and survives across
orchestration sessions; the chat instruction handles the one-off exception.

### A premium label IS the operator's explicit instruction

Premium models are operator-gated: never dispatch on one from your own initiative,
and never infer one from your own "this is complex" read of the issue. The reason is
cost discipline learned from real incidents — self-judged escalation inflates spend,
and the operator is the only party with the budget context to decide per dispatch.

That gate creates an apparent tension with labels, resolved like this: **setting
`agent-model-<premium-model>` on an issue counts as the operator saying so.** The
operator placed that label deliberately; honor it. The symmetric failures are both
anti-patterns:

- **Over-escalation:** choosing a premium model because the issue *looks* hard, or
  because a label is *absent* ("no label, so I'll judge"). Absence of a label means
  defaults apply — nothing more.
- **Under-escalation:** refusing or second-guessing an explicit premium request
  (chat or label). The operator decides; you execute.

### Why the workhorse is the floor for code, and why the cheap tier has no label

Evidence observed in practice (a PR-review thread): three consecutive
cheap-model rounds shipped non-passing "fixes" — incomplete fixes, mis-scoped edits,
ignored brief constraints — before a single workhorse-model agent diagnosed the root
cause. The token savings were smaller than the rework cost. Hence: the workhorse
model is the default for **all** code-writing dispatches (implement, refactor, fix,
write/repair tests, edit configs, modify workflows), and the cheap tier is reserved
for tasks where a wrong answer is obvious at a glance.

There is deliberately **no `agent-model-<cheap-model>` label.** The label family is
one-directional: it exists to grant or pin spending authority (pin the workhorse,
authorize a premium tier), not to let anyone force a code-writing task onto a model
proven to ship subtle bugs. A cheap-tier label on an issue would be an invitation to
repeat exactly the rework failure mode that set the policy. The cheap model remains a
*tool-task* choice the orchestrator makes for mechanical sub-steps, never an
escalation/de-escalation knob on issues.

For maximum token savings, `<cheap-model>` is each platform's **cheapest native model** — Haiku 4.5 on Claude Code, Raptor Mini / GPT-mini on Copilot, the free Auto tier on Cursor (see `MODEL-DEFAULTS.md`) — and mechanical sub-steps run as a **cheap-tier subagent** that returns a distilled, caveman answer rather than spending the orchestrator's context (see the dispatching-subagents skill).

## Effort labels: prose transport

`agent-effort-*` is consumed by writing an effort directive into the dispatch prompt
(the dispatching-subagents skill owns the full prompt template). There is no API
parameter, so the translation step is load-bearing:

| Label | Directive to include in the dispatch prompt |
| --- | --- |
| `agent-effort-max` | "Work at maximum effort: be exhaustive, verify every acceptance criterion, do not take shortcuts." |
| `agent-effort-high` | "Work carefully and multi-step: verify each acceptance criterion before moving on." |
| `agent-effort-medium` | Normal multi-step work — no special directive needed beyond the standard brief. |
| `agent-effort-low` | "This is a quick, mechanical change — keep it minimal." |

Effort resolution follows the same precedence as model: chat instruction > label >
default (normal, no special directive). An explicit chat instruction like "max
effort" overrides an `agent-effort-low` label for that dispatch.

## Access-gated model fallback: release the claim, leave the label

If an issue carries `agent-model-<premium-model>` and your current session **cannot
actually dispatch on that model** (no access or entitlement), do not silently
downgrade and do not sit on the issue:

1. Release the claim: remove `agent-claimed`, unassign yourself (set assignee empty),
   and retract or expire the lock comment per the jira-issue-locking skill.
2. **Leave the `agent-model-*` label in place.**
3. Add a short comment (`addCommentToJiraIssue`) stating that this session lacks access
   to the labeled model, so a capable operator session picks the issue up.
4. Move on to the next dispatchable issue.

Why: the label is an explicit operator instruction for that model. Silently
downgrading violates the precedence contract — the operator chose that model
deliberately, possibly because cheaper attempts already failed. Holding the claim
while unable to act starves the issue. Releasing while preserving the label routes
the work to an operator who can honor the instruction, without losing it.

## `agent-claimed`: the active-lock marker

`agent-claimed` marks an issue as actively being worked by an orchestrator. It is one
of **three required signals** — label + Jira assignee (set by accountId) + parseable
lock comment — because different audiences read different channels: humans scan
assignees at a glance, scripts grep the lock-comment marker, and the label drives JQL
filters. Any one alone gets missed by someone. The full claim/release protocol,
stale-expiry window, and multi-operator etiquette live in the jira-issue-locking skill; the
rule that belongs *here* is: lock **before** dispatching, never after — the window
between dispatch and lock is exactly when concurrent orchestrators double-claim.

## `do-not-dispatch`: the operator hold

`do-not-dispatch` is a hard, operator-owned hold. Never claim, dispatch, or
recon-into-implementation an issue carrying it, regardless of priority, staleness,
or how confident you are about the fix. Only the operator removes it.

Why it must be a label and not a comment: observed in practice, four explicit "do not
implement" comments on an issue failed to stop a sibling orchestrator from shipping a
PR — which broke the deploy for roughly two hours on a missing cross-account
prerequisite the operator had been holding for. Comments are prose that a busy
orchestrator skims past; a label is machine-readable in the pre-dispatch JQL filter
and cannot be missed by a correctly written query. Your issue-selection JQL must
exclude both `agent-claimed` and `do-not-dispatch`, and require an empty assignee:

```
project = <jira-project-key>
  AND statusCategory != Done
  AND labels NOT IN (agent-claimed, do-not-dispatch)
  AND assignee is EMPTY
  ORDER BY priority DESC
```

If you discover an issue was dispatched in error against a hold: stop the agent,
revert anything pushed, and re-state the hold in a comment defensively (label stays).

## `do-not-rebase`: breaking auto-rebase starvation

`do-not-rebase` is the one label in this taxonomy that does **not** live on the Jira
issue — Jira has no PR object, so it stays on the **GitHub PR** alongside the
PR-side mechanics. (Jira's Git integration can cross-link the PR to `PROJ-123` via a
smart-commit key in the branch/PR title, but the rebase opt-out is enforced on the
GitHub side where `<auto-rebase-automation>` runs.)

If the project runs `<auto-rebase-automation>` that rebases open PRs whenever
`<integration-branch>` moves, a starvation pattern emerges: sibling PRs merging every
few minutes + a CI suite that takes longer than the merge cadence = every CI run
cancelled by a new base SHA before it finishes. One PR was observed accumulating 5
consecutive cancelled runs in ~50 minutes. `do-not-rebase` opts a PR out of the
automation so one run can complete.

This label is **opt-in and reactive — never auto-applied.** Most projects don't run an auto-rebase automation at all; if yours doesn't, the label is unused and you never touch it.

Operational rules (only when `<auto-rebase-automation>` actually exists):

- **Apply it only after you observe the starvation** — a CI run cancelled by a new base SHA from a rebase. Do **not** set it proactively at PR-open or as a default; a label sitting on every slow PR causes more manual-merge rescues than it prevents.
- Apply it on the PR and verify it stuck (the same silent-rollback hazard applies to
  PR-side label edits — this exact label was the context in which that verify-after-write
  workaround was established).
- **Counter-risk:** a PR left opted-out for hours drifts from its base and ends up
  needing a manual merge rescue. Remove the label (or manually update the branch)
  once the PR is near the front of the queue. Queue mechanics are in the
  driving-prs-to-merge skill.

## `ready-to-dispatch`: advisory only — never authoritative

A grooming or triage pass may mark an issue as well-specified and unblocked — either
by transitioning it to `<jira-ready-status>` or, where the workflow can't be
customized, by applying a `ready-to-dispatch` / `triage-ready-to-dispatch` label (the
jira-issue-filing skill covers what "groomed" means; be explicit about which mechanism your
project uses). The orchestrator may use it to *rank* candidates. It must never be used
to *authorize* a claim, because the signal lies: it persists after another operator
claims the issue. Observed in practice, stale ready signals caused four double-locked
issues in one session.

The only authoritative claim gate is the assignee field. Immediately before locking —
not at selection time, immediately before — re-verify it is empty:

```
getJiraIssue(issueKey="PROJ-123", fields=["assignee"])
# proceed only if assignee is null/empty
```

Equivalently, a JQL `key = PROJ-123 AND assignee is EMPTY` returning the issue
confirms it. If the assignee is non-empty, someone else owns it; move on. See the
jira-issue-locking skill for the full pre-lock checklist.

## No `scripts/` directory

This skill ships **no `scripts/` directory and no bootstrap step**, and that is a
deliberate difference from its GitHub sibling (gh-issue-labels, which bundles a
`scripts/bootstrap-labels.sh` because GitHub labels must be created — with color and
description — before they can be applied). Jira is different in two ways:

- **Labels are created on first use.** Applying `agent-model-opus` or
  `agent-effort-high` via `editJiraIssue` brings the label into existence
  automatically; there is nothing to pre-create. The label family is therefore
  self-bootstrapping.
- **Issue type and Priority are native fields**, configured in the Jira project, not
  objects this skill creates. You select among existing values, you do not provision
  them.

So there is no script to run and nothing to re-run with `--force`. Adopting a project
is purely a matter of recording the bindings and confirming the native fields exist
(next section).

## Jira setup

No labels need pre-creation. Before the first dispatch round, confirm only that the
**native fields** the taxonomy leans on already exist in the project:

- **Priority field values** — ensure `Highest`/`High`/`Medium`/`Low`/`Lowest` exist
  and are on the issue edit screen, so the `P0→Highest … P3→Low` mapping resolves. If
  the Priority field is locked down or absent, fall back to a `priority-P0` style
  label and say so in CLAUDE.md.
- **Workflow statuses** — ensure `<jira-done-status>`, `<jira-inprogress-status>`, and
  `<jira-ready-status>` (if you use a status rather than the `ready-to-dispatch`
  label) exist as reachable transitions. Where the workflow can't be customized, use
  the label fallbacks and be explicit about it.
- **Issue types** — confirm `Bug` / `Story` / `Task` (or your project's equivalents)
  exist; discover the exact set via `getJiraProjectIssueTypesMetadata`.

The `agent-model-*`, `agent-effort-*`, `agent-claimed`, `do-not-dispatch`, and
`ready-to-dispatch` labels require nothing here — they appear the first time
`editJiraIssue` writes them.

After setup, record the bindings table (top of this skill) in the project's CLAUDE.md
so every orchestrator session resolves the same values.

## Policy facts are runtime state, not constants

Model defaults, the slot cap, and queue ceremonies change repeatedly as the operator
tunes them (the cheap-model default was fully inverted once; the slot cap changed
eight times in one project's history). Treat the *mechanism* in this skill — the field
and label families, precedence order, and consumption rules — as stable, but treat the
specific tier assignments and defaults as operator policy the project's CLAUDE.md may
override. When this skill and the adopting project's CLAUDE.md disagree on a binding
value, the project's CLAUDE.md wins.

## Token discipline: caveman for ops, humanizer for prose

This skill runs in high-volume, repetitive orchestration loops where tokens compound across many rounds and many agents. Operate in **caveman mode** (load the `caveman` skill) to cut token use on all working output — status, reasoning, slot tables, completion reports, dispatch and coordination chatter.

Caveman compresses *prose only*. It must NEVER alter machine-precise content, which stays byte-exact: lock-comment markers, the `RECON OK` / `RECON-ERROR` contract lines, JQL, `gh` / Atlassian-MCP commands, label and field names/values, `file:line` references, code blocks, and acceptance-criteria checklists. Compress the narration, never the protocol.

Durable prose a human reads later — issue/ticket bodies and PR descriptions — is the exception: write those through the `humanizer` skill (see the issue-filing skill), not in caveman.
