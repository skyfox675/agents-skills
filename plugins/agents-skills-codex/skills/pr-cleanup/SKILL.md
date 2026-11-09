---
name: pr-cleanup
description: Single-lane interval watcher that tidies up after agent PRs close — the post-merge janitor lane of a multi-agent fleet. Acts ONLY on closed PRs — deletes merged local branches, removes spent worktrees, closes the linked GitHub/Jira issue on merge, and releases the claim lock. Critical when PRs land on an integration branch (not the repo default), because GitHub then does NOT auto-close "Closes #N" issues. A PR closed WITHOUT merging leaves its issue open and re-dispatchable (lock released but issue not closed). Loops on an interval ("/loop <interval> start"). Use when running a cleanup lane, when merged issues stay open, when local disk/worktrees pile up, or when a dead dispatch leaks a lock.
---

# PR Cleanup Watcher

One job: **tidy up after PRs close.** When `<integration-branch>` is not the repo's default branch, GitHub does **not** auto-close `Closes #N` issues (the PR lands off the default branch), so closure is manual. Reclaim local disk, close the linked issue, release the lock. Nothing else.

This skill builds on the lock-release protocol in the issue-locking skill (`gh-issue-locking` for GitHub, `jira-issue-locking` for Jira) and the worktree/branch hygiene in `dispatching-subagents`. It adds the **single-lane watcher loop** and the **merged-vs-abandoned close-out split**.

## Project bindings

Project-agnostic; the adopting project defines these in its own CLAUDE.md. Used here:

| Placeholder | Meaning |
|---|---|
| `<owner>/<repo>` | GitHub repository slug |
| `<integration-branch>` | Branch PRs target; if it is NOT the repo default, `Closes #N` does not auto-close — closure is manual |
| `<default-branch>` | The repo's default branch (GitHub only auto-closes issues for PRs merged into this) |
| `<worktree-dir>` | Where feature branches live on disk (see `dispatching-subagents`) |
| `<claim-lock>` | The active-claim marker — a label (`agent-claimed`) + assignee on GitHub, the equivalent field on Jira (see the issue-locking skill) |
| `<tracker-key>` | Linked tracker reference convention (a GitHub `#N`, a Jira issue key) |

## The watcher model

A **single-lane, interval-driven loop** — one concern, scanned end-to-end every tick (`/loop <interval> start`). Distinct from the N-slot event loop in `orchestrating-slots` and the one-shot `pr-rescuer`. One watcher per lane; lanes do not cross.

This lane is light and read-mostly — cleanup is bounded shell + tracker API. Run it on the workhorse tier and delegate noisy scans (branch lists, worktree audits) to the cheap tier (`caveman:cavecrew-investigator`, or a fixed command parsed), keeping output compressed. It writes no application code, so there is no fix-sub-agent slot count here.

## Lane (do not cross)

You OWN: deleting merged local branches, removing spent `<worktree-dir>/*` worktrees, closing linked issues on merge, releasing the `<claim-lock>` (removing the claim marker + clearing assignee).

You do NOT touch: dispatching issues (the dispatch lane — `dispatching-subagents` / `orchestrating-slots`), CI/conflicts/queue (the `pr-checks` lane), open review threads (the `pr-comments` lane), deploy/infra health (a deploy lane, if your fleet runs one). Act on **closed PRs only** (MERGED or closed-unmerged) — never on open PRs, and never force a merge.

## Each loop tick

**Agent PR (shared definition across lanes):** a **closed** PR — merged OR closed-unmerged — whose author OR assignee = your login (`gh api user --jq .login`). Scope to YOUR login only; never clean another operator's branches/worktrees/issues.

1. Find recently closed agent PRs not yet cleaned (both MERGED and closed-unmerged).
2. **MERGED** → full close-out (see the issue-locking skill's close-on-merge protocol): close the linked issue (`Closes #N`) and/or transition the Jira issue to its done state, remove the `<claim-lock>` claim marker, clear the assignee, post a brief closing note.
3. **Closed-unmerged (abandoned PR)** → release the lock so the issue is re-dispatchable: remove the claim marker, clear the assignee, post a note that the PR closed without merging. **Do NOT close the issue — leave it open.** This is the backstop for a dispatch that opened a PR then died: the lock is freed but the work is still tracked.
4. **Local cleanup** (either case): delete the closed branch, `git worktree remove` the spent worktree under `<worktree-dir>`, prune.
5. **Salvage caution:** before deleting any worktree/branch, confirm it belongs to a closed PR and not to in-flight work — a parallel actor may own it (see *Stalled-agent recovery* in `dispatching-subagents`). When unsure, skip and report; do not delete.

## Why this lane exists (the auto-close gap)

GitHub auto-closes an issue from `Closes #N` **only when the PR merges into `<default-branch>`**. Fleets that integrate on a separate `<integration-branch>` never trigger that — so without this lane, merged issues stay open, claim locks go stale, and the dispatch lane re-picks zombie issues that are already done. Closing on merge is therefore mandatory here, not optional. (Same reasoning as the close-on-merge sweep in `orchestrating-slots`; this lane is the dedicated watcher form of it.)

## Token discipline: caveman for ops, humanizer for prose

This lane runs in a repetitive loop. Operate in **caveman mode** (load the `caveman` skill) for working output. Delegate noisy scans (branch lists, worktree audits) to the cheap tier and parse a fixed command's output rather than reading it whole.

Report per tick: `closed N (merged M / abandoned A), issues closed: #x, locks released: #y, branches/worktrees removed: K`.

Caveman compresses *prose only* — never machine-precise content: `gh`/`git`/tracker commands, label and field names, the `<claim-lock>` markers, `<tracker-key>` references stay byte-exact. The closing comment a human reads is the exception: write it normally, through the `humanizer` skill.

## Stop conditions

Nothing closed-and-uncleaned → `nothing to clean` and end the tick. The loop re-fires on its interval.
