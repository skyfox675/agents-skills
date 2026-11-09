---
name: jira-issue-locking
description: "Claim/lock/release protocol for Jira issues worked by AI agents, with multi-operator coordination etiquette. Use whenever an orchestrator is about to claim, dispatch, or start work on a Jira issue (lock BEFORE dispatch, always); whenever a PR linked to a claimed issue merges or closes (release the lock and explicitly transition the issue to Done — do not rely on Jira's PR-merge auto-transition); whenever you find an issue carrying a lock label or lock-marker comment and must decide active-vs-stale; and during any batch flow that claims multiple issues in one pass — even if the user only says \"pick up the next issue\", \"work PROJ-123\", \"fix\", \"release the lock\", or \"why is this issue still open\". Also covers bundled-issue locks, stale-lock reclaim, the multi-claim race re-check, and what to do when another operator already holds the lock."
---

# Locking Jira Issues: Claim, Coordinate, Release

Multiple orchestrator sessions — run by different humans, on different machines, at the same time — work the same Jira issue queue. Without a claim protocol, two agents silently pick up the same issue, burn duplicate work, and open conflicting PRs. This skill is the claim protocol: how to lock a Jira issue before dispatching work, how to recognize and respect (or reclaim) someone else's lock, and how to release cleanly on every exit path.

All Jira reads and writes here go through the **Atlassian MCP server** (the official Atlassian Remote MCP); operations are referenced by their canonical tool names (`getJiraIssue`, `editJiraIssue`, `searchJiraIssuesUsingJql`, `addCommentToJiraIssue`, `transitionJiraIssue`, `lookupJiraAccountId`, `atlassianUserInfo`). Exact tool names depend on the connected server. An adopter without the Atlassian MCP can substitute the Jira REST v3 API or a Jira CLI for the same operations — the protocol is identical, only the call surface changes.

Related skills: pick what to claim with the jira-issue-filing and jira-issue-fields skills; dispatch the work with the dispatching-subagents skill; run the surrounding loop with the orchestrating-slots skill; drive the resulting PR with the driving-prs-to-merge skill.

## Project bindings

These values are project policy, not protocol. The adopting project defines them in its own CLAUDE.md; this skill refers to them by placeholder.

| Binding | Meaning | Illustrative default |
|---|---|---|
| `<jira-project-key>` | Project key for JQL `project = ...` scoping (e.g. `PROJ`) | — |
| `<jira-site>`/cloudId | The Jira site the MCP targets | — |
| `<integration-branch>` | Branch agent PRs merge into | `dev` (default branch was `main`) |
| `<jira-done-status>` | Workflow status meaning "resolved/closed" | `Done` |
| `<jira-inprogress-status>` | Workflow status meaning "an agent is on it" | `In Progress` |
| `<jira-ready-status>` | Workflow status for queued, dispatchable work | `Ready` |
| `<claim-label>` | Site-wide "an automation holds this" label | `agent-claimed` — created on first use, no bootstrap needed |
| `<lock-marker>` | Stable greppable token in every lock comment | `claude-lock:` |
| `<hold-label>` | Operator-held "humans only, never dispatch" label | `do-not-dispatch` — Jira label-name comparisons are case-sensitive; pick one casing and let every filter assume it (lowercase, single-token, no spaces) |
| `<stale-window>` | Lock age threshold before reclaim is considered | 24h (tune to typical PR cycle time) |
| `<worktree-dir>` | Where agent worktrees live | see the dispatching-subagents skill |
| `<chat-channel>` | Team real-time channel for urgent pings | Slack |
| `<bot-trigger>` | The project's human-only AI-mention trigger | `@claude` |
| Operator identities | Informational roster of known operators | resolve dynamically — see below |

`<claim-label>` and `<lock-marker>` defaults carry no project semantics and can be adopted verbatim. Unlike GitHub, Jira needs no bootstrap script for the label — `<claim-label>` is created the first time it is applied with `editJiraIssue`. If you rename either binding, rename it in every JQL query and snippet below — a marker that drifts from the searches makes every lock invisible to stale-detection.

## The three coordination primitives

Every claimed issue carries exactly three signals, placed together. Each serves a different consumer at a different cost; dropping any one breaks that consumer.

