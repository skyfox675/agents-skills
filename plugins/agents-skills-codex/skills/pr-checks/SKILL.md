---
name: pr-checks
description: Single-lane interval watcher that keeps open agent PRs green and mergeable — the CI + conflict + merge-queue medic lane of a multi-agent fleet. Watches for failing required checks, DIRTY/conflicted branches, AND merge_group (queue) failures that head checks are blind to; dispatches fixes, dequeues + drafts poison-pill PRs that drop a whole ALLGREEN group, and re-arms innocent PRs ejected by a group drop. Loops on an interval ("/loop <interval> start"). Use when running a CI/checks lane, when a PR is green on its own head yet never merges, when one bad PR stalls the entire merge queue, or when telling a real poison pill apart from a flake or an innocent ejection.
---

# PR Checks Watcher

One job: **green checks + clean mergeability.** Find failing CI, merge conflicts, and **merge-queue failures** on open agent PRs and get them fixed. Nothing else.

The critical insight this lane exists for: **head-green does NOT mean queue-green.** A PR can pass its own head checks (against an older base) yet fail the `merge_group` run that actually gates the merge. Reading only `statusCheckRollup` is blind to that whole class of failure — and that blindness is exactly how one poison-pill PR stalls the queue for hours.

This skill builds on the shared PR mechanics in `driving-prs-to-merge` (the `mergeStateStatus` table, CI transient-vs-real classification, the conflict/DIRTY cheap-first ladder, merge-queue operations, force-push discipline). It adds the **single-lane watcher loop** and the **full merge-queue health protocol** on top.

## Project bindings

Project-agnostic; the adopting project defines these in its own CLAUDE.md (the full set lives in `driving-prs-to-merge`). Used here:

| Placeholder | Meaning |
|---|---|
| `<owner>/<repo>` | GitHub repository slug |
| `<integration-branch>` | Branch PRs target and the queue merges into |
| `<required-checks>` | Names of the merge-gating CI checks (the rollup check and its inputs) and the workflow that runs them |
| `<local-gate>` | The full local verification command CI mirrors (lint + typecheck + tests) |
| `<merge-strategy>` | Allowed strategy flag — and whether a **merge queue** governs `<integration-branch>` |
| `<flake-ledger>` | Where known-flaky jobs are tracked; absent → degrade to "retry twice on same SHA" |

## The watcher model

A **single-lane, interval-driven loop** — one concern, scanned end-to-end every tick (`/loop <interval> start`). Distinct from the N-slot event loop in `orchestrating-slots` and the one-shot `pr-rescuer`. One watcher per lane; lanes do not cross.

**Slots = max fix sub-agents running at once — NOT a cap on PRs scanned.** Scan EVERY agent PR each tick; if more PRs are red/conflicting than you have slots, queue the rest for next tick — never leave a red PR unwatched. Small fixed default (≈2 for this lane), tuned to the machine; a `slots=N` token in the start prompt overrides.

**You orchestrate; you do not diagnose-by-editing or write fixes yourself.** Delegate per `MODEL-DEFAULTS.md`:

- **Anything that writes or edits code (a CI/conflict fix on a PR branch) → a workhorse sub-agent** (prefer `caveman:cavecrew-builder` for ≤2-file fixes). Never the cheap tier for code.
- **Trivial read-only shell → the cheap tier** (`gh`/`grep`/`ls`, a path lookup, `caveman:cavecrew-investigator` locating failing code). The `gh` / `gh api graphql` queue commands below you run yourself — they are cheap and you are the brain reading their output.
- **Premium tier for a sub-agent only on explicit operator instruction or an `agent-model:`/`agent-effort:` label** — never self-escalated (see `gh-issue-labels` / `jira-issue-fields`).

Run the loop on the workhorse tier. Merge-queue diagnosis (head-green ≠ queue-green, poison-pill vs flake, ejected vs never-armed, wedge detection) is the highest-attention reasoning in this lane and the one place to consider operator-gated premium escalation — never on your own.

## Lane (do not cross)

You OWN: failing required checks (`<required-checks>`), **`merge_group` (queue) CI failures, poison-pill PRs, and queue ejections**, DIRTY/conflicting PRs, branches behind `<integration-branch>`.

You do NOT touch: dispatching new issues (the dispatch lane — `dispatching-subagents` / `orchestrating-slots`), review/bot comment threads (the `pr-comments` lane), merged-PR cleanup (the `pr-cleanup` lane), deploy/infra health (a deploy lane, if your fleet runs one). Notice one → ignore, not yours.

## Each loop tick

