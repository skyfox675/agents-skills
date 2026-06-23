# /gh-issue — file a groomed GitHub issue

Arguments: the text you type after the command

Parse them as:

- The first token (or quoted phrase) is the **breadcrumb** — a UI path (`Settings > Billing > Invoice row`), a route (`/dashboard`), a component or object name, or a file path.
- Optional `model:<tier>` and `effort:<level>` tokens may appear **anywhere** in the arguments. Strip them out before reading the rest. Valid tiers/levels come from the gh-issue-labels skill's taxonomy (model: `sonnet` | `opus` | `fable`; effort: `low` | `medium` | `high` | `max`, adjusted to the project's bound model lineup). An unrecognized value is a typo — warn the operator and file without that label rather than inventing one.
- Everything else is the **description** of the problem as the operator experienced it.

Example: `/gh-issue "Settings > Billing > Invoice row" clicking an invoice opens a 404 model:opus effort:high`

The **gh-issue-filing** skill is the protocol — issue anatomy, labels, duplicate etiquette all come from it. This command is the entry point; consult the skill before drafting. (Tracking work in Jira instead? Use `/jira-issue`.)

## Steps

1. **Recon the breadcrumb.** Resolve it to real code: search the repo for the component/route/object it names and capture the concrete `file:line` pointers the skill's evidence section requires. Verify every pointer by reading it before citing — stale references are worse than none. If the breadcrumb matches multiple candidates, cite the strongest and list the runners-up in the issue body so the implementer doesn't re-derive them.

2. **Check for duplicates** per the skill's etiquette: search open issues for the key terms from the breadcrumb and description. If a live duplicate exists, enrich it with a comment (your recon evidence) instead of forking a new issue, and report that outcome instead. If the operator passed `model:`/`effort:`, apply those labels to the duplicate — that instruction stands regardless of which issue carries the work.

3. **Draft the issue** using the skill's groomed anatomy: title per the project's convention, Symptom (from the operator's description, verbatim where possible), verified `file:line` evidence (from step 1), Desired behavior, independently-testable Acceptance criteria, and the traceability hint if the project binds one. Infer priority from user impact and state the reasoning in one line of the body — do not stop to ask. Write the Symptom and Desired-behavior prose naturally and run the body through the `humanizer` skill before filing — the issue is a story a human reads; keep the verified `file:line` evidence and the acceptance-criteria checklist exactly as captured.

4. **File it**: `gh issue create` with the filing-time labels (type + priority per the project's taxonomy), plus `agent-model:<tier>` / `agent-effort:<level>` when the operator passed them — these labels count as the operator's explicit per-issue instruction at dispatch time (see gh-issue-labels; premium tiers are operator-gated, and passing one here IS that operator's authorization). Never claim/lock at filing — claiming happens at dispatch time (see the gh-issue-locking skill).

5. **Report back**: the issue URL, the labels applied (including any model/effort pins), the evidence anchors cited, and any near-duplicates found in step 2.

If the project's label taxonomy is missing (`gh label list` shows no priority/type or agent-control labels), file the issue unlabeled and tell the operator which labels the bindings expect — the gh-issue-labels skill's `scripts/bootstrap-labels.sh` creates them in one command.