1. **Assignee = the operator's Jira account, set by `accountId`.** The at-a-glance human signal. It is what JQL `assignee = currentUser()` filters on, what the web UI shows as an avatar, and what other operators scan to find unclaimed work. Resolve the account via `lookupJiraAccountId` and set it with `editJiraIssue` (Jira assignment is by `accountId`, not by display name or email). Concurrent operators scope their slot math to `assignee = currentUser()`; an issue with the wrong (or a lingering) assignee scrambles everyone's view.
2. **`<claim-label>` = the coarse machine lock.** Any orchestrator scanning the open queue sees "an automation is on this" from a cheap `searchJiraIssuesUsingJql` query (`labels = <claim-label>`), without fetching N issues' comments.
3. **A lock comment with a machine-parseable marker line = the canonical record.** It answers who/where/when in enough detail (operator, worktree, branch, timestamp) to do staleness arithmetic and rescue work. Jira has no hidden HTML comment, so the marker lives on its own line in a plain/code block: humans see it, but it is still parseable. The bullet list above it gives humans the same fields in readable form.

The compression to remember: **the comment is the canonical record; the label is the signal; the assignee is the face.**

## Resolve operator identity dynamically

Once per session, resolve the current user's `accountId` via the Atlassian MCP:

```
atlassianUserInfo          → the current account (email, display name)
lookupJiraAccountId(self)  → OPERATOR = <accountId>
```

Use `OPERATOR` (the `accountId`) everywhere: issue assignee, the `operator=` field in lock comments, PR assignee (sub-agents must self-assign the same operator — see the dispatching-subagents skill), and `assignee = currentUser()` scoping. Do not hardcode an operator roster in docs or scripts: rosters drift. An illustrative procedure file once listed an identity that disagreed with the rest of its memory by one character — dynamic resolution from the auth context is the only value that cannot rot. A roster in project bindings is informational only.

## Before you claim: the pre-claim check

Run this gate immediately before every lock, even if a queue scan minutes ago said the issue was free.

1. **Hold label.** If the issue carries `<hold-label>`, stop. It is operator-held work deliberately reserved for humans. If an agent claimed one in error, stop the agent and revert the claim.
2. **Assignee must be empty.** Dispatch-readiness signals lie — in one observed case a `triage-ready-to-dispatch` state persisted after another operator claimed, producing four double-locked issues. The assignee field is the only authoritative claim gate; re-verify it is empty (JQL `assignee is EMPTY`, or `getJiraIssue` showing a null `assignee`) immediately before locking, because another operator may have claimed between your scan and now.
3. **Search for an existing lock marker:**

```
searchJiraIssuesUsingJql:
  jql: key = PROJ-123 AND comment ~ "claude-lock"
# then read the matching comments:
getJiraIssue(PROJ-123)  → inspect comments for the <lock-marker> line
```

Then decide three ways:

| State | Test | Action |
|---|---|---|
| **Active** | Marker ≤ `<stale-window>` old, **or** any age with a linked PR still open | Bail out. Report who holds it (`operator=`) and where (`worktree`/`branch`). Coordinate via `<chat-channel>`; never reclaim. |
| **Stale** | Marker > `<stale-window>` old **and** no PR activity (linked PR closed/merged without release, or no PR at all) | Reclaim politely (below). |
| **No lock** | No marker found | Proceed to claim. |

Staleness is a **two-condition** test: age AND PR state. A 3-day-old lock with a healthy open PR is ACTIVE — treating age alone as staleness recreates exactly the two-agents-on-one-issue race this system exists to prevent. The dual condition also kills zombie locks from crashed orchestrators whose PR died.

## Placing a lock (atomic, and always before dispatch)

Lock first, dispatch second — always. A sub-agent already working an unlocked issue is invisible to every other operator's scan; the claim window must close before any work starts.

`<claim-label>` needs no bootstrap on Jira — applying it once with `editJiraIssue` creates it. Use the binding's exact casing and token (no spaces — Jira labels cannot contain them).

Claiming is three actions that must all land — a partial lock (label without assignee, comment without label) breaks one of the three consumers and is invalid:

```
# 1+2. label and assignee in one edit
editJiraIssue(PROJ-123):
  labels:  add "<claim-label>"
  assignee: <accountId of $OPERATOR>      # resolved via lookupJiraAccountId

# 3. the lock-marker comment (ADF/wiki markup; the marker is its own line)
addCommentToJiraIssue(PROJ-123, body):
  **Agent session lock** — claimed by an automated session; do not assign to another agent.

  - operator: `<accountId>`
  - worktree: `<absolute-path-to-worktree>`
  - branch: `<branch-name>`
  - claimed at: `<ISO-8601 UTC timestamp>`

  ```
  claude-lock: operator=<accountId> worktree=<absolute-path> branch=<branch> at=<ISO-8601 UTC>
  ```

  This lock auto-expires after <stale-window> of no PR activity. If you can confirm the session
  has ended, reclaim by removing the `<claim-label>` label AND the assignee, then start work.
```

The canonical marker line uses the placeholder (with the default binding this renders as `claude-lock: ...`):

```
claude-lock: operator=<accountId> worktree=<path> branch=<branch> at=<ISO-8601 UTC>
```

This exact shape is the search target — `comment ~ "claude-lock"` finds it, and the line is then parsed field-by-field. `<path>` is the `<worktree-dir>` value bound per the dispatching-subagents skill.

Three pitfalls that have each produced broken locks in practice:

- **Put the marker on its own line in a code/plain block** so Jira's renderer does not reflow or linkify it — a marker wrapped into a paragraph or auto-linked is harder to parse, and stale-detection that reads it field-by-field can misattribute it.
- **Resolve the assignee to an `accountId`, not a name or email.** A comment or assignment carrying a display name or email instead of the `accountId` cannot be matched back to the operator by `assignee = currentUser()` or by marker parsing.
- **Substitute real values; do not post placeholders.** Agents copying the template verbatim have posted comments containing literal `<absolute-path-to-worktree>`, which breaks marker parsing and tells other operators nothing.

The lock comment is deliberately self-documenting: the expiry policy and exact reclaim mechanics are embedded in the lock itself, so a future agent or human who finds it needs no procedure file to act correctly.

## Bundled-issue locking

When one dispatch covers several issues (a lead issue plus tightly-coupled siblings fixed in the same PR), do not duplicate the full lock everywhere — duplicated worktree/branch records drift. Instead:

- **Lead issue**: full three-signal lock as above.
- **Each sibling**: label + assignee as normal, plus a short comment whose marker points at the lead:

```
addCommentToJiraIssue(PROJ-456, body):
  **Bundled with PROJ-123** — claimed as part of the same agent session; see the lock on PROJ-123.

  ```
  claude-lock: bundled_with=PROJ-123 operator=<accountId> at=<ISO-8601 UTC>
  ```
```

Anyone doing staleness arithmetic on a sibling follows `bundled_with` to the lead and evaluates that lock; release of the lead releases the bundle (run the release steps on every bundled issue).

## Batch claims: the race re-check

Jira has no compare-and-swap, so batch claiming is optimistic-lock-then-verify. When claiming several issues in one flow (e.g. a "claim the next 5 open issues" trigger), another operator can lock the same issue between your read and your edit. So, immediately after placing each lock, re-fetch and check for active markers:

```
# Collect all lock-marker comments on this issue
getJiraIssue(PROJ-123) → all comments whose body contains "claude-lock"

# For each operator, consider only their NEWEST marker (ignore markers older
# than the most recent "Session lock released" comment for that operator).
# If more than one operator has an active marker (placed within the current
# race window), earliest at= timestamp wins.
```

Earliest-`at=`-wins is a deterministic tiebreak both parties compute independently — no negotiation channel needed. Active-marker comparison: consider only the newest marker per operator and ignore any marker whose `at=` timestamp predates the most recent "Session lock released" comment from that operator (released locks leave their comment in place but are no longer active).

The re-check is required **only** in multi-claim flows; for a single-issue claim the read-then-edit window is short enough that the race is negligible, and adding the ceremony everywhere is waste. Skipping it in batch flows lets two operators silently double-claim.

## Stale locks: polite reclaim

When the pre-claim check says STALE:

```
editJiraIssue(PROJ-123):
  labels:   remove "<claim-label>"
  assignee: unset                      # clear the prior operator's accountId
addCommentToJiraIssue(PROJ-123):
  "Reclaiming stale lock from <prior-operator> (last activity <at>). Continuing work."
# then place a fresh lock with your own $OPERATOR per the standard procedure
```

Remove **both** the label and the prior assignee — each is read by a different scan, and a lingering assignee makes the issue look claimed forever. The explicit reclaim comment keeps the audit trail honest: who took over, from whom, why.

