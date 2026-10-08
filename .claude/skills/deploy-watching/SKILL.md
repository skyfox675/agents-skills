---
name: deploy-watching
description: Single-lane interval watcher that keeps the integration environment's deploys healthy by fixing FORWARD — the deploy-health lane of a multi-agent fleet. Each tick it reads the newest deploy run, locates the red (deploy step vs post-deploy smoke), classifies it transient (concurrent-deploy state-lock race, CI-infra blip, known smoke transient) or real (deterministic IaC error, ordered co-deploy race, regression from a merged commit, contention inside the shared environment), re-runs the former, and mints a forward-fix PR for the latter that preserves the offending commit's intent — never a revert, never a skipped test. Loops on an interval ("/loop <interval> start"). Use when running a deploy lane, when the dev/staging deploy went red after a merge, when deciding whether a red deploy needs a re-run or a code fix, when the environment may be running stale code, or when `pr-checks` hands over a failure rooted in the integration branch rather than a PR's diff.
---

# Deploy Watching

One job: **keep the integration environment's deploys healthy by fixing forward.** A failing deploy is diagnosed and repaired, not rolled back. The fix keeps whatever the offending commit shipped and makes the deploy healthy again. Nothing else.

This skill builds on `driving-prs-to-merge` (PR mechanics, the transient-vs-real ladder, force-push discipline) and pairs with `ci-flake-hunting` (the instability lane). Where a "make it green" instinct conflicts with the fix-forward rule, this skill wins.

## Project bindings

Project-agnostic; the adopting project defines these in its own CLAUDE.md.

| Placeholder | Meaning |
|---|---|
| `<owner>/<repo>` | GitHub repository slug |
| `<integration-branch>` | Branch merges land on, and the branch the deploy follows |
| `<deploy-workflow>` | The workflow that deploys `<integration-branch>` to the shared environment |
| `<deploy-step>` | The job/step that actually applies infrastructure and code (IaC apply, release, migrate) |
| `<smoke-jobs>` | Post-deploy verification jobs that run against the live environment |
| `<local-gate>` | The full local verification command CI mirrors (lint + typecheck + tests) |
| `<transient-ledger>` | Where known transient deploy/smoke signatures are recorded; absent → degrade to "re-run once on the same SHA" |

## The watcher model

A **single-lane, interval-driven loop** (`/loop <interval> start`), like the `pr-checks` lane but over deploy runs rather than PRs. Singleton: two deploy watchers re-run and fix the same red twice.

**Slots = max concurrent fix sub-agents in flight — NOT a cap on runs watched.** Look at every relevant deploy run each tick; queue extra fixes if more break at once than you have slots. Default **1** for this lane. A `slots=N` token in the start prompt overrides.

**You orchestrate; you do not diagnose-by-editing.** Delegate per `MODEL-DEFAULTS.md`:

- **Read-only log trawl, locate, classify** → the cheap tier (`caveman:cavecrew-investigator` or a cheap-tier sub-agent). Deploy and smoke logs are huge; keep them out of your context.
- **Code edit, ≤2 files, scope obvious** → `caveman:cavecrew-builder`. It has no Bash, so it cannot run tests or open a PR: investigator locates → builder edits → a Bash-capable step (you, or a workhorse sub-agent) verifies and opens the PR.
- **Anything bigger** (3+ files, cross-cutting, needs tests run to diagnose) → a workhorse sub-agent, which may delegate further on the same rules. **Never the cheap tier for code.**
- **Premium tier** only on explicit operator instruction or an `agent-model:` label — never self-escalated.

**Sub-agent refusal fallback.** A sub-agent can die on a false-positive safety classification when the fix touches security-adjacent code (malware scanning, upload/presign paths, auth). Narrow the brief so it names less of that surface, split the security-adjacent part into its own small dispatch, or do the fix yourself in a worktree — you are the Bash-capable verify-and-PR step anyway.

## Lane (do not cross)

You OWN: health of `<deploy-workflow>` on `<integration-branch>` — the deploy step, migrations/bootstrap, `<smoke-jobs>` — plus post-merge regressions on `<integration-branch>`. `pr-checks` hands you any PR failure rooted in a broken base rather than that PR's own diff.

You do NOT touch: dispatching feature issues (the `pr-dispatcher` lane), a given open PR's checks and conflicts (`pr-checks`), review threads (`pr-comments`), merged-PR cleanup (`pr-cleanup`), slow-but-green jobs (`ci-speed-hunter`). Per-PR preview environments are not this lane unless the project says otherwise — `driving-prs-to-merge` covers them. Notice one → ignore it.

**Flake vs deploy contention.** A test that is flaky in isolation belongs to `ci-flake-hunter`. Contention *inside the shared deployed environment* — parallel smoke shards colliding on one shared identity, queue, or channel under a merge burst — is a real defect of the deploy pipeline and stays here.

## Hard rules

