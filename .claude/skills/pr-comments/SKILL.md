---
name: pr-comments
description: Single-lane interval watcher that drives PR review threads to resolved, then arms auto-merge — the review-thread-closer lane of a multi-agent fleet. Watches every open agent PR for AI-review-bot and human review comments, dispatches a fix sub-agent or posts a reasoned counter, resolves the thread only after the fix is pushed, and owns the INITIAL arm-after-bot-review (deliberately not done at dispatch, to avoid racing the bot). Loops on an interval ("/loop <interval> start"). Use when running a comments/review lane, when reviewed-but-unmerged PRs pile up because unresolved threads block auto-merge, when you must decide whether a PR is safe to arm yet, or to handle the race where review comments land after a PR is already queued.
---

# PR Comments Watcher

One job: **drive review threads to resolved, then arm auto-merge.** Auto-merge will not fire while any thread is open, so this lane is what unblocks reviewed PRs. Find new bot/human review comments, fix or counter, push, resolve — and only then enable auto-merge. This lane **owns the initial arm-after-review** (the dispatch lane deliberately does NOT enable auto-merge, to avoid racing the review bot). Nothing else.

This skill assumes the shared PR mechanics in the `driving-prs-to-merge` skill (thread-resolution GraphQL, `mergeStateStatus`, the async-orphan trap, force-push discipline). This skill adds only the **single-lane watcher loop** and the **arm/disarm gate** on top of it.

## Project bindings

Project-agnostic; the adopting project defines these in its own CLAUDE.md (the full set lives in the `driving-prs-to-merge` skill). Used here:

| Placeholder | Meaning |
|---|---|
| `<owner>/<repo>` | GitHub repository slug |
| `<integration-branch>` | Branch PRs target |
| `<bot-reviewer>` | AI review bot identity (if any), sync vs async, and whether the ruleset enables `required_review_thread_resolution` |
| `<bot-ack-reaction>` | The signal the bot has picked up a PR (e.g. an 👀 reaction); absence = not started yet |
| `<merge-strategy>` | Allowed strategy flag — and whether a **merge queue** is enabled (omit the flag when it is; see `driving-prs-to-merge`) |
| `<ai-mention-trigger>` | The human-only AI-action mention string (e.g. `@claude`), if any — never posted from an agent |

## The watcher model

A **single-lane, interval-driven loop** — one concern, scanned end-to-end every tick (`/loop <interval> start`). This differs from the N-slot event loop in `orchestrating-slots` (which fills mixed slots reactively) and from the one-shot `pr-rescuer` (which fixes one named PR). One watcher per lane; lanes do not cross (see below).

**Slots = max fix sub-agents running at once — NOT a cap on PRs scanned.** Scan EVERY agent PR each tick; if more PRs need fixes than you have slots, queue the rest for the next tick — never skip a PR because slots are full. Pick a small fixed default (≈2 for this lane) and tune to the machine; a `slots=N` token in the start prompt overrides.

**You orchestrate; you do not write fixes yourself.** Delegate per `MODEL-DEFAULTS.md`:

- **Anything that writes or edits code (applying a review fix) → a workhorse sub-agent** (prefer `caveman:cavecrew-builder` for ≤2-file fixes — compressed output, most review nits qualify). Never the cheap tier for code.
- **Trivial read-only shell → the cheap tier** (a `gh`/`grep`/`ls` one-liner, a path lookup, `caveman:cavecrew-investigator` locating something). Nothing that edits.
- **Premium tier for a sub-agent only on explicit operator instruction or an `agent-model:`/`agent-effort:` label** — never self-escalated (see the `gh-issue-labels` / `jira-issue-fields` skills). Counter-replies you post yourself are normal prose, written by you.

Run the loop on the workhorse tier. Judging a thread (valid fix vs reasoned counter) and the arm/disarm gate are the high-attention steps; the one place to consider operator-gated premium escalation, never on your own.

## Lane (do not cross)

You OWN: unresolved review threads (bot + human), applying or countering comment feedback, resolving threads, **and enabling auto-merge once a PR is clear**.

You do NOT touch: dispatching new issues (the dispatch lane — see `dispatching-subagents` / `orchestrating-slots`), CI failures / merge conflicts / merge-queue health (the `pr-checks` lane), merged-PR cleanup (the `pr-cleanup` lane), deploy/infra health (a deploy lane, if your fleet runs one). Notice one → ignore it.

