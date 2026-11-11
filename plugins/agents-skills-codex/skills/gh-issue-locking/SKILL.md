---
name: gh-issue-locking
description: "Claim/lock/release protocol for GitHub issues worked by AI agents, with multi-operator coordination etiquette. Use whenever an orchestrator is about to claim, dispatch, or start work on an issue (lock BEFORE dispatch, always); whenever a PR linked to a claimed issue merges or closes (release the lock and explicitly close the issue — GitHub auto-close does not fire on non-default integration branches); whenever you find an issue carrying a lock label or lock comment and must decide active-vs-stale; and during any batch flow that claims multiple issues in one pass — even if the user only says \"pick up the next issue\", \"work #N\", \"fix\", \"release the lock\", or \"why is this issue still open\". Also covers bundled-issue locks, stale-lock reclaim, the multi-claim race re-check, and what to do when another operator already holds the lock."
---

# gh-issue-locking: Claim, Coordinate, Release

Multiple orchestrator sessions — run by different humans, on different machines, at the same time — work the same issue queue. Without a claim protocol, two agents silently pick up the same issue, burn duplicate work, and open conflicting PRs. This skill is the claim protocol: how to lock an issue before dispatching work, how to recognize and respect (or reclaim) someone else's lock, and how to release cleanly on every exit path.

Related skills: pick what to claim with the gh-issue-filing and gh-issue-labels skills; dispatch the work with the dispatching-subagents skill; run the surrounding loop with the orchestrating-slots skill; drive the resulting PR with the driving-prs-to-merge skill.

## Project bindings

These values are project policy, not protocol. The adopting project defines them in its own CLAUDE.md; this skill refers to them by placeholder.

| Binding | Meaning | Proven default |
|---|---|---|
| `<repo-slug>` | `org/repo` for `--repo` flags (or omit when cwd is the checkout) | — |
| `<integration-branch>` | Branch agent PRs merge into | `dev` (default branch was `main`) |
| `<claim-label>` | Repo-wide "an automation holds this" label | `agent-claimed`, color `F0E68C` — created by the gh-issue-labels bootstrap script |
| `<lock-marker>` | Stable greppable token in every lock comment | `claude-lock:` |
| `<hold-label>` | Operator-held "humans only, never dispatch" label | `do-not-dispatch` — label-name comparisons in jq filters are case-sensitive; whatever casing the bootstrap script creates is the only casing filters may assume (the bundled script creates lowercase names) |
| `<stale-window>` | Lock age threshold before reclaim is considered | 24h (tune to typical PR cycle time) |
| `<worktree-dir>` | Where agent worktrees live | see the dispatching-subagents skill |
| `<chat-channel>` | Team real-time channel for urgent pings | Slack |
| `<bot-trigger>` | The project's human-only AI-mention trigger | `@claude` |
| Operator logins | Informational roster of known operators | resolve dynamically — see below |

`<claim-label>` and `<lock-marker>` defaults carry no project semantics and can be adopted verbatim. The `<claim-label>` label itself is created by the gh-issue-labels bootstrap script — do not create it inline. If you rename either binding, rename it in every grep and snippet below — a marker that drifts from the greps makes every lock invisible to stale-detection.

## The three coordination primitives

Every claimed issue carries exactly three signals, placed together. Each serves a different consumer at a different cost; dropping any one breaks that consumer.

1. **Assignee = the operator's GitHub login.** The at-a-glance human signal. It is what `gh issue list --assignee @me` filters on, what the web UI shows as an avatar, and what other operators scan to find unclaimed work. Concurrent operators scope their slot math to `--assignee @me`; an issue with the wrong (or a lingering) assignee scrambles everyone's view.
2. **`<claim-label>` = the coarse machine lock.** Any orchestrator scanning the open queue sees "an automation is on this" from a cheap list query, without fetching N issues' comments.
3. **A lock comment with a machine-parseable HTML marker = the canonical record.** It answers who/where/when in enough detail (operator, worktree, branch, timestamp) to do staleness arithmetic and rescue work. The HTML comment is invisible in the rendered GitHub UI, so the bullet list above it duplicates the fields for humans.

The compression to remember: **the comment is the canonical record; the label is the signal; the assignee is the face.**

## Resolve operator identity dynamically

Once per session:

```bash
OPERATOR=$(gh api user --jq .login)
```

Use `$OPERATOR` everywhere: issue assignee, the `operator=` field in lock comments, PR assignee (sub-agents must self-assign the same login — see the dispatching-subagents skill), and `--assignee @me` scoping. Do not hardcode an operator roster in docs or scripts: rosters drift. One procedure file observed in practice listed a login that disagreed with the rest of its memory by one character — dynamic resolution from the auth context is the only value that cannot rot. A roster in project bindings is informational only.

