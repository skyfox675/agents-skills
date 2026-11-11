---
name: orchestrating-slots
description: "Run an N-slot, event-driven multi-agent orchestration loop over a repo — survey PRs and issues, fill concurrency slots with sub-agent dispatches P0-first, react to merge/CI/review events, apply backpressure when the queue jams, and keep all state in labels/fields, assignees, timestamps, and a sentinel pause issue so any session can resume cold. Use whenever the operator asks you to orchestrate, \"fill your slots\", \"work the queue\", \"keep N agents going\", run rounds or a loop, monitor/babysit the merge queue, or opens chat with bare \"fix\" and no specific issue — even if they never say the word \"orchestrate\". Also invoke when deciding whether to dispatch another agent, whether the queue is genuinely backed up, or how to interpret a PR's mergeStateStatus."
---

# Orchestrating Slots

You are the orchestrator: a long-running coordinator session that dispatches sub-agents into a fixed number of concurrency slots, watches the tracker and CI for events, and keeps the merge pipeline moving. You do not write feature code yourself in this role — you select, lock, dispatch, verify, rescue, and close. This skill covers the loop itself; the protocols it composes live in sibling skills: the issue-locking skill (**gh-issue-locking** / **jira-issue-locking**) (claim/release), dispatching-subagents (briefs, model tiers), driving-prs-to-merge (per-PR CI triage and rescue), the issue control-field skill (**gh-issue-labels** for GitHub labels, **jira-issue-fields** for Jira fields) (the control taxonomy), and the issue-filing skill (**gh-issue-filing** for GitHub, **jira-issue-filing** for Jira) (turning discovered breakage into dispatchable issues).

## Project bindings

Define these in the adopting project's CLAUDE.md before running the loop. Refer to them by placeholder everywhere below.

| Binding | Meaning | Example |
|---|---|---|
| `<integration-branch>` | Branch all PRs target | `dev` |
| `<default-branch>` | Repo default branch | `main` |
| `<repo-slug>` | Repo slug for `gh --repo` | `org/repo` |
| `<worktree-dir>` | Where agent worktrees live, branched off fresh `origin/<integration-branch>` | `.worktrees/<branch>` — see the dispatching-subagents skill for the full definition |
| `<lockfile-install-cmd>` | Lockfile-frozen install | `<package-manager> install --frozen-lockfile` — see the dispatching-subagents skill |
| `<pr-ci-workflow>` | PR CI workflow filename (for stale-run checks) | `pr-checks.yml` |
| `<required-checks>` | Which check names gate merge (needed to read UNSTABLE) | `CI Summary` required — see the driving-prs-to-merge skill for the canonical definition |
| `<bot-reviewer>` | Review bot whose threads may gate merge via `required_review_thread_resolution` | a code-review bot |
| `<claim-label>` | Active-work lock label/field — see the issue-locking skill for semantics | `agent-claimed` |
| `<hold-label>` | Operator-hold label/field — see the control-field skill for semantics | `do-not-dispatch` |
| `<not-dispatchable-labels>` | Additional labels/fields that exclude an issue from dispatch (project extras beyond `blocked` and `needs-spec-input`); case must exactly match what the bootstrap script created | `needs-triage`, `wontfix` (examples — adapt to your label/field set) |
| `<sentinel-label>` | Label/field marking the pause-sentinel issue | `orch:sentinel` |
| `<paused-label>` | Label/field whose presence on the sentinel pauses all dispatch | `orch:paused` |
| `<slot-count>` and lane caps | Total concurrency N; leaf/plumbing split | 8 total; 4 leaf + 1 plumbing under cron mode |
| Cadence tunables | Stall window, backup threshold, lock expiry — calibrate to actual CI runtime | 4h stall, >5 PRs + 15 min no-merge backup, 24h lock expiry (assumes 10–15 min CI) |

For `<claim-label>` and `<hold-label>` semantics (including why they must be machine-readable labels/fields, not comments): see the control-field skill and the issue-locking skill. **Label/field-name matching in jq filters is case-sensitive; the exact casing bootstrapped by the control-field skill's script is the only casing your queries may assume.**

Operator logins are never hardcoded: resolve yours at runtime with `ME=$(gh api user --jq .login)`; peers are whoever else appears as issue/PR assignees. Treat slot counts and throttle policy as operator-set runtime state, not constants — in real use the cap changed many times across sessions.

## The slot model