One thing reclaim cannot do: recover the prior work. The prior operator's worktree is local to their machine. Reclaim means re-dispatch fresh — do not waste time hunting for their in-progress branch.

**Never reclaim an active lock**, even to "speed things up." Recent timestamp plus an in-flight PR means another agent is working right now; reclaiming creates the exact race the system prevents. If your need is genuinely more urgent, post a comment on the issue describing the conflict — the other operator's orchestrator will surface it on its next tick — and/or ping `<chat-channel>`.

## Releasing locks

Every exit path has a release. The semantics are deliberately **asymmetric** — success keeps the assignee as credit, failure strips it for availability — and that asymmetry is load-bearing.

### PR merged into `<integration-branch>` — release AND explicitly transition to Done

Do not rely on Jira's PR-merge auto-transition. Jira's GitHub/Bitbucket integration *can* auto-move an issue to a done status when a PR merges, but only if the project is configured with smart-commit / development-panel automation and the PR carries the Jira key (`PROJ-123` in branch or title). If that automation is absent — or your agent PRs land on a non-default `<integration-branch>` the automation does not watch — every issue silently stays open after its fix merges: the queue fills with phantom work, other operators re-dispatch already-solved problems, and claim labels stick around. (In practice this produced zombie recon dispatches on merged work, and one session missed the explicit transition nine times before the operator caught it.) The orchestrator must transition explicitly, three operations in order:

```
# 1. release the lock label (assignee RETAINED as completion credit)
editJiraIssue(PROJ-123): labels remove "<claim-label>"
# 2. transition to the done status, recording the resolving PR
transitionJiraIssue(PROJ-123 → <jira-done-status>)
addCommentToJiraIssue(PROJ-123): "Resolved by PR #1234 (merged into `<integration-branch>`)."
# 3. audit-trail unlock comment
addCommentToJiraIssue(PROJ-123): "Session lock released — PR #1234 merged."
```

Retaining the assignee on a completed issue is intentional: it is the at-a-glance record of who landed it. Even where the project HAS reliable auto-transition configured, the explicit `transitionJiraIssue` is cheap insurance and steps 1 and 3 still apply.

### PR closed WITHOUT merging — full release back to the queue

```
editJiraIssue(PROJ-123):
  labels:   remove "<claim-label>"
  assignee: unset
addCommentToJiraIssue(PROJ-123):
  "Session lock released — PR #1234 closed without merging; issue remains open."
# transition back to <jira-ready-status> if the issue was moved to <jira-inprogress-status> on claim
```

Here the assignee must go too: if it lingers after a failed attempt, the issue looks claimed in every operator's `assignee = currentUser()` scan and nobody picks it up next round. One field encodes both meanings — kept = credit, cleared = available.

### Released on a blocker, blocker now resolved — re-lock fresh

Releasing when you hit a blocker (upstream dependency, operator hold, missing infra) was the right call: it returned the issue to the queue honestly. When the blocker clears and you pick the issue back up, do not resurrect or edit the old lock comment — run the full claim procedure again with a fresh comment and a fresh timestamp. Staleness arithmetic reads the newest marker; a re-dated old lock is indistinguishable from tampering, and a fresh one costs nothing.

### Reconciliation sweep: lock expiry is not issue closure

`<stale-window>` expiry handles the lock **label** for crashed orchestrators, but does nothing about the underlying issue. The two lifecycles desynchronize after crashes: a stale lock can sit on an issue whose PR merged long ago. Any agent that finds one runs the full merged-PR three-step block above to reconcile — not just a label strip; the issue still needs the explicit `transitionJiraIssue` to `<jira-done-status>`.