## Before you claim: the pre-claim check

Run this gate immediately before every lock, even if a queue scan minutes ago said the issue was free.

1. **Hold label.** If the issue carries `<hold-label>`, stop. It is operator-held work deliberately reserved for humans. If an agent claimed one in error, stop the agent and revert the claim.
2. **Assignee must be empty.** Dispatch-readiness labels lie — in one illustrative incident a `ready-to-dispatch` label persisted after another operator claimed, producing four double-locked issues. The assignee field is the only authoritative claim gate; re-verify it is `[]` immediately before locking, because another operator may have claimed between your scan and now.
3. **Grep for an existing lock marker:**

```bash
gh issue view <N> --repo <repo-slug> --json labels,assignees,comments \
  --jq '.comments[] | select(.body | contains("<lock-marker>")) | .body'
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

Bootstrap the `<claim-label>` label via the gh-issue-labels skill's `scripts/bootstrap-labels.sh` — do not create it inline. The script uses the same color and description as the claim/release protocol expects.

Claiming is three actions that must all land — a partial lock (label without assignee, comment without label) breaks one of the three consumers and is invalid:

```bash
gh issue edit <N> --add-label "<claim-label>" --add-assignee "$OPERATOR"
gh issue comment <N> --body "$(cat <<EOF
**Agent session lock** — claimed by an automated session; do not assign to another agent.

- operator: \`$OPERATOR\`
- worktree: \`<absolute-path-to-worktree>\`
- branch: \`<branch-name>\`
- claimed at: \`<ISO-8601 UTC timestamp>\`

<!-- <lock-marker> operator=$OPERATOR worktree=<absolute-path> branch=<branch> at=<ISO-8601 UTC> -->

This lock auto-expires after <stale-window> of no PR activity. If you can confirm the session has ended, reclaim by removing the \`<claim-label>\` label AND the \`$OPERATOR\` assignee, then start work.
EOF
)"
```

The canonical marker line uses the placeholder (with the default binding this renders as `<!-- claude-lock: ... -->`):

```
<!-- <lock-marker> operator=<login> worktree=<path> branch=<branch> at=<ISO-8601 UTC> -->
```

This exact shape is the grep target. `<path>` is the `<worktree-dir>` value bound per the dispatching-subagents skill.

Three pitfalls that have each produced broken locks in practice:

- **Leave the heredoc delimiter unquoted** (`<<EOF`, not `<<'EOF'`) so `$OPERATOR` interpolates — a quoted heredoc posts a lock with a literal `$OPERATOR` and stale-detection cannot attribute it.
- **Escape backticks** (`` \` ``) inside the heredoc so they pass through as literal markdown instead of being executed as shell command substitution.
- **Substitute real values; do not post placeholders.** Agents copying the template verbatim have posted comments containing literal `<absolute-path-to-worktree>`, which breaks marker parsing and tells other operators nothing.

The lock comment is deliberately self-documenting: the expiry policy and exact reclaim mechanics are embedded in the lock itself, so a future agent or human who finds it needs no procedure file to act correctly.

## Bundled-issue locking

When one dispatch covers several issues (a lead issue plus tightly-coupled siblings fixed in the same PR), do not duplicate the full lock everywhere — duplicated worktree/branch records drift. Instead:

- **Lead issue**: full three-signal lock as above.
- **Each sibling**: label + assignee as normal, plus a short comment whose marker points at the lead:

```bash
gh issue comment <S> --body "$(cat <<EOF
**Bundled with #<lead>** — claimed as part of the same agent session; see the lock on #<lead>.

<!-- <lock-marker> bundled_with=#<lead> operator=$OPERATOR at=<ISO-8601 UTC> -->
EOF
)"
```

Anyone doing staleness arithmetic on a sibling follows `bundled_with` to the lead and evaluates that lock; release of the lead releases the bundle (run the release steps on every bundled issue).

## Batch claims: the race re-check

GitHub has no compare-and-swap, so batch claiming is optimistic-lock-then-verify. When claiming several issues in one flow (e.g. a "claim the next 5 open issues" trigger), another operator can lock the same issue between your read and your edit. So, immediately after placing each lock, re-fetch and check for active markers:

```bash
# Collect all lock-marker comments on this issue
all_markers=$(gh issue view <N> --json comments \
  --jq '[.comments[] | select(.body | contains("<lock-marker>")) | .body]')