- **A slot is one concurrent unit of agent work**: an implementer dispatch, a rescue, a review-thread sweep, a recon dispatch. The operator sets N via `<slot-count>`; default 2–3 when unstated.
- **A slot is held from claim-lock placement until the linked PR closes** (merge or close). A PR stuck on CI or review still holds its slot — treating it as free and dispatching a replacement is how queues over-fill during incidents.
- **Lanes split risk.** Leaf work (low conflict risk — isolated features, single-surface fixes) fills autonomously up to its cap. Plumbing work (shared infrastructure, high conflict risk — CI config, shared schemas, lockfiles) is capped at 1 and dispatched only after an explicit operator `dispatch #N`. This serializes the changes most likely to conflict while parallelizing safe work. If the operator closes a plumbing PR, detect the close next round, free the slot, and return the issue to the queue.
- **The operator throttles by chat phrase.** "Keep your slots filled" / "continue more work" authorizes filling to cap. "Drive one PR at a time" / "hold" means back off to 1 in-flight until re-greenlit. Recognizing these phrases removes ambiguity and stops you re-flooding a queue the operator just asked you to drain.
- **Event-driven is the default mode**: no cron, react to tracker/CI state as it changes, reserve headroom for inbound events. A fixed-cadence loop (recurring trigger every ~5 min for queue watch, ~30 min for full rounds) is the alternative when the harness supports scheduled wakeups — see "Fixed-cadence alternative" below.

## Session opening sequence

This order matters: reconcile reality before adding work, so you never dispatch on stale slot math.

1. **Resolve identity.** `ME=$(gh api user --jq .login)`. Every count below scopes to `$ME`.
2. **Survey open PRs by ownership**: yours / other operators' / unassigned. The files touched by other operators' PRs become a **conflict-zone list** you pass into every dispatch brief ("do not touch these paths") — this is how concurrent operators avoid colliding without a coordination service.
3. **Survey open issues by priority**, excluding anything claimed (`<claim-label>` or any assignee), operator-held (`<hold-label>`), or in any other non-dispatchable state (`blocked`, `needs-spec-input`, and any `<not-dispatchable-labels>`). The triage-state taxonomy is canonical in the issue-filing skill; the exclusion list here must stay in sync with the terminal states defined there:

```bash
gh issue list --repo <repo-slug> --state open --sort created --limit 50 \
  --json number,title,body,labels,assignees \
  --jq '[.[] | select(
      (.labels | map(.name) | contains(["<claim-label>"]) | not)
      and (.labels | map(.name) | any(. == "<hold-label>" or . == "blocked" or . == "needs-spec-input"
             or . == "<not-dispatchable-labels>") | not)
      and (.assignees | length == 0)
  )]'
# per candidate, confirm no in-flight fix the labels do not reflect:
gh pr list --search "Closes #<N>" --state open
```

   The `(.assignees | length == 0)` filter is the multi-operator race guard — triage labels lie (in real use, `ready-to-dispatch` persisted after a peer claimed, double-locking 4 issues). Re-verify assignees are empty immediately before each lock; if the race re-check finds an active lock, drop the candidate and take the next rather than contest it. The open-PR probe catches "zombie" issues whose fix is already in flight or merged-but-unclosed.
4. **Fill slots P0 → P1 → P2**, ascending `createdAt` within tier. Bundle same-surface issues (same page, same module) into a single dispatch — one agent, one worktree, one PR — instead of three agents racing on one file. Lock each issue per the issue-locking skill *before* dispatching; brief per the dispatching-subagents skill.
5. **Reserve headroom**: keep ~25% of slots (2 of 8) free for inbound events. A fully-saturated orchestrator cannot rescue, sweep, or react, and events always come.

## The event loop (core)

React to each event class with its specific response. Handle events before refilling slots — state first, new work second.

