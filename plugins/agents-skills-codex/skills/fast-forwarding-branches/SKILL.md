---
name: fast-forwarding-branches
description: Keep the primary checkout's integration branch current with a safe, interval-driven `git pull --ff-only` — and alert, never improvise, when the fast-forward is refused. Because agents work in worktrees cut from the primary, a stale primary silently hands every new worktree a stale base (stale hooks, stale scripts, stale skills). A refused fast-forward ("Your local changes to the following files would be overwritten", "Not possible to fast-forward") means someone left work in the primary or the branch diverged — that is an anomaly to report, never to stash, reset, rebase, or merge away. Use whenever running the branch-ff lane, keeping a local checkout in sync on a loop, or deciding what to do when a pull is blocked by local changes or divergence.
---

# Fast-forwarding the primary checkout

One job: **keep the primary checkout's integration branch at the remote tip, safely, on a loop.** Fast-forward when it is clean; report loudly and change nothing when it is not.

## Why this lane exists (it explains every rule below)

Agents work in **worktrees** cut from the primary checkout. Everything a fresh worktree inherits — git hooks, repo scripts, CI config, the skills and agents themselves — comes from the primary's branch. So a primary that has drifted a week behind hands *every* newly-created worktree a stale base, and the staleness is invisible until something breaks oddly. One cheap `pull --ff-only` per tick keeps the base honest.

The second half matters just as much. Because agents are supposed to be in worktrees, **the primary checkout should normally be clean.** If a fast-forward is refused because local changes would be overwritten, that is not a routine condition to work around — it means uncommitted work is sitting in the primary. Clobbering it would destroy someone's work. So the refusal is the *product* of this lane: surface it, and stop.

## Project bindings

Project-agnostic; the adopting project defines these in its own CLAUDE.md.

| Placeholder | Meaning |
|---|---|
| `<integration-branch>` | The branch the primary checkout is expected to sit on (e.g. `main`) |
| `<remote>` | The remote to pull from (almost always `origin`) |

## The tick — run exactly this

Safe by construction: `--ff-only` never rewrites, merges, or clobbers anything — it refuses instead. The branch guard leaves a primary that is on some other branch completely alone. Run this from anywhere inside the repo (the primary checkout or any worktree — it resolves the primary itself):

```sh
PRIMARY="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"
BRANCH="$(git -C "$PRIMARY" rev-parse --abbrev-ref HEAD)"

if [ "$BRANCH" != "<integration-branch>" ]; then
  echo "ff tick: skipped — primary is on '$BRANCH', not <integration-branch>"
else
  BEFORE="$(git -C "$PRIMARY" rev-parse --short HEAD)"
  git -C "$PRIMARY" pull --ff-only <remote> <integration-branch> 2>&1 | tail -8
  AFTER="$(git -C "$PRIMARY" rev-parse --short HEAD)"
  echo "ff tick: $BEFORE -> $AFTER"
fi
```

Never substitute a bare `git pull` (it can merge), `pull --rebase`, `reset`, `checkout -f`, or `clean`. The only mutation this lane is ever allowed to make is a fast-forward that git itself judged safe.

## Decision table — match the output, do exactly the action, nothing else

| Output contains | Meaning | Action |
|---|---|---|
| `Already up to date.` | Primary is already at the tip. Healthy no-op. | Report `ff tick: up to date (<sha>)`. Done. |
| `Fast-forward` / `Updating <old>..<new>` | A real fast-forward landed. | Report `ff tick: fast-forwarded <old>..<new>`. Done. |
| `skipped — primary is on '<branch>'` | Primary is parked on another branch. | Report the skip. Done — this is not an error, and you never switch branches to "fix" it. |
| `Your local changes to the following files would be overwritten by merge:` | **Uncommitted work is sitting in the primary.** | **ALERT.** Report the blocked tick plus the verbatim file list. Change nothing — no stash, no checkout, no reset. Done. |
| `cannot pull with rebase` / `You have unstaged changes` | Same class: a dirty primary. | **ALERT** exactly as above. Change nothing. |
| `fatal: Not possible to fast-forward, aborting.` | The local branch has commits the remote does not — it has **diverged**. | **ALERT.** Report that the primary has diverged and name the commit count (`git -C "$PRIMARY" log --oneline <remote>/<integration-branch>..HEAD`). Never rebase or merge to reconcile it. Done. |
| `Could not resolve host` / `unable to access` / `Connection refused` | Transient network. | Report `ff tick: network unreachable — retry next tick`. Done. No action. |
| `There is no tracking information` / `no such ref` | Branch has no upstream, or the remote branch is gone. | **ALERT** with the exact message. Change nothing. Done. |
| Anything else | Unknown state. | **STOP. Do not improvise.** Report the command output verbatim and hand off to the operator. |

## Hard rules

- **Never resolve a block yourself.** No `git stash`, `reset`, `checkout -f`, `clean`, `rebase`, `merge`, or `push --force` — ever, under any output. The uncommitted work in the primary belongs to a human; destroying it is far worse than a stale branch. Alert and stop.
- **Never touch worktrees.** Agents are actively working in them. This lane's blast radius is exactly one directory: the primary checkout, and only when it is on `<integration-branch>`.
- **Never switch branches.** A primary parked on another branch is a skip, not a problem to fix.
- **Never improvise a git command** that is not in the tick block or the decision table. If the output matches no row, stop and report it verbatim.
- **Ticks are idempotent.** An already-current primary is a no-op costing under a second, so never skip a tick because "it probably already ran" — the check *is* the point.

## Scheduling

A loop lane: the operator starts it with `/loop <interval> start` and each firing is one tick. Cadence is the operator's dial; nothing about the behaviour changes with the interval. A few minutes to an hour all work — the tick is cheap, and the cost of a stale primary grows with how often new worktrees are cut.

## Token discipline (caveman)

Load the `caveman` skill. One line per tick, nothing more:

- `ff tick: up to date (<sha>)`
- `ff tick: fast-forwarded <old>..<new>`
- `ff tick: skipped — primary on '<branch>'`
- `ff tick: network unreachable — retry next tick`
- `ff tick: BLOCKED — <one-line reason>` **followed by the verbatim git output** (the only case where more than one line is correct).

Caveman compresses prose only — git commands, branch names, SHAs, and the blocked-file list stay byte-exact. Never paraphrase the git output on a block; the operator needs the literal file list.

## Stop conditions

Primary up to date, fast-forwarded, or legitimately skipped → report the one-liner and end the tick. The loop re-fires on its interval. A BLOCKED tick does **not** stop the loop — keep reporting it each tick until the operator clears the primary, because a repeating alert is the signal that the work is still stranded there.