# For each operator, consider only their NEWEST marker (ignore markers older
# than the most recent "Session lock released" comment for that operator).
# If more than one operator has an active marker (placed within the current
# race window), earliest at= timestamp wins.
```

Earliest-`at=`-wins is a deterministic tiebreak both parties compute independently — no negotiation channel needed. Active-marker comparison: consider only the newest marker per operator and ignore any marker whose `at=` timestamp predates the most recent "Session lock released" comment from that operator (released locks leave their comment in place but are no longer active).

The re-check is required **only** in multi-claim flows; for a single-issue claim the read-then-edit window is short enough that the race is negligible, and adding the ceremony everywhere is waste. Skipping it in batch flows lets two operators silently double-claim.

## Stale locks: polite reclaim

When the pre-claim check says STALE:

```bash
gh issue edit <N> --remove-label <claim-label> --remove-assignee <prior-operator>
gh issue comment <N> --body "Reclaiming stale lock from <prior-operator> (last activity <at>). Continuing work."
# then place a fresh lock with your own $OPERATOR per the standard procedure
```

Remove **both** the label and the prior assignee — each is read by a different scan, and a lingering assignee makes the issue look claimed forever. The explicit reclaim comment keeps the audit trail honest: who took over, from whom, why.

One thing reclaim cannot do: recover the prior work. The prior operator's worktree is local to their machine. Reclaim means re-dispatch fresh — do not waste time hunting for their in-progress branch.

**Never reclaim an active lock**, even to "speed things up." Recent timestamp plus an in-flight PR means another agent is working right now; reclaiming creates the exact race the system prevents. If your need is genuinely more urgent, post a comment on the issue describing the conflict — the other operator's orchestrator will surface it on its next tick — and/or ping `<chat-channel>`.

## Releasing locks

Every exit path has a release. The semantics are deliberately **asymmetric** — success keeps the assignee as credit, failure strips it for availability — and that asymmetry is load-bearing.

### PR merged into `<integration-branch>` — release AND explicitly close

GitHub's `Closes #N` keyword only auto-closes issues when the PR merges into the repo's **default** branch. If your agent PRs land on a non-default `<integration-branch>`, every issue silently stays open after its fix merges: the queue fills with phantom work, other operators re-dispatch already-solved problems, and claim labels stick around. (In production this produced zombie recon dispatches on merged work, and one session missed the explicit close nine times before the operator caught it.) The orchestrator must close explicitly, three commands in order:

```bash
# 1. release the lock label (assignee RETAINED as completion credit)
gh issue edit <N> --remove-label "<claim-label>"
# 2. close with the resolving PR recorded
gh issue close <N> --reason completed --comment "Resolved by PR #<PR-number> (merged into \`<integration-branch>\`)."
# 3. audit-trail unlock comment
gh issue comment <N> --body "Session lock released — PR #<PR-number> merged."
```

Retaining the assignee on a completed issue is intentional: it is the at-a-glance record of who landed it. If your project merges straight to the default branch, the explicit close is unnecessary (auto-close fires) but steps 1 and 3 still apply.

### PR closed WITHOUT merging — full release back to the queue

```bash
OPERATOR=$(gh api user --jq .login)
gh issue edit <N> --remove-label "<claim-label>" --remove-assignee "$OPERATOR"
gh issue comment <N> --body "Session lock released — PR #<PR-number> closed without merging; issue remains open."
```

Here the assignee must go too: if it lingers after a failed attempt, the issue looks claimed in every operator's `--assignee` scan and nobody picks it up next round. One field encodes both meanings — kept = credit, stripped = available.

### Released on a blocker, blocker now resolved — re-lock fresh

Releasing when you hit a blocker (upstream dependency, operator hold, missing infra) was the right call: it returned the issue to the queue honestly. When the blocker clears and you pick the issue back up, do not resurrect or edit the old lock comment — run the full claim procedure again with a fresh comment and a fresh timestamp. Staleness arithmetic reads the newest marker; a re-dated old lock is indistinguishable from tampering, and a fresh one costs nothing.

### Reconciliation sweep: lock expiry is not issue closure

`<stale-window>` expiry handles the lock **label** for crashed orchestrators, but does nothing about the underlying issue. The two lifecycles desynchronize after crashes: a stale lock can sit on an issue whose PR merged long ago. Any agent that finds one runs the full merged-PR three-command block above to reconcile — not just a label strip.

