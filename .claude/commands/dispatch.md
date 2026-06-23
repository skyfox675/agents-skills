---
description: Start an event-driven orchestration session — fill N concurrency slots with sub-agent dispatches, split across dev slots (new issues), rescue slots (CI failures, review threads, stuck PRs), and flex slots (dev work that yields to incidents). Example — /dispatch 8, or /dispatch dev:5 rescue:1 flex:2
argument-hint: <total-slots> | dev:<n> rescue:<n> flex:<n>
allowed-tools: Bash(gh issue list:*), Bash(gh issue view:*), Bash(gh pr list:*), Bash(gh pr view:*), Bash(gh pr checks:*), Bash(gh api user:*), Bash(gh label list:*), Bash(gh run list:*)
---

# /dispatch — fill orchestration slots

> Operate in caveman mode (load the `caveman` skill) — orchestration is high-volume and tokens compound across rounds. Keep `gh` commands, labels, lock markers, and slot/PR numbers byte-exact; compress only the narration.

Arguments: `$ARGUMENTS`

Parse them as:

- A single number `N` is the **total slot count**. Default split: rescue = max(1, ⌊N/8⌋), flex = ⌊N/4⌋, dev = the remainder. `/dispatch 8` → dev:5 rescue:1 flex:2.
- `dev:<n>`, `rescue:<n>`, `flex:<n>` tokens (anywhere in the args) set counts explicitly and always win over the derived split. Any subset is fine — unallocated remainder from a total goes to dev. `/dispatch 8 rescue:2` → dev:4 rescue:2 flex:2.
- No arguments is an error: ask the operator for a slot count rather than guessing — slot capacity is operator policy (see orchestrating-slots).

**Slot semantics** (full protocol in the **orchestrating-slots** skill — read it before acting):

- A **dev slot** runs a sub-agent implementing a groomed issue from the queue. Dedicated: it refills with dev work when freed.
- A **rescue slot** is held for inbound incidents: CI failures on owned PRs, bot-review thread sweeps, DIRTY/stuck PRs, deployment or smoke-check failures. Dedicated: never backfill rescue capacity with dev work just because it's idle — rescue capacity exists so a queue incident never waits behind feature work.
- A **flex slot** works in both directions: fill it with dev work when the pipeline is healthy, but it is the first capacity reclaimed when incidents exceed rescue capacity — preempt its dev dispatch only if the work isn't yet near a push (otherwise let it finish, then convert). Flex slots are also the first to go idle under backpressure.
- A slot is held from claim-lock placement until the linked PR closes. Existing in-flight work you own counts against today's slots — reconcile before dispatching anything new.

## Steps

1. **Resolve identity and reconcile.** `ME=$(gh api user --jq .login)`. Survey open PRs by ownership: yours (each holds a dev or flex slot already), other operators' (their files become the conflict-zone list passed into every brief — never dispatch onto them), unassigned. Release any stale claims per the issue-locking skill (gh-issue-locking / jira-issue-locking).

2. **Fill rescue slots first** if rescue-type work already exists: owned PRs with failing required checks, unresolved bot-review threads, DIRTY state, or red deploys. These outrank new dev work — a blocked merge pipeline starves everything downstream. Overflow incidents claim flex slots next. Triage per the driving-prs-to-merge ladder before spending any slot (a flake rerun is free; a rescue dispatch is not).

3. **Fill dev then flex slots** from the issue queue: open issues sorted P0 → P1 → P2, excluding claimed, operator-held, and not-dispatchable labels (taxonomy in the issue control-field skill — gh-issue-labels for GitHub, jira-issue-fields for Jira — and the issue-filing skill — gh-issue-filing / jira-issue-filing). Bundle same-surface small issues into one dispatch — review cost is per-PR, not per-issue. For each dispatch: lock per the issue-locking skill (gh-issue-locking / jira-issue-locking), resolve model/effort per the control-field skill, write the eight-section brief per dispatching-subagents, and launch independent dispatches in the same message so they run in parallel.

4. **Hold flex (then dev) slots when the queue is gated.** If every open PR is blocked on one fix landing (a platform-wide advisory, a broken required check), dispatching more dev work only adds rebase thrash — fix the gate, hold the rest, resume filling after it clears.

5. **Track and report.** Keep one task-list entry per slot (so state survives a context reset). End with a slot table: slot #, type (dev/rescue/flex), assignment (issue/PR numbers), model, status. Then operate the event loop per orchestrating-slots — verify every agent completion (verify-then-trust) before refilling its slot, and rebalance flex slots toward whichever side (dev/rescue) is under pressure each round.

If the slot count the operator gave conflicts with what reconciliation finds (e.g. `/dispatch 4` but you already own 5 open PRs), report the discrepancy and operate at the higher of the two rather than abandoning in-flight work — slots track reality, not aspiration.