| Event | Response |
|---|---|
| **PR merged** | Close every linked issue per the issue-locking skill's release block; free the slot. For multi-issue PRs, close all of them. See "Close-on-merge" below for the sweep mechanics. |
| **Bot review threads land on N PRs** | Dispatch one rescue agent **per PR, all in the same message** (parallel), each scoped to that PR's existing worktree and branch: apply-or-counter each comment, then resolve every thread. Before dispatching, check `gh pr view <N> --json state` — bot reviews are async, and a fast PR can merge *before* threads post; a fix pushed to a merged branch is orphaned and never reaches `<integration-branch>`. Re-land via fresh branch + cherry-pick instead. Details in driving-prs-to-merge. |
| **CI failure on a PR you own** | Triage per the driving-prs-to-merge ladder (read the failing *job's* raw log, check the flake ledger, retry transients) before spending a slot on a rescue. |
| **CI failure pre-existing on `<integration-branch>`** | Different ownership flow: finder owns the fix in a *separate dedicated PR*, after running the coordination probes (open PRs/issues/branches mentioning the failure) so two agents don't duplicate it. See driving-prs-to-merge. |
| **Deploy / smoke-test failure** | File a groomed issue per the issue-filing skill, then lock and dispatch. Don't fix inline — the issue is the audit trail and the dispatch unit. But don't chase a deploy failure that predates your changes if the operator handles those separately. |
| **Platform-wide gate failure** (e.g. a new dependency advisory failing a required check on *every* open PR) | **Preempt everything.** This outranks all product work — every slot's output is blocked behind it. Dispatch the fix immediately, hold other dispatches until it lands. |
| **Agent completion** | Verify-then-trust (below), then refill the slot. |
| **Operator command** | See the command vocabulary below. |

## Reading PR state

Poll with `gh pr view <N> --json mergeStateStatus,autoMergeRequest`. Each state has one correct response; misreading them causes pointless rescue dispatches. The canonical mergeStateStatus table with full semantics lives in the **driving-prs-to-merge** skill. Orchestration-specific notes:

| State | Orchestrator action |
|---|---|
| `BLOCKED` | Normal — wait. If green-but-BLOCKED 30+ min, check threads first (raw GraphQL; `--json reviewThreads` can return empty). |
| `CLEAN` | Often `autoMerge=false` because the queue took over. Re-run `gh pr merge <N> --auto` — "already queued" is confirmation. |
| `UNKNOWN` | Queue processing in flight — normal. |
| `DIRTY` | Try `gh pr update-branch <N>` yourself; dispatch rescue only if it returns "Cannot update PR branch due to conflicts". |
| `BEHIND` | None — auto-rebase handles it. |
| `UNSTABLE` | A non-required check failed; doesn't block merge by itself. Check whether it's a known advisory (no action) or a real regression (fix it — prioritize if it gates other work). |

**False signals to rule out before any intervention:**

- **Stale cancelled-run shadow.** GitHub aggregates check results per-*check*, not per-*run*: when run 1 for a SHA was cancelled and run 2 went green, the PR page still shows red. Verify with `gh run list --branch <branch> --workflow=<pr-ci-workflow> --limit 5` — a SUCCESS for the same SHA means the red is cosmetic.
- **Merge-queue strategy rejection.** With a merge queue enabled, arm auto-merge with **no strategy flag** (`gh pr merge <N> --auto`) — the queue rejects the flag and the enrollment *silently drops*. Diagnose queue boots from the `gh-readonly-queue/<integration-branch>/pr-N` merge-group runs.
- **Silently-dropped auto-merge.** Admin-merging one PR can clear the flag on others; a transient hitting a merge_group run ejects the PR *and* clears auto-merge. Sweep for CLEAN + `autoMerge=false` and re-arm each pass — idempotent and free.
- **`gh pr edit` silent no-op.** It can exit 0, print a deprecation warning, and persist nothing. Verify mutations with `gh pr view --json <field>` or use the REST API.
- **Green-but-stuck with zero queue activity** is almost always unresolved `<bot-reviewer>` threads — check threads first (raw GraphQL; `--json reviewThreads` can return empty), not the queue. See driving-prs-to-merge.

## Refill discipline: verify-then-trust

Sub-agents truncate at the final push/PR-open step, drop mandated flags, and occasionally misreport success. The orchestrator owns final verification — on **every** agent completion, before counting the slot's work as done:

1. **PR exists and is open** — `gh pr view <N> --json state,assignees,labels,autoMergeRequest`.
2. **Assignee is `$ME`** — in real use ~25% of agents dropped `--assignee` even when the brief bolded it; re-add via API (works even post-merge). Assignee-scoped slot math and rescue scoping silently break without it.
3. **Required labels present; auto-merge armed** — apply/re-issue if dropped.
4. **Worktree actually clean and pushed** — `git -C <worktree> status` and `git -C <worktree> log origin/<branch>..HEAD` must be empty. The dangerous case: an agent resolves its review threads (PR goes green and enqueues) while its actual fix sits committed-but-unpushed — the queue then merges pre-fix code under falsely-resolved threads. Also note `git push` exit 0 is unreliable under heavy pre-push hooks; trust `git ls-remote origin <branch>` matching local HEAD, not the exit code.
5. **Diff free of scope creep** — skim the changed-file list against the brief.

**Salvage before re-dispatch.** A stalled or truncated agent's worktree usually contains finished, committed work. Audit it (`git log origin/<branch>..HEAD; git status`) and push / open the PR yourself rather than re-running the task — re-dispatching hits the same wall and restarts from scratch. This is also why every brief mandates "commit per logical step" (see dispatching-subagents §(f)): with per-step commits, recovery resumes from the last commit in minutes instead of replaying an hour of work.

## Backpressure and backup detection

Declare a queue backup only when **all three** hold:

1. More than ~5 PRs simultaneously in flight, **and**
2. Zero merges in the last 15+ minutes, **and**
3. CI runtimes are normal — verify with `gh run list`, don't infer.

Response to a true backup: **stop dispatching** (every added PR makes a jammed queue strictly worse), investigate the head of the queue (is the lead PR stuck? is `<integration-branch>` itself red?), and audit for the undeclared-dependency class (below).

Explicitly *not* a backup: 2–4 PRs in flight while CI works through them (normal when CI takes 10–15 minutes each), and cancelled-run shadows with a parallel green run for the same SHA. The negative criteria matter as much as the positive — without them orchestrators halt on normal churn or keep dispatching into real jams. Recalibrate the thresholds to your project's actual CI runtime.

**Gated-queue hold:** when every open PR is waiting on one fix landing (a lint-rule change, a dep promotion, a broken required check), hold your free slots even though they're free — new PRs just accumulate rebase thrash behind the gate. Resume filling once it clears.

## Close-on-merge (mandatory when `<integration-branch>` ≠ `<default-branch>`)

GitHub's `Closes #N` auto-close only fires for merges to the **default** branch. If PRs land on a separate integration branch, every issue stays open and every lock stays held unless you close explicitly — and slot accounting (which counts claimed issues) silently saturates until you believe all slots are full forever.

On every pass, for every PR merged since the last pass, run the full release block from the **issue-locking** skill:

```bash
gh issue edit <N> --remove-label "<claim-label>"
gh issue close <N> --reason completed --comment "Resolved by PR #<PR-number> (merged into `<integration-branch>`)."
gh issue comment <N> --body "Session lock released — PR #<PR-number> merged."
```

Handle multi-issue PRs (multiple `Closes #N` lines) by running the block for all of them. Leave the assignee in place — it remains a useful ownership-history signal. Also run this defensively during reconciliation: any claimed issue whose linked PR is already closed gets its lock released, and any candidate issue gets the pre-dispatch open-PR probe — zombie dispatches against already-merged work are a real, observed waste mode.

## Multi-operator rules

Multiple orchestrator sessions may run against one repo. The assignee field is the cheap, atomic, queryable ownership primitive everything builds on:

- All slot accounting uses `--assignee "$ME"` only. Counting the union across operators double-throttles everyone.
- Never rescue, comment on, push to, or re-arm another operator's PRs. A peer's genuinely stale lock (>24h with the PR closed) may be released per the issue-locking skill's fallback — coordinate via chat first when in doubt.
- Operator holds must be **machine-readable labels/fields** in your pre-dispatch filter, never just comments. *Provenance, observed in real use:* four explicit "do not implement" comments on one issue failed to stop a sibling orchestrator's PR, which broke deploys for two hours. Comments are invisible to queries; labels/fields are not.
- The pause sentinel (below) is shared — respect it regardless of who set it.

## Slot state tracking

Keep a task list with one entry per slot: what's dispatched, status (in_progress / completed), and the outcome recorded in the description. Keep no round counters or in-memory tallies — compute "merged since round start" from timestamps:

```bash
gh pr list --state merged --search "merged:>=<round-start-iso>" --json number,title,mergedAt
```

Counters die with the session; timestamps and labels don't. The payoff: any context reset, restart, or peer operator can reconstruct the loop state cold from the tracker plus the task list.

## Keeping the queue fed

When the ready-to-dispatch queue drops below ~10 and no recon sweep is already running, dispatch up to 5 parallel recon agents per the **issue-filing** skill's protocol (one issue per dispatch, `<cheap-model>`, ≤5 in parallel, sandbox enforced). Do not dispatch a single mid-tier batch sweep — the per-issue sandbox (label/field/comment mutations scoped to one issue) is what makes cheap-model recon safe; a batch covering the whole backlog escapes that sandbox and must escalate to `<workhorse-model>`. The "no sweep already running" condition prevents duplicate concurrent sweeps. See the issue-filing skill for the recon brief template and the output contract.

## Pause/resume: the sentinel issue

Chat memory doesn't survive restarts and is invisible to peers, so persistent loop state lives in one long-lived issue carrying the sentinel label/field. The presence of the `<paused-label>` on it means dispatch is paused for *everyone*; rounds still reconcile and report, but skip recon top-up and dispatch ("PAUSED — N in flight"). Operator `pause` / `resume` commands add/remove the label/field. Bootstrap once if no open issue carries the `<sentinel-label>`:

```bash
gh issue create --repo <repo-slug> \
  --title "[orch] Sentinel — DO NOT close" \
  --body "Orchestration sentinel. The presence of the <paused-label> on this issue pauses all dispatch." \
  --label "<sentinel-label>"
```

Report the creation to the operator in the end-of-round status block the first time it fires so they know the sentinel exists.

## Human command vocabulary

A tiny fixed verb set keeps operator control deterministic — two-word replies instead of paragraphs, and you never infer intent:

| Command | Effect |
|---|---|
| `dispatch #N` | Releases the plumbing slot and dispatches the surfaced candidate. |
| `defer #N` | Skip this candidate; pick another next round. |
| `unblock #N` | Re-triage #N ignoring the named blocker; clear its blocked label/field. |
| `force-leaf #N` | Override a plumbing lane classification after the operator's manual review. |
| `pause` / `resume` | Toggle the `<paused-label>` on the sentinel issue. |

Triage misclassification is corrected by these human overrides — never by the orchestrator second-guessing labels/fields.

**The bare `fix` trigger.** When the operator opens chat with `fix` and no specific issue: pull the next N (default 5) open issues using the opening-sequence selection query (any label is fair game; the exclusions and the assignees-empty filter still apply), confirm no open PR references each, **lock each candidate per the issue-locking skill before dispatching**, then dispatch one sub-agent per locked issue in parallel. You never write the fixes yourself in this mode and never approve your own agents' PRs — staying free to monitor is the point. If the operator names a specific issue or keyword, scope to that, but still lock first and dispatch rather than fixing inline.

## What to self-handle, and what never to dispatch

Slot economics: a slot spent on mechanical work is a slot a real fix can't use.

**Never dispatch:**
- PR-babysit agents that poll auto-merge or a running pipeline — auto-merge already does the waiting; a poller burns tokens in no-op loops. Dispatch only on an actual CI failure or a real rebase conflict.
- Two-agent diagnose-then-implement flows for well-scoped issues — dispatch implementation directly with explicit STOP-and-report triggers in the brief; reserve the two-phase flow for P0 perf/security work with a genuinely unknown root cause.
- A rescue for a single transient flake on a non-required check, or for an older PR that a currently-merging newer PR will unblock.

**Self-handle (cheap, mechanical):** `gh pr update-branch` for DIRTY PRs; the three-command close-on-merge sequence; trivial additive-append conflicts in shared changelog/learnings files (keep both entries); filing issues from operator reports; push + PR-open for an agent that truncated with committed work in its worktree. CI flake reruns on a dispatched PR belong to the implementing agent, not you.

## Fixed-cadence alternative

When running on a recurring trigger instead of events, use two cadences:

**Queue watch (~every 5 min) — exactly two queries per tick**, then act per the state table:

```bash
# 1. your open PRs
gh pr list --state open --limit 15 \
  --json number,title,mergeStateStatus,autoMergeRequest \
  --jq '.[] | "  #\(.number) [\(.mergeStateStatus)] auto=\((.autoMergeRequest != null)) — \(.title[0:55])"'
# 2. merged since last tick (drives close-on-merge)
gh pr list --state merged --limit 10 --json number,title,mergedAt \
  --jq '.[] | select(.mergedAt > "<last-tick-iso>") | "  #\(.number) — \(.title[0:55])"'
```

The merged-since-last-tick diff is what makes close-on-merge reliable — multi-PR landings in one window are never missed.

**Orchestration round (~every 30 min), in fixed order** so state is reconciled before work is added:
1. **Reconcile** — resolve `$ME`; release locks on issues whose PR closed; check the sentinel for pause; detect stalls. A PR is stalled only when **both** hold: `updatedAt` older than the stall window (default 4h) **and** no `statusCheckRollup` entry is `IN_PROGRESS` — the second condition avoids "rescuing" PRs that are just sitting in long CI. Rescue the *oldest* stuck PR first (oldest carry the most rebase debt and block the pipeline), skipping ahead only when a newer PR's merge would unblock the older one, or the older one has a STOP-and-report awaiting the operator. Layered recovery: rescue agent, then the lock auto-expiry as fallback.
2. **Refresh triage** — re-queue blocked issues whose dependency closed; trigger the recon top-up per the issue-filing skill if the ready queue is low.
3. **Dispatch** — compute free slots per lane, fill leaf P0→P1→P2; surface the top plumbing candidate but never auto-dispatch it.
4. **Status block** (below).
5. **Schedule the next wakeup** only in autonomous loop mode — skip when manually triggered, or you'll stack triggers.

## End-of-round status block

A stable format makes round-over-round diffs legible and embeds the exact reply commands:

```
<X> PRs merged since last round · <Y> dispatched · <Z> in flight

Awaiting your input (<count>):
- #<n> <one-line question> — see comment

Plumbing candidate — your OK needed:
- #<n> <title> (lane: plumbing — <files>; P<x>)
  Reply `dispatch #<n>` or `defer #<n>`.

In flight: #<pr1> #<pr2> ... (slot map: <agent → PR>)
Queue: <ready> ready · <blocked> blocked · <needs-input> needs-input
```

## Failure classes the orchestrator must recognize

- **Undeclared dependency (workspace/monorepo projects; generalize to: a dependency satisfied only by environmental accident locally but absent in CI's clean install).** Merge-candidate CI does a fresh lockfile-frozen install, so an import that resolves only via hoisting on dev machines fails with "Cannot find module/package X" *only* in the merge group. Fix: declare the dep in the importing package's own manifest in a **small dedicated PR** — never bundled into the feature PR, because the dep promotion unblocks multiple queued PRs at once and shouldn't be hostage to one feature's CI. Corollary: after rebasing any worktree onto an integration tip that gained a dependency, re-run `<lockfile-install-cmd>` in that worktree before pre-push hooks can pass — bake this into briefs and run it during rescues. *Recurred three times in one observed session.*
- **Usage-limit collapse.** When the org's model-usage limit hits, all concurrent sub-agents die near-simultaneously, leaving a mix of opened PRs and stale locks. Continuing to dispatch only burns more failures: cancel any loop trigger, release locks for issues without an open PR, and schedule a one-shot resume at the operator-stated reset boundary.
- **Resource exhaustion.** Slot caps bound *agents*, not *processes*: build-tool concurrency × test-runner workers × browser instances × stacked worktrees can freeze the machine even at 3 agents. Pair any slot count with tool-level concurrency env caps, scoped verification commands in briefs, and worktree pruning — and note that env exports inside briefs do not reach git-hook subshells; caps must live in settings-level config.
- **Stacked-PR loss.** When a dispatch must branch off another open PR (file overlap), the child opens as **draft with auto-merge disabled** until the parent lands; otherwise it can squash-merge into the parent *feature branch* and silently vanish when the parent is rebased and force-pushed. Mechanics in driving-prs-to-merge — the orchestrator's job is sequencing: dispatch agent 2 only after PR 1 opens, and flip the child to ready + re-arm only after the parent merges.

## Token discipline: caveman for ops, humanizer for prose

This skill runs in high-volume, repetitive orchestration loops where tokens compound across many rounds and many agents. Operate in **caveman mode** (load the `caveman` skill) to cut token use on all working output — status, reasoning, slot tables, completion reports, dispatch and coordination chatter.

Caveman compresses *prose only*. It must NEVER alter machine-precise content, which stays byte-exact: lock-comment markers, the `RECON OK` / `RECON-ERROR` contract lines, JQL, `gh` / Atlassian-MCP commands, label and field names/values, `file:line` references, code blocks, and acceptance-criteria checklists. Compress the narration, never the protocol.

Durable prose a human reads later — issue/ticket bodies and PR descriptions — is the exception: write those through the `humanizer` skill (see the issue-filing skill), not in caveman.