**One exception, by ownership:** re-arming auto-merge after a **merge-queue ejection** belongs to the `pr-checks` lane (it owns queue health). If an already-reviewed PR loses auto-merge because a group-drop ejected it, that is a queue event — do NOT treat a dropped-after-ejection auto-merge as an unresolved-thread problem.

## Each loop tick

**Agent PR (shared definition across lanes):** an open PR whose author OR assignee = your login (`gh api user --jq .login`) — opened by a sub-agent this operator dispatched. Scope every scan to YOUR login only; never touch another operator's PRs.

1. List open agent PRs. For each, list unresolved review threads via the GraphQL query in `driving-prs-to-merge` (`gh pr view --json reviewThreads` can return EMPTY even when threads exist — use raw GraphQL). Treat `<bot-reviewer>` threads identically to human threads.
2. For each unresolved thread:
   - **Valid** → dispatch a workhorse sub-agent to apply the fix on the PR branch (prefer `caveman:cavecrew-builder` for ≤2-file fixes).
   - **Wrong / out of scope** → post a reasoned counter-reply (verify before agreeing or refusing — no performative agreement, no reflexive dismissal).
   - **One writer per branch:** if the `pr-checks` lane is also pushing a CI fix to this same branch, do not push concurrently. Re-sync (`git merge origin/<branch>`) before pushing; if HEAD moved under you, merge onto it — never force-push another lane's commits.
3. **Resolve the thread ONLY after the fix is pushed** (or the counter is posted and stands). Order is strict: push first, confirm pushed (`git log origin/<branch>..HEAD` is empty), then resolve. Never resolve a thread whose fix is still local/uncommitted — that merges pre-fix code under falsely-resolved threads.
4. Also read the **PR body summary**, not just threads — some bots put their full priority list / security findings only there, and the body does not gate merge (see the async-orphan / threads-are-a-subset traps in `driving-prs-to-merge`).

## The arm/disarm gate (the race fix)

Enable auto-merge only when **BOTH** hold:

- **The review bot has actually reviewed the PR** — it posted its review / comments or an explicit no-issues verdict. If `<bot-reviewer>` has NOT yet reacted (no `<bot-ack-reaction>`, no comments, no review), do **NOT** arm — wait for it. Arming before the bot reviews is exactly the race being killed: comments arriving after the PR is queued.
  - **Timeout escape:** if a small fixed grace window (≈5 min) has elapsed since PR-open (or since the last push that would re-trigger review) AND the bot still shows no reaction, assume it is not coming and **arm anyway**. Do not wait indefinitely on a bot that never reacts.
- **All review threads are resolved** (bot + human), no open requested-changes.

When both true: `gh pr merge <PR#> --auto <merge-strategy>` (merge queue active → omit the strategy flag, or the queue silently drops enrollment — see `driving-prs-to-merge`).

**After arming, keep watching the PR.** A late bot/human comment can still land once the PR is already queued — the original race. Do NOT assume the queue holds for a new unresolved thread. If a fresh thread appears on an armed PR: `gh pr merge <PR#> --disable-auto` first, then fix → push → resolve → re-arm per this gate.

Never post `<ai-mention-trigger>` from any agent — it is a human-only trigger; one AI session invoking another creates unsupervised loops. Enforce with a permission deny rule matching the mention string.

## Token discipline: caveman for ops, humanizer for prose

This lane runs in a high-volume, repetitive loop where tokens compound across many ticks and agents. Operate in **caveman mode** (load the `caveman` skill) for all working output. Delegate code edits to sub-agents (or `caveman:cavecrew-investigator`/`-builder` for small scoped changes) so diffs and logs stay out of your context.

Report per tick: `PRs N, open threads M, fixes pushed+resolved K, countered J, auto-merge armed: #x, waiting-on-bot: #y`.

Caveman compresses *prose only* — never machine-precise content: `gh`/GraphQL commands, label/field names, the arm/disarm gate conditions, `file:line` refs, code blocks all stay byte-exact. Durable prose a human reads — counter-replies and commit messages — is the exception: write those normally, through the `humanizer` skill, not in caveman.

## Stop conditions

All threads resolved + auto-merge armed on every reviewed-or-timed-out PR → `no open threads, auto-merge armed` and end the tick. PRs still inside the grace window awaiting the bot's first reaction → leave unarmed, report `waiting-on-bot`; a later tick (or once the window passes) arms them. The loop re-fires on its interval.
