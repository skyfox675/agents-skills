---
description: Same as /gh-issue, plus an AWS deep-dive — diagnose the reported symptom through the operator's live AWS CLI session using strictly read-only calls (logs, metrics, resource state, CloudTrail) before filing the groomed GitHub issue with cloud-traced evidence. Example — /gh-issue-use-aws "file export" presigned download URLs 403 on staging model:opus
argument-hint: <breadcrumb> <description of the issue> [model:tier] [effort:level]
allowed-tools: Bash(gh issue create:*), Bash(gh issue list:*), Bash(gh label list:*), Bash(gh search:*), Bash(aws sts get-caller-identity:*), Bash(aws logs tail:*), Bash(aws logs filter-log-events:*), Bash(aws cloudtrail lookup-events:*)
---

# /gh-issue-use-aws — file a groomed GitHub issue with an AWS-traced diagnosis

Arguments: `$ARGUMENTS` — parsed exactly like `/gh-issue` (see `gh-issue.md` in this commands directory): breadcrumb first, optional `model:`/`effort:` tokens anywhere, the rest is the description. The filing flow — codebase recon, duplicate check, groomed anatomy, labels, report — is `/gh-issue`'s, unchanged. This command adds one phase: an **AWS deep-dive** between recon and drafting, run against the operator's current AWS CLI session. (Tracking work in Jira instead? Use `/jira-issue-use-aws`.)

## The AWS deep-dive

The point: many symptoms ("the tile shows zero", "downloads 403", "the pipeline never finishes") can't be root-caused from code alone — the answer lives in CloudWatch logs, resource configuration, IAM, or event history. An issue that ships with the cloud-traced root cause ("the Lambda's env var is missing on the deployed function — ARN ..., confirmed via get-function-configuration") is dispatchable without the implementer re-deriving the diagnosis with their own (possibly absent) AWS access.

### Ground rules — read-only means read-only

- **Identity first.** Run `aws sts get-caller-identity` and note account + assumed role; state the account/region every finding came from. If the session's account doesn't plausibly match the environment the operator described, say so and stop the deep-dive — evidence from the wrong account is worse than none.
- **Allowed operations**: `get-*`, `describe-*`, `list-*`, `lookup-events` (CloudTrail), `filter-log-events` / `tail` (CloudWatch Logs), and the Logs Insights pair `start-query`/`get-query-results` (sanctioned despite the `start-` prefix — it reads, it doesn't change state; keep queries time-bounded, scanning costs money).
- **Forbidden, no exceptions**: anything that creates, updates, deletes, puts, attaches, modifies, tags, invokes, starts (other than `start-query`), stops, reboots, or terminates. `lambda invoke` counts as forbidden — executing code is not reading state.
- **Secrets stay sealed.** Diagnose with metadata (`describe-secret`, parameter descriptions, key existence) — never `get-secret-value` or `get-parameter --with-decryption`. If a diagnosis genuinely hinges on a secret's value, report that to the operator as an operator-action item instead of reading it.
- **Use the session as-is.** No `--profile` switching unless the operator named one. The session's permissions are the boundary — an AccessDenied is a finding ("diagnosis needs X permission"), not an obstacle to work around.
- Only `sts get-caller-identity`, log reads, and CloudTrail lookups are pre-approved above; other read calls will prompt per the project's permission settings. Adopting projects that use this command often should allowlist their common read patterns in `.claude/settings.json` rather than blanket-granting `aws:*` — the narrow grant is what keeps "read-only" enforceable.

### Method

1. Form a hypothesis from the codebase recon (which Lambda/queue/table/bucket/distribution serves this breadcrumb), then verify each hop against the deployed reality: function configuration and env vars, log streams around the failure window, queue depths and DLQs, table/bucket existence and the exact key shapes the code queries, recent CloudTrail events for config drift.
2. Prefer narrowing over trawling: time-bound log queries to the reported failure window; filter on request/correlation IDs from the symptom when the operator provided any.
3. If the deep-dive is substantial, dispatch it as a **diagnostic sub-agent** (per dispatching-subagents) with this section's ground rules pasted verbatim into the brief — a diagnostic agent changes no code and no cloud state; its deliverable is findings.

### Evidence into the issue

AWS findings go in the issue's evidence section alongside the `file:line` pointers: resource ARNs/IDs, the exact read command run, minimal log excerpts (timestamps kept, anything sensitive redacted), and the account/region context. Findings that require operator action (missing permission, unprovisioned resource, secret rotation) get their own "Operator action" line in the issue body — clearly separated from what a dispatched agent can fix in code.

Everything else — dedupe etiquette, model/effort pins, never-claim-at-filing, the final report — follows `/gh-issue` exactly.