**Agent PR (shared definition across lanes):** an open PR whose author OR assignee = your login (`gh api user --jq .login`). Scope every scan to YOUR login only; never touch another operator's PRs.

1. List open agent PRs.
2. For each, read **both layers — they are different signals:**
   - **Head checks**: `gh pr view <PR#> --json statusCheckRollup,mergeStateStatus,autoMergeRequest`.
   - **Queue / merge_group state**: see *Merge-queue health* below. Skipping this layer is the blind spot that lets one poison-pill PR stall the whole queue.
3. **Failing head check** → read the failing JOB's raw log (not the summary), classify transient vs real per `driving-prs-to-merge`. Dispatch a workhorse sub-agent to fix on the PR branch; push; let CI re-run. Never `--admin`, never `--no-verify`, never skip-label past a real failure.
4. **Merge conflict / behind `<integration-branch>` / `UNMERGEABLE` queue entry** → sync by **merge, not rebase** (`git merge origin/<integration-branch>`) when the project's pre-push hook rejects rebased PR branches and these PRs carry `do-not-rebase`; otherwise follow the cheap-first DIRTY ladder in `driving-prs-to-merge`. Re-push through the hook (full `<local-gate>`); never bypass.
   - **One writer per branch:** if the `pr-comments` lane is also pushing a review fix to this branch, don't push concurrently — re-merge `origin/<branch>` before pushing, never force-push its commits.
5. **Merge-queue failures + ejections** → run *Merge-queue health* **every tick** (not only when a head check is red — this is the layer naive watchers miss).
6. **Transient failure** (cancellation, known flake in `<flake-ledger>`) → re-run the check before touching code. See the transient-vs-real classification in `driving-prs-to-merge`.
7. **Failure rooted in `<integration-branch>`, not this PR's diff** (a broken-base regression that fails every PR) → hand to the deploy/infra lane if your fleet separates deploy health; that is not this lane's to fix. Per-PR stuck/recurring → escalate per the stuck-PR triage in `driving-prs-to-merge`.

## Merge-queue health (head-green ≠ queue-green)

Only relevant when a **merge queue** governs `<integration-branch>` with **ALLGREEN grouping** (any one failure drops the whole group). Reading only head `statusCheckRollup` is blind to all of it — and that blindness is how PRs sit stuck for hours.

- The queue re-runs the full suite on a synthetic `gh-readonly-queue/<integration-branch>/pr-<N>-<sha>` branch — the PR **squashed onto current `<integration-branch>`**. A PR can pass its own head checks (against an older base) yet **fail the merge_group run** (classic: a typecheck error that only appears against the current base). The merge_group result, not the head check, is the real merge gate.
- **ALLGREEN drops the WHOLE group on any one failure.** When one PR's merge_group run fails, GitHub drops every PR in that group and clears their auto-merge enrollment. The innocent siblings sit `CLEAN` but **unqueued and unarmed** — green-looking, going nowhere. One poison-pill PR (or one bad title) stalls the entire queue.

Run all four EVERY tick:

**A. Find poison pills (failed merge_group runs).**

```bash
gh run list --repo <owner>/<repo> --event merge_group --workflow "<required-checks-workflow>" \
  --status failure --limit 10 --json headBranch,createdAt
# headBranch = gh-readonly-queue/<integration-branch>/pr-<N>-<sha>  →  that PR N failed the QUEUE run
```

A PR whose **merge_group** run **failed** (not `cancelled` — see C) is a poison pill. **Confirm real, not flake** — a flake is the *same head SHA with both a pass AND a fail*, so fetch every conclusion for that SHA (drop the status filter):

```bash
SHA=$(gh pr view <PR#> --repo <owner>/<repo> --json headRefOid --jq .headRefOid)
gh run list --repo <owner>/<repo> --event merge_group --workflow "<required-checks-workflow>" --limit 40 \
  --json headSha,conclusion --jq "[.[]|select(.headSha==\"$SHA\")|.conclusion]"
# contains BOTH "success" and "failure" → flake → gh run rerun, do NOT dequeue or code-fix
# only "failure" (no success for this SHA)  → real poison pill → proceed
```

For a real merge_group failure:

1. **Dequeue + disarm** so it stops dropping groups (`--disable-auto` alone does NOT dequeue):
   ```bash
   gh pr merge <PR#> --disable-auto
   ID=$(gh api graphql -f query='query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){pullRequest(number:$n){id}}}' -f o=<owner> -f r=<repo> -F n=<PR#> --jq '.data.repository.pullRequest.id')
   gh api graphql -f query='mutation($id:ID!){dequeuePullRequest(input:{id:$id}){clientMutationId}}' -f id="$ID"
   ```
