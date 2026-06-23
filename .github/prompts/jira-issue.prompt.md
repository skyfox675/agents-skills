---
description: File a groomed, dispatchable Jira issue from a breadcrumb (component/page/object) plus a problem description — recon the code, verify evidence, dedupe via JQL, set fields, file via the Atlassian MCP. Optionally pin the dispatch model/effort. Example — /jira-issue "Settings > Billing > Invoice row" clicking an invoice opens a 404 model:opus effort:high
argument-hint: <breadcrumb> <description of the issue> [model:sonnet|opus|fable] [effort:low|medium|high|max]
agent: agent
---

# /jira-issue — file a groomed Jira issue

Arguments: `${input:args}`

Parse them as:

- The first token (or quoted phrase) is the **breadcrumb** — a UI path (`Settings > Billing > Invoice row`), a route (`/dashboard`), a component or object name, or a file path.
- Optional `model:<tier>` and `effort:<level>` tokens may appear **anywhere** in the arguments. Strip them out before reading the rest. Valid tiers/levels come from the jira-issue-fields skill's taxonomy (model: `sonnet` | `opus` | `fable`; effort: `low` | `medium` | `high` | `max`, adjusted to the project's bound model lineup). An unrecognized value is a typo — warn the operator and file without that label rather than inventing one.
- Everything else is the **description** of the problem as the operator experienced it.

Example: `/jira-issue "Settings > Billing > Invoice row" clicking an invoice opens a 404 model:opus effort:high`

The **jira-issue-filing** skill is the protocol — issue anatomy, the Jira field/label taxonomy, duplicate etiquette all come from it. This command is the entry point; consult the skill before drafting. Jira reads/writes go through the **Atlassian MCP** (`createJiraIssue`, `searchJiraIssuesUsingJql`, `getJiraIssue`, `editJiraIssue`, …) — allowlist your server's tools in `.claude/settings.json` (the prefix above, `mcp__atlassian__`, may differ from your configured server name); adopters without the MCP can substitute the Jira REST v3 API or a Jira CLI. (Tracking work in GitHub instead? Use `/gh-issue`.)

## Steps

1. **Recon the breadcrumb.** Resolve it to real code: search the repo for the component/route/object it names and capture the concrete `file:line` pointers the skill's evidence section requires. Verify every pointer by reading it before citing — stale references are worse than none. If the breadcrumb matches multiple candidates, cite the strongest and list the runners-up in the issue body so the implementer doesn't re-derive them.

2. **Check for duplicates** per the skill's etiquette: `searchJiraIssuesUsingJql` for the key terms from the breadcrumb and description (e.g. `project = <jira-project-key> AND statusCategory != Done AND text ~ "<terms>"`). If a live duplicate exists, enrich it with a comment (your recon evidence) instead of forking a new issue, and report that outcome instead. If the operator passed `model:`/`effort:`, apply those labels to the duplicate — that instruction stands regardless of which issue carries the work.

3. **Draft the issue** using the skill's groomed anatomy in the Jira **description**: summary per the project's convention, Symptom (from the operator's description, verbatim where possible), verified `file:line` evidence (from step 1), Desired behavior, independently-testable Acceptance criteria (as a checklist), and the traceability hint if the project binds one. Infer priority from user impact and state the reasoning in one line of the body — do not stop to ask. Write the Symptom and Desired-behavior prose naturally and run the description through the `humanizer` skill before filing — the ticket is a story a human reads; keep the verified `file:line` evidence and the acceptance-criteria checklist exactly as captured.

4. **File it**: `createJiraIssue` with the issue **type** (Bug/Story/Task) and **Priority** field per the project's taxonomy, plus the `agent-model-<tier>` / `agent-effort-<level>` labels when the operator passed them — these count as the operator's explicit per-issue instruction at dispatch time (see jira-issue-fields; premium tiers are operator-gated, and passing one here IS that operator's authorization). Never assign/lock at filing — claiming happens at dispatch time (see the jira-issue-locking skill).

5. **Report back**: the issue key + URL, the type/priority/labels applied (including any model/effort pins), the evidence anchors cited, and any near-duplicates found in step 2.

If the project's Priority field or workflow statuses aren't set up, file with what's available and tell the operator which fields/statuses the bindings expect — unlike GitHub labels, Jira labels need no pre-creation (they exist on first use), so no bootstrap step is required (see jira-issue-fields).