If the stale lock belongs to a **different** operator (the marker's `operator=` ≠ your login) and the PR is genuinely merged or long-closed, you may reconcile their lock — but the unlock comment must name whose lock you cleared ("Releasing stale lock held by `<prior-operator>` — PR #<PR> merged <date>."). Silent cross-operator state mutation corrupts the audit trail.

### Capacity collapse: release PR-less locks

When sub-agent capacity dies mid-flight (org usage limits, mass crashes), all concurrent agents fail near-simultaneously, leaving a mix of opened PRs and orphaned locks. As part of recovery: stop dispatching, then release every lock you hold whose issue has **no open PR** — those locks would otherwise block the queue until expiry. Locks with open PRs stay; the PR keeps them active by definition. (See the orchestrating-slots skill for the resume scheduling.)

## Multi-operator etiquette

- **Never assign another operator's login to your work.** It scrambles their `--assignee @me` view and their slot math.
- **Never manually merge or close another operator's PRs.** Where every PR opens with auto-merge armed (see the driving-prs-to-merge skill), the merge fires when CI greens; manual intervention bypasses their merge discipline and races their orchestrator's close-on-merge follow-ups. If your project lacks auto-merge, the rule restates as: only the dispatching operator's side merges their own PRs.
- **Never force-push to another operator's branch.** Same ownership boundary.
- **Peer review crosses operators freely; merging does not.** Reviewing a PR dispatched by another operator is fine and welcome: the PR keeps their assignee, your review posts from your login, and that mismatch is by design. Just review — leave the merge to their automation.
- **Duplicate issues: the later filer yields.** Comment "Duplicate of #X — closing in favour of that." and close your own. Exception: if the original is low-quality, enrich the original and close yours as the dupe — preserve the better content, not the earlier timestamp.
- **Queue backups: first noticer calls the hold.** Send a hold message in `<chat-channel>` AND post "Holding new dispatches pending queue clear" as a comment on the most-recent PR in flight. Dual-channel matters: the comment is durable and discoverable by an operator who missed the chat.
- **The comment is the record; the ping is for speed.** Routine coordination goes as comments on the relevant issue or PR — durable, greppable by other orchestrators, survives operator absence. Urgent coordination (e.g. "rolling back X") gets both: the comment for the record, the `<chat-channel>` ping for latency. A ping alone leaves nothing for the other orchestrator's next scan.
- **Comments alone do not stop dispatches.** Machine pre-claim filters read labels and assignees, not prose. In one illustrative incident, four explicit "do not implement" comments failed to stop a PR that broke deploys for two hours. An operator hold must be the `<hold-label>`; if you encounter a hold expressed only in comments, apply the label yourself and re-state the hold.
- **Never post `<bot-trigger>` mentions from automation.** The project's AI-mention trigger is human-only; one automated session invoking another creates runaway loops. Ideally the project enforces this with a permission deny rule on `gh` commands containing the trigger — if you hit that deny, do not work around it.

## Anti-patterns (each one happened)

- Reclaiming an active lock to "speed things up."
- Assigning the other operator's login to your locked issue.
- Manually merging or closing the other operator's PRs.
- Posting `<bot-trigger>` mentions from automation to coordinate.
- Force-pushing to the other operator's branch.
- Stripping a stale label without checking whether the merged-PR close block is owed.
- Posting lock comments with unsubstituted `<placeholders>`.
- Trusting a readiness label over an empty-assignee check.

## Adapting beyond GitHub

On GitHub, everything above is verbatim `gh`. On another tracker, map the three primitives: an assignee-equivalent (per-person, list-filterable), a label-equivalent (cheap queue-scan flag), and a comment-equivalent that persists an arbitrary machine-parseable string. `--reason completed` becomes the tracker's resolution field. The portable invariants are unchanged: on success record which PR resolved it and keep the operator attributed; on abandonment strip attribution entirely; the parseable marker is the canonical record. The Jira realization of this protocol is the `jira-issue-locking` skill.

## Token discipline: caveman for ops, humanizer for prose

This skill runs in high-volume, repetitive orchestration loops where tokens compound across many rounds and many agents. Operate in **caveman mode** (load the `caveman` skill) to cut token use on all working output — status, reasoning, slot tables, completion reports, dispatch and coordination chatter.

Caveman compresses *prose only*. It must NEVER alter machine-precise content, which stays byte-exact: lock-comment markers, the `RECON OK` / `RECON-ERROR` contract lines, JQL, `gh` / Atlassian-MCP commands, label and field names/values, `file:line` references, code blocks, and acceptance-criteria checklists. Compress the narration, never the protocol.

Durable prose a human reads later — issue/ticket bodies and PR descriptions — is the exception: write those through the `humanizer` skill (see the issue-filing skill), not in caveman.
