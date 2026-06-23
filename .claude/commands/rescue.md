---
description: Rescue a stuck PR or a failing environment — diagnose and fix failing CI/CD, PR checks, blocking review threads, and merge conflicts, then re-arm the merge path. Example — /rescue 1234, or /rescue dev
argument-hint: <pr-number | environment>
allowed-tools: Bash(gh pr view:*), Bash(gh pr checks:*), Bash(gh pr list:*), Bash(gh run list:*), Bash(gh run view:*), Bash(gh run rerun:*), Bash(gh api:*), Bash(gh issue list:*)
---

# /rescue — unstick a PR or an environment

> Operate in caveman mode (load the `caveman` skill) to conserve tokens. Keep `gh` commands, GraphQL, check/job names, and PR numbers byte-exact; compress only the narration. Any issue you file goes through the `humanizer` skill (see the issue-filing skill).

Arguments: `$ARGUMENTS`

Parse the single argument: a number (with or without `#`) is a **PR rescue**; anything else (`dev`, `staging`, `prod`, an ephemeral env name) is an **environment rescue**. No argument: survey owned open PRs and the integration branch for the most blocked thing and propose the target — don't guess silently.

The protocols live in the **driving-prs-to-merge** skill (PR lifecycle, CI triage ladder, thread etiquette, conflict recovery) and its CI-ownership rules — consult it before acting. Diagnosis precedes mutation: most "stuck" PRs are false signals that cost nothing to clear, and a wrong rescue burns CI runs and review attention.

## PR rescue (`/rescue <pr#>`)

1. **Snapshot the PR**: `gh pr view <N> --json state,mergeStateStatus,autoMergeRequest,labels,headRefName` + `gh pr checks <N>` + unresolved review threads via the GraphQL query in driving-prs-to-merge (`--json reviewThreads` can return empty — use raw GraphQL). If the PR is already merged or closed, stop and say so — fixes pushed to merged branches are orphaned (re-land via fresh branch if work is needed).

2. **Rule out false signals first**, per the skill's catalog: stale cancelled-run shadow (a newer SUCCESS run for the same SHA), queued-not-broken (`CLEAN` + `autoMerge=false` → re-run `gh pr merge <N> --auto`; "already queued" is confirmation), silently-dropped auto-merge (re-arm, it's idempotent), green-but-stuck (almost always unresolved bot threads, not the queue).

3. **Failing checks**: read the failing *job's* raw log via the API — summary and gate jobs only show the cascade, not the cause. Classify: transient/flake (does the same check pass on sibling PRs and the integration branch?) → one rerun before touching code; real failure → fix in the PR's existing worktree/branch, following the pre-push hygiene from dispatching-subagents (rebase first, reinstall deps, regenerate derived artifacts).

4. **Blocking threads**: treat bot reviewers as human reviewers — apply the fix or counter with reasoning, then resolve each thread via the GraphQL mutation. Threads gate merge in repos with thread-resolution rulesets; unresolved threads with green CI is the classic invisible blocker.

5. **Merge conflicts (`DIRTY`)**: try `gh pr update-branch <N>` first; on real conflicts, rebase the branch onto the fresh integration branch in its worktree. Derived/generated artifacts (lockfiles, generated manifests): take the integration branch's version, then regenerate with the project's generator — never hand-merge them. Push per `<force-push-policy>` (--force-with-lease after a rebase; if policy reserves force pushes for the operator, stop and report with the exact command).

6. **Re-arm and verify**: auto-merge enabled, required labels still present, then report — diagnosis, actions taken, current mergeStateStatus, and what (if anything) still blocks.

## Environment rescue (`/rescue <env>`)

1. **Find the failure**: latest runs of the environment's deploy/CI workflows (`gh run list --branch <integration-branch>` or the env's workflow). Identify the failing jobs and read their raw logs — same rule, the *job's* log, not the summary.

2. **Classify**: infra transient (rerun), real regression (find the introducing change — recent merges touching the failing area), config/secret/permission gap (these need operator action — surface the exact missing resource and the provisioning command; never guess at secrets).

3. **Ownership and coordination**: before fixing, check for an existing PR or issue already addressing it (the finder-owns-it rule has a coordination-check escape). If none: file a groomed issue per the issue-filing skill (gh-issue-filing / jira-issue-filing) (run/job IDs as evidence), then either fix it directly when mechanical or lock + dispatch per dispatching-subagents when substantial.

4. **Verify the fix lands**: the fix PR goes through the normal driving-prs-to-merge flow; the rescue isn't done until the environment's workflow is green again or the remaining blocker is explicitly an operator action (say which).

In both modes, end with a short report: what was wrong (root cause, not symptom), what you changed, what state the target is in now, and anything that needs the operator.