If the stale lock belongs to a **different** operator (the marker's `operator=` accountId ≠ your own) and the PR is genuinely merged or long-closed, you may reconcile their lock — but the unlock comment must name whose lock you cleared ("Releasing stale lock held by `<prior-operator>` — PR #1234 merged <date>."). Silent cross-operator state mutation corrupts the audit trail.

### Capacity collapse: release PR-less locks

When sub-agent capacity dies mid-flight (org usage limits, mass crashes), all concurrent agents fail near-simultaneously, leaving a mix of opened PRs and orphaned locks. As part of recovery: stop dispatching, then release every lock you hold whose issue has **no open PR** — those locks would otherwise block the queue until expiry. Locks with open PRs stay; the PR keeps them active by definition. (See the orchestrating-slots skill for the resume scheduling.)

## Multi-operator etiquette

- **Never assign another operator's account to your work.** It scrambles their `assignee = currentUser()` view and their slot math.
- **Never manually merge or close another operator's PRs.** Where every PR opens with auto-merge armed (see the driving-prs-to-merge skill), the merge fires when CI greens; manual intervention bypasses their merge discipline and races their orchestrator's transition-on-merge follow-ups. If your project lacks auto-merge, the rule restates as: only the dispatching operator's side merges their own PRs.
- **Never force-push to another operator's branch.** Same ownership boundary.
- **Peer review crosses operators freely; merging does not.** Reviewing a PR dispatched by another operator is fine and welcome: the PR keeps their assignee, your review posts from your account, and that mismatch is by design. Just review — leave the merge to their automation.
- **Duplicate issues: the later filer yields.** Comment "Duplicate of PROJ-100 — closing in favour of that," link the two, and transition your own to `<jira-done-status>` (resolution: Duplicate). Exception: if the original is low-quality, enrich the original and close yours as the dupe — preserve the better content, not the earlier timestamp.
- **Queue backups: first noticer calls the hold.** Send a hold message in `<chat-channel>` AND post "Holding new dispatches pending queue clear" as a comment on the most-recent PR in flight. Dual-channel matters: the comment is durable and discoverable by an operator who missed the chat.
- **The comment is the record; the ping is for speed.** Routine coordination goes as comments on the relevant issue or PR — durable, searchable by other orchestrators (`comment ~ "..."`), survives operator absence. Urgent coordination (e.g. "rolling back X") gets both: the comment for the record, the `<chat-channel>` ping for latency. A ping alone leaves nothing for the other orchestrator's next scan.
- **Comments alone do not stop dispatches.** Machine pre-claim filters read labels, status, and assignees, not prose. In one observed case four explicit "do not implement" comments failed to stop a PR that broke deploys for two hours. An operator hold must be the `<hold-label>`; if you encounter a hold expressed only in comments, apply the label yourself and re-state the hold.
- **Never post `<bot-trigger>` mentions from automation.** The project's AI-mention trigger is human-only; one automated session invoking another creates runaway loops. Ideally the project enforces this with a permission deny rule on operations whose body contains the trigger — if you hit that deny, do not work around it.

## Anti-patterns (each one happened)

- Reclaiming an active lock to "speed things up."
- Assigning the other operator's account to your locked issue.
- Manually merging or closing the other operator's PRs.
- Posting `<bot-trigger>` mentions from automation to coordinate.
- Force-pushing to the other operator's branch.
- Stripping a stale label without checking whether the merged-PR transition block is owed.
- Posting lock comments with unsubstituted `<placeholders>`.
- Trusting a readiness status or label over an empty-assignee check.
- Relying on Jira's PR-merge auto-transition instead of transitioning explicitly.

## Adapting beyond Jira

On Jira via the Atlassian MCP, everything above is verbatim. On another tracker, map the three primitives: an assignee-equivalent (per-person, list-filterable), a label-equivalent (cheap queue-scan flag), and a comment-equivalent that persists an arbitrary machine-parseable string. `transitionJiraIssue` to `<jira-done-status>` becomes the tracker's resolution transition. The portable invariants are unchanged: on success record which PR resolved it and keep the operator attributed; on abandonment strip attribution entirely; the parseable marker is the canonical record.

## Token discipline: caveman for ops, humanizer for prose

This skill runs in high-volume, repetitive orchestration loops where tokens compound across many rounds and many agents. Operate in **caveman mode** (load the `caveman` skill) to cut token use on all working output — status, reasoning, slot tables, completion reports, dispatch and coordination chatter.

Caveman compresses *prose only*. It must NEVER alter machine-precise content, which stays byte-exact: lock-comment markers, the `RECON OK` / `RECON-ERROR` contract lines, JQL, `gh` / Atlassian-MCP commands, label and field names/values, `file:line` references, code blocks, and acceptance-criteria checklists. Compress the narration, never the protocol.

Durable prose a human reads later — issue/ticket bodies and PR descriptions — is the exception: write those through the `humanizer` skill (see the issue-filing skill), not in caveman.