2. Treat the merge_group failure as a real failing check → dispatch a workhorse fix on its branch. **Merge `origin/<integration-branch>` in first** — the failure is usually a semantic conflict with the current base (typecheck, mock drift) the head run never saw.
3. If it can't be fixed this tick, convert to **draft** (`gh pr ready <PR#> --undo`). A draft cannot re-enter the queue, so a sibling lane re-arming on green head checks can't re-poison. Mark ready (`gh pr ready <PR#>`) when fixed.

**B. Re-arm innocent ejected PRs.** `CLEAN` + no `mergeQueueEntry` + no `autoMergeRequest` is **not** enough — those three read identically for a PR ejected from the queue AND for a brand-new PR the `pr-comments` lane has not armed yet (review threads still pending). Arming the latter races the comments lane and can merge before review. **Discriminator:** an ejected PR has a **`merge_group` run for its _current_ head SHA** (the run cancelled/failed when its group dropped); a never-armed PR has **no merge_group history at all**. Re-arm only when ALL hold:

1. A merge_group run exists for the PR's current head SHA → it was queued, then ejected:
   ```bash
   SHA=$(gh pr view <PR#> --repo <owner>/<repo> --json headRefOid --jq .headRefOid)
   gh run list --repo <owner>/<repo> --event merge_group --json headSha,conclusion \
     --jq "[.[]|select(.headSha==\"$SHA\")]|length"     # >0 → was queued → ejected;  0 → never-armed, NOT yours
   ```
2. Head checks green AND **all review threads resolved** (never re-arm a PR with open bot/human threads — that gate is the `pr-comments` lane's).
3. Not currently in the queue, no live auto-merge.
   Then: `gh pr merge <PR#> --auto` (NO `--squash`/strategy flag — a merge queue REJECTS it and silently drops enrollment).

A PR with **zero** merge_group history is *never-armed*, not ejected → leave it to the `pr-comments` lane's initial arm-after-review; do not touch it. This rule is the **re-arm-after-ejection** case only.

**C. `cancelled` ≠ `failed`.** A `cancelled` merge_group run is collateral from another PR's group-drop (the cancel-on-destroy workflow), NOT this PR's fault. Do not treat it as a poison pill — treat the PR as an innocent ejection (rule B).

**D. `UNMERGEABLE` / wedged entries.** `mergeStateStatus`/`autoMergeRequest` lie when enqueued; the only definitive queue state is GraphQL:

```bash
gh api graphql -f query='query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){
  pullRequest(number:$n){ mergeQueueEntry{ state position enqueuedAt } } } }' -f o=<owner> -f r=<repo> -F n=<PR#>
```

`state == UNMERGEABLE` → conflict against base → dequeue + merge `origin/<integration-branch>` (step 4) or draft. Wedged: `state == AWAITING_CHECKS` with `enqueuedAt` more than ~30 min ago and no merge_group run started → dequeue → `gh pr update-branch` → re-arm. Compute the age from `enqueuedAt` with your platform's date arithmetic (e.g. on BSD/macOS `date -j -f %Y-%m-%dT%H:%M:%SZ`).

**Title-format trap:** a single bad PR title (e.g. 2+ leading caps, if the ruleset gates on title format) boots the entire merge group it shares. If a group keeps dropping with no failing test, check titles and fix via API edit: `gh api -X PATCH repos/<owner>/<repo>/pulls/<PR#> -f title='<lowercase conventional>'`.

## Token discipline: caveman for ops, humanizer for prose

This lane runs in a high-volume, repetitive loop. Operate in **caveman mode** (load the `caveman` skill) for all working output. Delegate diagnosis + edits to sub-agents (or `caveman:cavecrew-investigator` to locate failing code) so noisy logs stay out of your context.

Report per tick: `PRs N, head-red: #x (fix dispatched), conflict: #y, poison-pill: #z (dequeued+drafted), re-armed ejected: #w, queue: healthy/thrashing`.

Caveman compresses *prose only* — never machine-precise content: every `gh`/`gh api graphql` command, the queue-state names (`UNMERGEABLE`/`AWAITING_CHECKS`/`cancelled`/`failure`), `file:line` refs, code blocks stay byte-exact. Commit messages and PR-body prose: write normally, through the `humanizer` skill.

## Stop conditions

All scanned PRs green at **both** layers (head checks AND merge_group), no poison pill sitting in the queue, every innocent ejection re-armed → `queue healthy` and end the tick. The loop re-fires on its interval. Note: head-green-only is NOT a stop condition — a green head with a failing/absent merge_group result still needs action.
