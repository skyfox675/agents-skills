---
name: driving-prs-to-merge
description: Owns the entire post-open PR lifecycle in a multi-agent GitHub repo — enabling and re-arming auto-merge, reading mergeStateStatus correctly, triaging CI failures from per-job logs, classifying transient vs real failures, resolving bot and human review threads (including the async-bot orphan trap), rescuing DIRTY/conflicted PRs, operating merge queues, handling pre-existing red CI, and dispatching fresh-context peer review. Use whenever a PR has been opened and must reach merge, a PR is stuck (green-but-not-merging, BLOCKED, DIRTY, booted from a merge queue), CI on a PR is red, auto-merge "mysteriously dropped", review threads need handling, or any agent encounters failing CI — even if the user only says "why isn't my PR merging", "CI is red", "fix this PR", or "the queue looks broken".
---

# Driving PRs to Merge

After opening any PR, the opener owns driving it to merge. No waiting for a human nudge. The loop exit condition: all required checks green AND every review thread resolved — auto-merge then fires on its own. Everything below exists to get to that state cheaply and honestly.

## Project bindings

This skill is project-agnostic. The adopting project defines these in its own CLAUDE.md; refer to them by placeholder throughout.

| Placeholder | Meaning |
|---|---|
| `<owner>/<repo>` | GitHub repository slug |
| `<integration-branch>` | Branch PRs target (may differ from the repo default branch — see "After merge") |
| `<merge-strategy>` | Allowed strategy flag (`--squash`, `--merge`, `--rebase`) — and whether a **merge queue** is enabled (changes the command, see below) |
| `<local-gate>` | The full local verification command CI will mirror (lint + typecheck + tests), ideally scoped to changed packages + dependents |
| `<worktree-dir>` | Where feature branches live on disk (see the dispatching-subagents skill) |
| `<bot-reviewer>` | AI review bot identity (if any), whether it reviews sync or async, and whether the ruleset enables `required_review_thread_resolution` |
| `<required-checks>` | Names of merge-gating CI checks |
| `<failure-catalog>` | Location of the failure-pattern catalog (maps check-name → likely cause → fix recipe → evidence PR#) |
| `<flake-ledger>` | Where known-flaky jobs are tracked (e.g. a scheduled workflow posting to a pinned issue); absent → degrade to "retry twice on same SHA" |
| `<per-pr-deploy>` | Per-PR preview-environment workflow, if any, and its **path filter** |
| `<breaking-change-labels>` | Acknowledgment labels/annotations that breaking-change gates honor |
| `<derived-artifacts>` | Generated files (lockfiles, operation manifests) + their regeneration commands |
| `<append-only-files>` | Shared append-only files (changelogs, learnings logs) that conflict trivially |
| `<ai-mention-trigger>` | The human-only AI-action mention string (e.g. `@claude`), if the repo has one |
| `<force-push-policy>` | Who may force-push feature branches (some environments permission-block sub-agents; orchestrator performs with operator authorization) |
| `<commit-convention>` | Commit message format; see the dispatching-subagents skill for the canonical definition |

## The PR-open ritual

Run all three immediately after opening, as one atomic ritual:

```bash
gh pr create --base <integration-branch> --title "<conventional title>" \
  --body "<... Closes #N ...>" \
  --assignee "$(gh api user --jq .login)"
gh pr view <PR#> --json assignees,labels   # verify assignee landed
gh pr merge <PR#> --auto <merge-strategy>   # merge queue active? OMIT the strategy flag — see below
```

If the assignee or required labels did not land, repair via the REST API:

```bash
gh api -X POST repos/<owner>/<repo>/issues/<PR#>/assignees -f "assignees[]=<login>"
gh api -X POST repos/<owner>/<repo>/issues/<PR#>/labels -f "labels[]=<label>"
```

Never use `gh pr edit` for repairs — it can exit 0, print a GraphQL deprecation warning, and persist *nothing* (observed losing a title fix and assignee, leaving a required title check red).

Why each step:

- **Self-assignment at creation** is the scoping mechanism when multiple operators/agents run concurrently: `gh pr list --assignee @me` is how each operator filters their in-flight work. Author is automatic; assignee is what the filter reads. (See the issue-locking skill (**gh-issue-locking** / **jira-issue-locking**) for the full multi-operator protocol.)
- **Auto-merge at open** means the PR merges the moment gates clear, with no babysitting.
- **Merge-queue caveat (battle-tested):** when a merge queue manages `<integration-branch>`, `gh pr merge --auto --squash` is *rejected by the queue and the auto-merge enrollment silently drops* — no error appears on the PR; it just never merges. Pass `--auto` with no strategy flag. This was the root cause of auto-merge "mysteriously dropping" across many PRs in practice.
- **Re-issue rule:** if auto-merge enrollment is rejected at open (e.g. a review requirement not yet satisfiable), it does NOT queue itself for later. Note it in the PR body and explicitly re-run `gh pr merge <PR#> --auto` once the blocker clears, or the green PR sits unmerged indefinitely. The command is idempotent — "already queued to merge" is confirmation, not an error.
- Never `--admin` past checks or required reviews — the sanctioned alternatives are `<breaking-change-labels>` or an honest stop-and-report (see "Meta-gates").

## Stuck-PR triage query

When scanning for stuck PRs, use `--assignee @me` (the ownership signal) as the primary filter. If the agent may have dropped the assignee flag, add a secondary `--author` sweep to catch assignee-dropped PRs:

```bash
gh pr list --repo <owner>/<repo> --assignee @me --state open \
  --json number,createdAt,mergeStateStatus,statusCheckRollup \
  --jq '[.[] | select(.mergeStateStatus == "DIRTY" or
        ([.statusCheckRollup[]? | select(.conclusion=="FAILURE")] | length > 0))]
        | sort_by(.createdAt) | .[] | {n: .number, age: .createdAt}'
```

## Pre-flight: local gates before any push

Run `<local-gate>` before pushing — via git hooks or manually mid-development. If a hook blocks the push, fix the issue and push again; never bypass with `--no-verify`. Bypassing converts a 30-second local catch into lint/type errors landing in CI 10 minutes after the push — the prohibition exists exactly to prevent that loop. Scope the gate to changed packages and their dependents so it stays fast.

One reliability caveat learned the hard way: with heavy pre-push hooks, `git push` exit 0 is not proof the push landed (hook rejection can surface as exit 0 in background tasks). Verify `git ls-remote origin <branch>` matches local HEAD before claiming "pushed".

## Reading PR state: the mergeStateStatus table

`gh pr view <PR#> --json mergeStateStatus,autoMergeRequest,statusCheckRollup`

| State | Means | Your action |
|---|---|---|
| `BLOCKED` | Waiting on a required check (most commonly CI in progress). Normal. | Wait. If green-but-BLOCKED for 30+ min with zero queue activity, check **review threads first** — it is almost always unresolved threads, not a broken queue. |
| `CLEAN` | All required checks green; eligible to merge or actively in the queue. Often shows `autoMerge=false` because the queue consumed the flag. | **"CLEAN auto=false" after queue pickup means QUEUED, not broken.** `gh pr merge --auto` replying "already queued" is confirmation. Do not panic-toggle. |
| `UNKNOWN` | Being processed by the merge queue; a merge_group run is in flight. Normal. | Wait. |
| `DIRTY` | Branch conflicts with `<integration-branch>`. | Run the cheap-first rescue ladder (below). |
| `BEHIND` | Behind base but not conflicting. | Auto-rebase (if configured) or `gh pr update-branch` handles it. |
| `UNSTABLE` | A non-required check failed. | A non-required check failed; doesn't block merge by itself. Check whether it's a known advisory (no action) or a real regression (fix it — prioritize if it gates other work). |

`autoMergeRequest: null` is ambiguous (never armed OR consumed by the queue), and `mergeStateStatus` can read CLEAN/UNSTABLE while enqueued. Only GraphQL `mergeQueueEntry` is definitive:

```bash
gh api graphql -f query='query($o:String!,$r:String!,$n:Int!){
  repository(owner:$o,name:$r){ pullRequest(number:$n){
    mergeQueueEntry{ state position } autoMergeRequest{ enabledAt } } } }' \
  -f o=<owner> -f r=<repo> -F n=<PR#>
```

## CI failure triage — in this order

### 1. Read the failing job's actual log

`gh run view --log-failed` (and check-summary UIs) usually show only the aggregate/gate job that failed *because* an upstream job failed — you diagnose the cascade, not the cause. In one production repo this made a checkout transient look like a coverage failure and burned a full rescue dispatch. Fetch the specific failed job's raw log:

```bash
gh run list --branch <branch> --limit 3 --json databaseId,workflowName,conclusion
gh run view <run-id> --json jobs --jq '.jobs[] | "\(.name) → \(.conclusion // "running")"'
JOB_ID=$(gh run view <run-id> --json jobs --jq '.jobs[] | select(.name == "<JobName>") | .databaseId')
gh api "repos/<owner>/<repo>/actions/jobs/$JOB_ID/logs" | grep -E "FAIL|Error|::error" | head -20
```

Walk the pipeline chain in dependency order (e.g. deploy → DB bootstrap → smoke → E2E) so you find the FIRST real failure, not a downstream symptom.

### 2. Classify transient vs real before touching code

Rebasing or "fixing" a flake wastes rebase debt and can introduce conflicts that wouldn't otherwise exist. In order:

1. **Does the same test pass on sibling PRs / `<integration-branch>` right now?** If yes, lean transient.
2. **Is the job on `<flake-ledger>`?** Mechanical classification rule: a job is flaky iff the *same head SHA* produced both a failure and a success conclusion. On the list → retry, don't rebase.
3. **Rerun the failed job once.** Only investigate code after a second identical failure on the same SHA. One rerun has rescued queue-gating PRs outright.
4. **Known infra transients** (e.g. checkout exit-128 "Bad credentials", registry WAF pull blocks misreported as "pull access denied" — not a rate limit, no 429) always clear on rerun; never dispatch a rescue for them. Note: `gh run rerun --failed` is rejected on superseded or in-progress runs with a misleading "workflow file may be broken" error — use a full rerun.
5. **Stale-failure shadow:** a displayed failure can be from a cancelled/superseded run. If a recent SUCCESS run exists for the same SHA, the failure is stale — nothing to fix.

### 3. Your own behavior change can break specs legitimately

If your PR changes user-facing behavior (e.g. adds a confirm dialog before delete), an existing E2E spec failing on that flow is a *real contract change*, not a flake: update the spec to walk the new UX **in the same PR**. Related trap: whole-page scans (e.g. axe accessibility) inside unrelated specs can catch UI your PR added elsewhere on the page — scope the scan to the component that spec actually tests (matching the spec's stated intent); don't suppress the rule.

### 4. Match against the failure-pattern catalog

Maintain a catalog at `<failure-catalog>` mapping check-name → likely cause → fix recipe → evidence PR#. Recurring failures recur; pre-classification means a rescue starts at the fix, not the discovery. Seed entries (drawn from a JS/TS project — keep the failure SHAPES, rebuild names and recipes per stack):

- **New-lint-rule cascade** — a stricter rule merged to base retroactively breaks every open PR after rebase. Fix: substitute the canonical helpers the rule demands; never disable the rule.
- **Mock-drift cascade** — a merged feature changed a signature; tests mocking the old one fail. Fix: update mocks to the new signature, one commit per pattern. Never blanket-skip (the skipped test is often a security gate).
- **Async-timing flake** — asserting synchronously after an event that schedules async work (focus/RAF/animation). Fix: `await waitFor(() => expect(...))` (JS instance of the shape: assertion races scheduled async work — use your framework's retry-until-true primitive). Retrying forever doesn't fix the race.
- **Stale ephemeral-env data** — preview env provisioned before a recent migration/default change. Fix: rebase+push so the fresh deploy re-runs migrations, or add an idempotent UPDATE to the env-bootstrap script aligning reference data with existing assertions.
- **Cold-deploy timeout** — first per-PR deploy provisions cold and exceeds timeouts. Fix: rebase (picks up timeout bumps already on base) + retrigger; subsequent deploys reuse state. Not a rescue-agent job.
- **DIRTY-no-failures** — see the rescue ladder below.

`<per-pr-deploy>` caveat: deploy workflows with path filters will NOT re-trigger on an empty commit if the PR's diff doesn't match the deploy paths (e.g. test-only PRs). Pushing empty commits to "bring the deploy back" is a dead end by design — know the filter.

## Review threads: bot review = human review

Treat `<bot-reviewer>` comments identically to human review comments. For each: (1) read it — if a suggestion looks technically wrong, *verify before agreeing or refusing* (no performative agreement, no reflexive dismissal); (2) apply the change OR reply with a reasoned counter; (3) mark the thread resolved. When the ruleset enables `required_review_thread_resolution`, **auto-merge will not fire while any thread is unresolved** — the recurring symptom is a fully green PR stuck BLOCKED with zero queue runs, which looks exactly like a broken merge queue and has caused repeated misdiagnoses in practice. Check threads FIRST.

```bash
gh api repos/<owner>/<repo>/pulls/<PR#>/comments     # all line comments (bot + human)
gh pr view <PR#> --json reviews,comments             # review summaries + top-level comments

# gh pr view --json reviewThreads can return EMPTY even when threads exist — use raw GraphQL:
gh api graphql -f query='query($o:String!,$r:String!,$n:Int!){
  repository(owner:$o,name:$r){ pullRequest(number:$n){
    reviewThreads(first:50){ nodes{ id isResolved path
      comments(first:1){ nodes{ author{login} body } } } } } } }' \
  -f o=<owner> -f r=<repo> -F n=<PR#>

# After applying or countering, resolve:
gh api graphql -f query='mutation($t:ID!){
  resolveReviewThread(input:{threadId:$t}){ thread{ isResolved } } }' -f t=<thread-node-id>
```

Three traps with real incident history:

- **The async-orphan trap.** Async bots post threads minutes after PR-open; implementer agents exit before the threads exist, so the orchestrator must sweep open PRs and apply-or-counter-then-resolve on their behalf (see the orchestrating-slots skill for cadence). Worse: a fast PR can auto-merge *before* the threads post — threads land on the CLOSED PR, and a fix pushed to the merged branch is **orphaned, never reaching `<integration-branch>`** (observed: a real bug stayed live while its threads showed "resolved"). Before dispatching any thread-fix work, check `gh pr view <PR#> --json state`; re-land orphaned fixes via a fresh branch off `<integration-branch>` + cherry-pick.
- **Threads are a subset of findings.** Some bots put their full priority list and security review only in the PR body summary, which doesn't gate merge — real P1s (including an authz bypass, in one incident) can auto-merge unaddressed if you triage only threads. Read the body summary too.
- **Resolved threads, unpushed fix.** An agent can resolve its threads (PR goes green and auto-enqueues) while the actual fix sits committed-but-unpushed — the queue merges pre-fix code under falsely-resolved threads. Verify `git -C <worktree> log origin/<branch>..HEAD` is empty before trusting resolutions.

Never post `<ai-mention-trigger>` from any agent — it is a human-only trigger; one AI session invoking another creates unsupervised loops. Enforce mechanically with a permission deny rule matching the mention string in any CLI invocation.

## Meta-gates: titles, breaking changes, honest failure

- **Title-format checks** can gate merge, and with a merge queue **one bad title boots the entire merge group containing it** (innocent green PRs get ejected alongside). Example (observed in practice): subjects beginning with 2+ consecutive capitals were rejected, booting three PRs at once. Fix via API title edit (`gh api -X PATCH repos/<owner>/<repo>/pulls/<PR#> -f title=...`); the check re-runs on edit.
- **Breaking-change gates** (API schema diffs, unsafe migrations) get the sanctioned hatch — `<breaking-change-labels>` or an annotated in-file comment with reason — never an admin merge. The hatch leaves an audit trail; the bypass leaves nothing, and without a sanctioned hatch agents under pressure invent unsanctioned ones.
- **Honest-failure escalation:** when you genuinely cannot fix a gate (missing secret, no infra access, ambiguous intent), say so explicitly and stop. Every paper-over (`--no-verify`, skip-checks, deleting tests) converts a visible, attributable failure into invisible debt discovered later without context.

## Conflicts and DIRTY rescue — cheap-first ladder

Burn the minimum resource at each rung: an API call before an orchestrator action before an agent slot.

1. **`gh pr update-branch <PR#> --repo <owner>/<repo>`** — for DIRTY/BEHIND with zero failing checks. Succeeds (done, no agent) or fails loudly with "Cannot update PR branch due to conflicts" (a real conflict — escalate). This CLI call is fine; the GitHub web "Update branch" button on a *conflicted* PR is not — it produces a merge nobody verified.
2. **Self-handled trivial conflicts** — `<append-only-files>` conflicts resolve mechanically by keeping both entries; `<derived-artifacts>` resolve by **taking the integration branch's version, then regenerating with the project's generator** — never hand-merge generated files; commit the regen.

   ```bash
   cd <worktree>
   git fetch origin <integration-branch>
   git rebase origin/<integration-branch>
   # append-only file → keep both entries; derived artifact → checkout theirs, re-run generator
   git add <file> && git rebase --continue
   git push --force-with-lease origin <branch>
   ```

3. **Dispatched rescue agent** — only for actual code conflicts, on the PR's existing worktree/branch. See the dispatching-subagents skill for the brief template; the brief must name the failing checks, cite the catalog pattern, and include stop-and-report triggers (a failure that looks like a real regression goes to the operator, not a blind "fix" that adjusts the test).

After resolving locally, always re-run `<local-gate>` against the merged result before pushing — conflicts resolved without re-running gates ship silent semantic breakage.

**Force-push discipline.** After rebasing any already-pushed branch, the push requires `--force-with-lease` — never bare `--force` (lease protects against clobbering a concurrent push from a CI auto-rebase bot or sibling operator; recovery from a bare force-push on a shared branch requires force-pushing every downstream branch, because history is rewritten). Plain pushes apply only to never-pushed branches. Never force-push protected/integration branches — it rewrites history every open PR and CI run is based on; recovery requires force-pushing every downstream branch. Per `<force-push-policy>`, sub-agents may be permission-blocked from force pushes — the orchestrator performs them, after explicit operator authorization where required.

**Auto-rebase starvation:** only relevant if the project runs an auto-rebase automation (most don't). Never apply `do-not-rebase` proactively or at PR-open — apply it only after you observe a CI run cancelled by a rebase, then remove it once the PR nears the front of the queue. See the issue control-field skill (**gh-issue-labels** for GitHub labels, **jira-issue-fields** for Jira fields) for the opt-in rule and counter-risk.

## Merge-queue operations

- A PR's own head CI being green proves nothing about queue success: the queue re-runs the full suite on a synthetic `gh-readonly-queue/<integration-branch>/pr-<N>` branch (base + queued entries). **Diagnose boots from those merge-group runs, not the PR's checks.** Any flaky merge-gating test boots whatever shares the queue group.
- Pushing to a branch already in the queue is rejected (GH006 "Branches that are queued for merging cannot be updated"), and `gh pr merge --disable-auto` does NOT dequeue. Recovery: GraphQL `dequeuePullRequest(input:{id:<pr-node-id>})` → push → re-arm `gh pr merge --auto`. A wedged queue (queued 30–40 min, branch locked, no merge-group run ever starts) needs dequeue → `gh pr update-branch` → re-arm.
- A transient hitting a merge_group run **ejects the PR AND clears auto-merge** — the PR then sits CLEAN-looking but unqueued forever. Re-arm `gh pr merge --auto` after every ejection.

## Stuck-PR triage order

When multiple PRs are stuck, work the **oldest first** — older PRs accumulate the most rebase debt and re-fail on every new integration-branch merge; newest-first compounds that cost.

Exactly two skip-ahead exceptions: (a) a newer PR *unblocks* the older one (lint-rule or CI-infra fix the older is downstream of) — merge the unblocker first; (b) the older PR has a stop-and-report awaiting operator decision.

**What NOT to rescue** (each rule prevents an observed waste mode): auto-merge engaged and CI merely running — auto-merge handles the wait, a "babysit" agent burns tokens in no-op polling; a single flake on a non-required check — retry catches it; an older PR about to be unblocked by a newer PR currently merging — let it land.

## Stacked PRs

When a branch must be cut off another open PR's branch (file overlap): open the child as **draft** with `--base <parent-branch>` and do NOT enable auto-merge. If auto-merge is armed early, GitHub squash-merges the child into the parent *feature branch*; a later parent rebase+force-push can silently erase the child's commit from the merge chain — losing the work entirely. Draft state is the mechanical guard. After the parent merges (`gh pr view <parent#> --json mergedAt`):

```bash
git fetch origin <integration-branch>
git rebase origin/<integration-branch>        # parent's commits already in base; only your increments remain
git push --force-with-lease origin <branch>
gh pr edit <PR#> --base <integration-branch>  # GitHub may have retargeted automatically — check first
gh pr ready <PR#>
gh pr merge <PR#> --auto <merge-strategy>     # engage auto-merge NOW (queue → no strategy flag)
```

## Pre-existing red CI: finder owns it

Any agent encountering a failing gating signal owns getting it fixed, even if the failure pre-dates their branch. "I didn't break it" is not an exemption — one tolerated red check trains every agent to ignore red checks. But run the **four coordination probes first** (two agents independently "owning" the same broken test produce conflicting PRs); any hit → link to it and stand down:

```bash
gh pr list --state open --search "<test/file/path>"
gh pr list --state open --search "<failing test name or assertion>"
gh issue list --state open --label bug --search "<test name>"
git ls-remote --heads origin | grep -i "<test-keyword>"
```

Then: a **separate dedicated fix PR** off freshly-fetched `<integration-branch>`, cross-linked from your primary PR — never bundled (bundling muddies review, couples merge risk, and hides the fix from other agents' probes). Classify the dependency explicitly: the fix gates your primary PR only if it shares a package/test surface your CI exercises; otherwise both land in parallel. One known counter-case: never split an E2E-spec fix from the component change it depends on — circularly dependent, neither passes alone.

Resolution priority, documented in the fix-PR body:

1. **Real fix** (default) — fix the bug or repair the test logic.
2. **Delete** — only if the test exercises removed code or duplicates coverage; name the dead code or superseding test.
3. **Skip + tracking issue** (escape hatch only) — `.skip()` permitted only with a simultaneously-filed issue (see the issue-filing skill (**gh-issue-filing** for GitHub, **jira-issue-filing** for Jira)), referenced both inline at the skip site AND in the PR body. Untracked skips outlive their blocker and the coverage hole becomes permanent.

One scoping caveat: don't chase a deploy failure that predates your change (same step failed on a prior commit without your code) when the operator handles deploy health separately — your merged change rides the next green deploy; chasing it derails the task at hand. Confirm which regime the project runs.

## Fresh-context peer review

For orchestrator-dispatched work, peer review is **selective, cold, and never approves**:

- **Selective:** skip for trivial changes (typo, lint, single-line tweak, copy, dead-code delete, fixture-only) — CI plus implementer verification is the bar there. Review what carries risk.
- **Cold:** brief the reviewer with *no implementer context* — "Review PR #N with no prior context; read the diff and linked issue independently; verify the change resolves the **issue's reported behavior**, not merely that the diff looks correct; check `<the project's hard rules>`." Prefixing "the implementer says this works" anchors the reviewer and defeats the point.
- **Never `--approve`:** reviewers use `gh pr review --comment` or `--request-changes` only. Approval-by-proxy satisfies human-review branch protection without any human in the loop; express positive verdicts as comments.
- **Hands-off:** reviewers never modify the PR assignee (it is the multi-operator ownership signal) and never post `<ai-mention-trigger>`.
- Route reviewer specialization by change shape (app code → general reviewer; tests → QA profile; auth/secrets/isolation → security profile; infra/pipelines → ops profile; DDL/migrations → data profile); a PR spanning shapes gets parallel reviewers. Dispatch mechanics and model policy: see the dispatching-subagents skill.

## After merge

If `<integration-branch>` is not the repo's default branch, GitHub will **not** auto-close `Closes #N` issues — the orchestrator must close them explicitly and release the issue lock, or zombie issues get re-dispatched and claim labels go stale. Protocol: see the issue-locking skill. Run the close-on-merge sweep every monitoring tick (see the orchestrating-slots skill).

## Token discipline: caveman for ops, humanizer for prose

This skill runs in high-volume, repetitive orchestration loops where tokens compound across many rounds and many agents. Operate in **caveman mode** (load the `caveman` skill) to cut token use on all working output — status, reasoning, slot tables, completion reports, dispatch and coordination chatter.

Caveman compresses *prose only*. It must NEVER alter machine-precise content, which stays byte-exact: lock-comment markers, the `RECON OK` / `RECON-ERROR` contract lines, JQL, `gh` / Atlassian-MCP commands, label and field names/values, `file:line` references, code blocks, and acceptance-criteria checklists. Compress the narration, never the protocol.

Durable prose a human reads later — issue/ticket bodies and PR descriptions — is the exception: write those through the `humanizer` skill (see the issue-filing skill), not in caveman.