- **Fix forward, never revert.** No `git revert`, no rollback of a merged change.
- **No masking.** No `--no-verify`, no `--admin`, no skip-labels, no stubbed-out behaviour, no timeout bump without evidence a longer wait catches something that was actually coming.
- **Preserve intent.** The fix keeps the functionality the offending commit shipped. Mend it so the original goal and a healthy deploy both hold.
- **Normal PR flow.** Fresh branch off `origin/<integration-branch>`, hooks intact, `<local-gate>` green, the project's `do-not-rebase` convention honoured. You may edit CI/workflow config when that is the genuine fix.
- **Never arm auto-merge yourself.** `pr-comments` arms after review; arming early races the review bot.

## Each loop tick

1. **Pick the run.** `gh run list --repo <owner>/<repo> --workflow <deploy-workflow> --branch <integration-branch> --limit 5 --json databaseId,headSha,status,conclusion,createdAt`. Act on the **newest** run (head SHA closest to the `origin/<integration-branch>` tip). An older run's result stops mattering once a newer commit's run exists. If a newer superset run is still in progress, let it adjudicate and end the tick.
2. **Locate the red.** `gh run view <id> --json jobs` then `gh run view <id> --log-failed`. Which job failed decides urgency:
   - **Deploy-step red** → the environment may be running old code. Urgent.
   - **Smoke-job red** → the deploy landed; only verification failed. This holds even when the smoke job's own plumbing failed (artifact download, setup).
3. **Classify** (table below). Transient → `gh run rerun <id> --failed`, open no PR, note it.
4. **Real** → dispatch the fix per *The watcher model*, open the PR (assigned to your login, no auto-merge), and **hand off**. `pr-checks` drives CI, `pr-comments` handles threads and arms. Do not drive it to green yourself.
5. **Confirm recovery** once the fix has merged and a new deploy has run. Only then close the incident.

## Transient vs real

**Re-run first** when the signature is environmental. **The tie-breaker:** the same signature repeating on a re-run of the **same SHA** is real.

| Signature | Bucket | Action |
|---|---|---|
| Two deploy runs started within about a minute, the later one fails acquiring the shared IaC state lock, and its apply log is near-empty | Transient — concurrent-deploy lock race | Re-run once the sibling run has finished |
| Cancelled run, CI-provider or artifact-service 4xx/5xx, package-mirror fetch failure, secret-store read 5xx | Transient — CI infra | Re-run |
| A smoke signature recorded in `<transient-ledger>`, on a commit that cannot touch that surface | Transient — known smoke transient | Re-run. If it needs 2+ re-runs, or its cadence climbs, it is no longer transient: hand the test-in-isolation case to `ci-flake-hunter`, keep the contention case here |
| Deterministic IaC error: resource already exists, immutable field changed, a create-only flag rejecting an update | **Real** | Fix the IaC. A re-run cannot clear a deterministic diff |
| Components that must deploy in order (schema before resolvers, migration before code, producer before consumer) went out together and the dependent half failed | **Real** — ordered co-deploy race | Two-phase land: ship the prerequisite first, the dependent change in a follow-up. A re-run does not fix it |
| Smoke fails on behaviour the merged commit changed | **Real** — regression, or a stale test the commit should have updated | Fix forward. Decide which side is wrong before editing |
| Smoke fails under a merge burst, then a later run self-recovers with no code change | **Real** — shared-environment contention | Self-recovery is evidence of contention, not of a fix. Root-cause it |

**Diagnosing contention.** Correlate the failing request's service logs with the platform's own metrics for the exact failure minute. Logs show whether the handler ran clean; metrics show whether the platform delivered, dropped, or errored. Logs alone cannot tell "our bug" from "the platform dropped it under concurrent load", because platforms rarely log their own fan-out or delivery step. The usual fix is isolation (temporal: run the sensitive check after the producing shards finish; or by identity), not a longer timeout.

## Merge-queue state is not a stall

A fix PR that has entered a merge queue can show **no auto-merge request** with `mergeStateStatus` `CLEAN`, then `UNKNOWN` while the queue builds the merge group. That is the queue working, not a disarm. Re-arming returns "already queued". Confirm with the `mergeQueueEntry` GraphQL query in `pr-checks` before calling anything stalled. Only `BLOCKED`, `DIRTY`, or a PR provably absent from the queue is a stall, and even then arming belongs to the PR lanes, not you.

## Token discipline: caveman for ops, humanizer for prose

Operate in **caveman** mode (load the `caveman` skill) for all working output; delegate log trawls so deploy logs stay out of your context. Report per tick:

`deploy <sha> <status>; <job> red → transient, re-ran / real → fix PR #x; recovered? y/n`

Caveman compresses prose only. `gh` commands, error signatures, run ids, and `file:line` refs stay byte-exact. Commit messages and PR bodies are normal prose, written through `humanizer`.

## Stop conditions

Newest deploy run green, or every red either re-run (transient) or carrying an open fix PR handed to the PR lanes → `deploys green` / `deploy fix in flight #x`, end the tick. The loop re-fires on its interval.
