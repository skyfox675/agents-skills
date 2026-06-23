---
name: jira-issue-filing
description: "File and triage Jira issues that AI sub-agents can implement without asking a single follow-up question — the six-section groomed-issue format (verified file:line evidence, literal acceptance criteria, traceability hint) in the issue description, the filing-time issue-type/Priority/label taxonomy, duplicate and cross-reference etiquette between concurrent operators, follow-up filing instead of scope creep, and the recon protocol that classifies stub issues into ready-to-dispatch / needs-spec-input / blocked via a sandboxed cheap-model decision tree with a machine-parseable output contract. Use whenever you are about to file, draft, groom, split, enrich, or triage a Jira issue or a batch of them — when an operator reports a bug or pastes an error, when a feature request needs to become trackable work, when you discover adjacent work mid-task that must become a follow-up issue rather than scope creep, or when an issue queue needs triage before dispatch — even if the user just says \"file this\", \"make a ticket\", or \"write that up\"."
---

# Filing Jira Issues That Agents Can Ship

Issues filed here feed the multi-agent pipeline (claimed per jira-issue-locking,
dispatched per dispatching-subagents, scheduled per orchestrating-slots,
merged per driving-prs-to-merge; fields/labels per jira-issue-fields). This skill
covers both ends of intake: writing groomed issues, and recon-triaging stubs.

All Jira reads and writes go through the **Atlassian MCP server** (the official
Atlassian Remote MCP); operations are named by their canonical tool
(`createJiraIssue`, `getJiraIssue`, `editJiraIssue`, `searchJiraIssuesUsingJql`,
`transitionJiraIssue`, `addCommentToJiraIssue`) — exact tool names depend on the
connected server. Adopters without the Atlassian MCP can substitute the Jira
REST v3 API or a Jira CLI for the same operations; the protocol is identical,
only the call surface changes.

## Project bindings

Define these once in the adopting project's CLAUDE.md, alongside the sibling
skills' shared bindings (integration branch, worktree convention, toolchain
bootstrap, CI gate names, bot reviewers, operator accountIds). The body refers
to them by placeholder; example values are illustrations, not requirements.

| Binding | Meaning | Example |
|---|---|---|
| `<jira-project-key>` | project key targeted by `createJiraIssue` / JQL | `PROJ` |
| `<jira-site>` | site/cloudId the MCP operates against | `acme.atlassian.net` |
| `<issue-types>` | exactly-one issue type per ticket | `Bug`, `Story`, `Task` |
| `<priority-field>` | exactly-one native Priority value | `Highest`…`Lowest` |
| `<jira-ready-status>` | workflow status meaning ready-to-dispatch | `Ready` |
| `<jira-inprogress-status>` | workflow status meaning active work | `In Progress` |
| `<jira-blocked-status>` / `<jira-needs-input-status>` | terminal triage statuses (label fallback below) | `Blocked` / `Needs Input` |
| `<jira-done-status>` | terminal completed status | `Done` |
| `<security-label>` | flag for authn/authz/data-isolation/OWASP-class issues | `security` |
| `<lane-labels>` | shared-surface vs isolated work (hyphenated; no spaces) | `lane-plumbing`, `lane-leaf` |
| `<component-labels>` | component/subsystem label or Component | `subsystem-auth` |
| `<triage-labels>` | terminal triage states, label fallback when workflow is locked | `triage-ready-to-dispatch`, `triage-needs-spec-input`, `triage-blocked` |
| `<claim-label>` / `<hold-label>` | active-work lock (jira-issue-locking) / operator hold (jira-issue-fields); neither applied at filing | `agent-claimed` / `do-not-dispatch` |
| `<breaking-change-labels>` | CI breaking-change acknowledgment gates, if any | `db-breaking-change-acknowledged` / `api-breaking-change-acknowledged` |
| `<traceability-scheme>` | requirement-ID format + doc location, if formal traceability exists | `REQ-<PREFIX>-<N>` in `docs/specs/` |
| `<shared-surfaces>` | enumerated contention-prone files defining the plumbing lane | DB schema, new migrations, API schema, design tokens, shared-types package, root manifest/lockfile |
| `<crown-jewel-invariant>` | hardest invariant; mentioning it auto-escalates to Highest | "tenant isolation" |
| `<subsystem-tiers>` | security-critical (auto-Highest) / core (partial → High) / deferred (auto-stall without logged decisions) | auth/payments vs core feature modules vs deferred/experimental areas… |
| `<decision-records>` | where architectural decisions for deferred areas are logged | `docs/specs/_subsystems/` |
| `<design-source>` | UI source of truth a UI spec must anchor to | `design-system/` folder |
| `<cheap-model>` / `<default-model>` | recon model tier / escalation tier | `haiku` / `sonnet` |

Projects whose workflow cannot be customized use the `<triage-labels>` fallback
instead of dedicated statuses — be explicit which you use. Projects without
formal traceability drop `<traceability-scheme>` but keep the explicit "no
requirement needed" escape described below.

PRs still live on GitHub (see driving-prs-to-merge); the Jira issue is
cross-referenced from the PR via its issue key `PROJ-123`, never the reverse
paraphrase.

## Core principle: the issue body IS the spec

Dispatch briefs point at the issue description; they never paraphrase it —
paraphrases go stale the moment the issue is edited, and stale paraphrases have
caused shipped rework. So the description must clear this bar: **a sub-agent can
pick the issue up and ship a PR without asking the operator anything**. Every
skipped section becomes a clarifying-question round-trip; every round-trip is a
lost dispatch cycle. Keep design debate OUT of the description — agents treat
description text as instructions, so embedded debate becomes accidental
requirements. Spec goes in the description; discussion in comments
(`addCommentToJiraIssue`).

## The six mandatory sections

These six sections go in the Jira issue **description** (ADF / wiki markup —
checklists render as a bullet or checkbox list; acceptance criteria as a
checklist of testable items). The Title section becomes the Jira **summary**.

### 1. Title (summary)

`[type] Subject — short qualifier`, under 100 characters — specific enough
that the dispatch queue is scannable without opening issues.

```
Example:
- [Security] No API introspection/debug endpoint control in production
- Settings > Billing > status pills: add on-hover check-icon affordance (route to existing modal)
```

### 2. Symptom / what's wrong (or what's missing)

Concrete, framed so an agent can locate the change point from the description
alone: quote offending copy verbatim, link screenshots, paste error text, link
the failing CI run or log. Label any suspected cause explicitly ("Hypothesis,
unverified: …"), never bare — agents implement an unlabelled hypothesis as if
it were a confirmed finding.

### 3. Affected code — verified file:line refs (required)

A fenced list, one `` - `path/to/file.ts:NN` — one-phrase description `` entry
per location (`:NN-MM` for ranges):

```
Example:
- `apps/web/src/lib/billing.ts:120` — invoice row click handler
- `apps/web/src/…/status-pills.tsx:83-129` — pill render
```

Grep to confirm every cited line number immediately before filing — stale line
refs are worse than no refs, because an agent trusting a wrong pointer wastes
more time than one searching fresh. Rough-but-verified beats precise-but-stale;
if you only know the file, cite the file and say so.

### 4. Desired behaviour / replacement copy

Spell out exactly what to produce:

- Copy fixes: the literal replacement text, not a description of its tone.
- UI work: interaction states (hover, focus, click, keyboard, disabled,
  read-only) and the anchor in `<design-source>`.
- Backend work: the contract — input → output plus every error case that
  matters.

### 5. Acceptance criteria (required)

A checklist where each item is **independently testable**. The implementing
agent self-verifies against this list before opening the PR, so an untestable
criterion ("works well") is a no-op.

```
Example:
- [ ] Click any non-current pill opens the existing confirmation dialog.
- [ ] Confirm fires `onStatusChange` exactly once; Cancel/Esc fires nothing.
- [ ] Read-only path renders no interactive button.
- [ ] Tests cover all 4 transition directions (forward + backward).
```

### 6. Traceability hint

Three-way, pick one:

- **Refines an existing requirement** — name its `<traceability-scheme>` ID.
- **Proposes a new requirement** — candidate ID + suggested wording.
- **No requirement needed** — say so explicitly for pure chore/CI work.

The explicit "none needed" option exists so agents never stall hunting for
traceability on work that legitimately has none.

## Optional sections that pay for themselves

- **Open questions for operator** — `**Operator: confirm <X>**` lines for
  genuinely ambiguous decisions; converts silent wrong guesses into visible
  questions.
- **Out of scope / follow-ups** — adjacent work the agent must NOT do, noting
  follow-ups will be filed; the scope-creep fence that keeps PRs small.
- **Reference implementation** — "mirrors PR #1234's pattern" when a shipped PR
  established the approach; prevents pattern divergence across the codebase.
- **Dependency** — `Depends on PROJ-123` when another PR must land first;
  recon's BLOCK rule consumes this exact phrase mechanically.

## Issue type, Priority, and labels at filing time

- Exactly one `<issue-types>` value (Bug / Story / Task), exactly one
  `<priority-field>` value — the exactly-one constraints make
  `searchJiraIssuesUsingJql` filterable and the dispatch queue deterministic.
  Pick the issue type via `getJiraProjectIssueTypesMetadata`; set Priority on
  the native field. Map P0→Highest, P1→High, P2→Medium, P3→Low (Lowest for
  trivia). If the project's Priority field is locked down, fall back to a
  `priority-P0` label.
- `<security-label>` if the issue touches authn/authz, data isolation, or an
  OWASP-class concern.
- A plumbing `<lane-labels>` tag if the work is primarily on a shared surface
  (recon can also set this later). Jira labels cannot contain spaces — use
  hyphenated single tokens (`lane-plumbing`, `subsystem-auth`).
- `<breaking-change-labels>` pre-flagged if the spec itself calls for breaking
  schema/API/DB changes — discovering the CI acknowledgment gate mid-PR stalls
  the merge; the implementer can add it later, but filing-time is cheaper.

Do not apply `<claim-label>` or set the assignee at filing time — claiming
happens when work starts, per jira-issue-locking; premature claims hide
filed-but-unworked issues from the dispatch filter and show phantom ownership to
concurrent operators. `<hold-label>` is operator-only (see jira-issue-fields) — never
apply it.

## One theme per issue; batch filings are independent

Split multi-theme reports into separate issues before filing, not after
dispatch — integration throughput is fastest with small focused PRs, and a
multi-theme issue forces one bloated PR or an agent guessing where to stop.
Batch-file distinct items as separate issues (parallel `createJiraIssue` is
fine), each with a fully independent description, key, and lock surface; shared
lock comments or cross-issue state break per-issue ownership for
independently-filed issues — the only sanctioned shared-lock shape is the
bundled-issue protocol in jira-issue-locking (one lead lock, sibling `bundled_with`
pointers).

## Cross-references, duplicates, and follow-ups

- **Issue spawned by another issue:** put `Refs PROJ-123` at the top of the new
  description AND post a forward-link comment on the source (`addCommentToJiraIssue`:
  "filed as PROJ-456") — bidirectional links survive either issue being closed.
  Where the project uses Jira issue links, an explicit "relates to" link is
  stronger than free text.
- **Refining an existing issue:** comment on it rather than filing a sibling,
  unless scope or owner is materially different — near-duplicate siblings split
  the discussion and the claim/lock surface across two keys.
- **Pre-filing search:** search open issues for the same symptom
  (`searchJiraIssuesUsingJql`), and check merged PRs on GitHub — when PRs land on
  a non-default integration branch the linked Jira issue is not auto-transitioned,
  so a non-Done status does not mean "unfixed" (see driving-prs-to-merge for the
  transition-on-merge sweep).
- **Two operators filed the same thing:** the later filer yields (comment
  "Duplicate of PROJ-123 — closing in favour of that.", then
  `transitionJiraIssue` your own to `<jira-done-status>`/a Won't-Do resolution),
  unless the original is low-quality — then enrich the original and close your
  own as the dupe. The deterministic rule avoids negotiation; the exception
  preserves the better content.
- **Work discovered mid-task:** file a follow-up (full six sections, `Refs`
  back to the current issue/PR) instead of expanding the current PR. Imperative
  operator phrasing ("update X") during a diagnostic session means "file an
  issue specifying X" unless implementation is explicitly delegated.

## Filing anti-patterns (each named because it happened)

- "X is broken" with no code refs or screenshots — forces twenty questions.
- Design debate in the description — becomes accidental requirements; use comments.
- One issue spanning many themes — throttles the whole merge pipeline.
- The same issue filed under multiple issue types "hoping one matches".
- Claiming (`<claim-label>` or assignee) at file time — see above.

---

# Recon: triaging stub issues into dispatchable work

Not every issue arrives at the grooming bar. Recon is the cheap, sandboxed
classification pass that moves a stub to exactly one terminal triage state.

## The status-encoded triage state machine

An issue is **untriaged** when it carries a `<component-labels>` label but sits
in none of the terminal triage states. One recon pass moves it to exactly one
terminal state — prefer the Jira **workflow status** (`<jira-ready-status>` /
`<jira-needs-input-status>` / `<jira-blocked-status>`); fall back to the
`<triage-labels>` labels for projects whose workflow can't be customized. Be
explicit which you use:

| Terminal state | Mandatory companions | Must NOT have |
|---|---|---|
| `<jira-ready-status>` / `triage-ready-to-dispatch` | lane label + Priority value | — |
| `<jira-needs-input-status>` / `triage-needs-spec-input` | a multiple-choice question comment | lane label or Priority |
| `<jira-blocked-status>` / `triage-blocked` | a comment naming the dependency | the ready status/label |

Encoding state in status (or labels) makes the queue queryable with one
`searchJiraIssuesUsingJql` call and readable by multiple operators without
shared memory. The companion requirements make partial classification
*detectable*: a terminal state missing its companions is corrupted state, and a
needs-input issue carrying lane/Priority gets picked up by careless filters as
if ready. The dispatch filter selects only the ready state — but status and
labels go stale (in one observed case the ready state persisted after another
operator claimed, double-locking four issues), so verify the assignee field is
empty (`assignee is EMPTY`) immediately before locking; see jira-issue-locking. The
ready bar is the filing grooming bar: the description alone lets an agent ship
with zero round-trips.

## Why recon runs on `<cheap-model>` — and when it must not

Cheap models ship subtle errors on open-ended work; they are safe only when
the blast radius is capped and the task is mechanical. Recon qualifies only
while all three properties hold:

1. Tool access hard-restricted: read-only repo access plus label/comment
   mutations on a single issue.
2. Decision tree concrete and short (five rules, stop at first match).
3. Output is a single contract line validatable at a glance.

If a recon brief violates any property — e.g. it also asks the agent to
rewrite the issue description — escalate that dispatch to `<default-model>`.

## Sandbox: allowed and forbidden operations

Allowed:

```text
getJiraIssue PROJ-123                         # title, description, labels, status, comments
searchJiraIssuesUsingJql "project = <jira-project-key> AND ..."   # open issues / dedupe
git grep …   # plus git log — read-only repo queries
gh pr list --state open --search "PROJ-123"   # GitHub PRs cross-referencing the key
editJiraIssue PROJ-123  (add/remove label only, this issue)
addCommentToJiraIssue PROJ-123 "…"
transitionJiraIssue PROJ-123 → terminal triage status  (this issue only)
```

Forbidden — on attempting any of these, stop and emit `RECON-ERROR: <what was
attempted>`; silent recovery hides sandbox escapes from the orchestrator:

- Edit or Write any repo file.
- Create issues or PRs; transition this issue to Done or any other issue at all.
- Mutate any other issue or any PR.
- Add or remove the assignee — assignment is the lock-time ownership signal
  owned exclusively by the orchestrator (set by accountId via
  `lookupJiraAccountId`; see jira-issue-locking); a recon agent setting one forges a
  claim that other operators will honor.

## The decision tree — apply in order, stop at first match

Ordering encodes precedence: an ambiguous spec stalls *before* lane/Priority
effort is spent; lane must be known *before* the lane-contention check; and
Priority is computed only for issues that will actually dispatch.
Stop-at-first-match keeps the task inside a cheap model's reliability envelope.

1. **SPEC-CLARITY → needs-spec-input** if: hedge words ("appropriate",
   "reasonable", "intuitive", "complex", "robust") without measurable detail —
   these read as requirements but are undecided design, and dispatching them
   produces guess-driven implementations; OR an undecided reference (e.g.
   "configure webhook" without destination/format/auth); OR a deferred-tier
   subsystem with no decision logged in `<decision-records>`; OR a recorded
   code/spec deviation with no resolution; OR a UI requirement with no anchor
   in `<design-source>`.
2. **LANE** → plumbing if likely-touched files include any `<shared-surfaces>`
   (purely additive changes, e.g. a new enum value, count as leaf). Use two
   evidence sources: the issue's Affected-code/Files metadata AND `git grep`
   for the requirement ID and adjacent identifiers — listed metadata goes
   stale, and grep alone misses planned-but-unwritten files. Else leaf.
3. **BLOCK → blocked** if: the description says `Depends on PROJ-123` and
   PROJ-123 is not Done; OR the spec references another requirement mapping to
   an open issue (chase ONE transitive hop only — deeper chains blow the token
   budget and rarely change the verdict); OR it is plumbing-lane while another
   plumbing PR in flight touches the same file — parallel shared-surface PRs
   (schema, migrations, tokens) reliably collide on merge.
4. **PRIORITY** (only if reached): Highest if the subsystem is security-critical
   per `<subsystem-tiers>` OR the text mentions `<crown-jewel-invariant>` OR
   it is a bug with severity high/critical. High if partially implemented AND in
   a core-tier subsystem. Medium otherwise.
5. **CLEAR** → move to `<jira-ready-status>` (or add `triage-ready-to-dispatch`).
   Done.

## Spec-stall comments are multiple-choice, never open-ended

Open-ended questions push spec-writing back onto the operator and stall the
queue indefinitely; multiple-choice with a write-in turns the reply into a
one-token unblock that recon mechanically consumes on re-run. One comment
(`addCommentToJiraIssue`):

```markdown
**Recon stalled — 1 question for you:**

The spec says: > <quoted line, verbatim>

The agent would need to choose between:
- (a) <option a — concrete description>
- (b) <option b — concrete description>
- (c) <neither — describe what you want>

Reply with `(a)` / `(b)` / `(c) <your answer>`. The orchestrator will re-run
recon and dispatch.
```

Then move to `<jira-needs-input-status>` (or add `triage-needs-spec-input`) and
STOP — no lane label or Priority.

## Output contract and orchestrator validation

The recon agent ends with exactly one line:

```
RECON OK PROJ-123: ready-to-dispatch lane:<L> priority:<P>
RECON OK PROJ-123: needs-spec-input
RECON OK PROJ-123: blocked (PROJ-<dep>)
RECON-ERROR: <message>
```

Validate this line against the state actually set (`getJiraIssue PROJ-123` —
status + labels) — agents can report `RECON OK` without performing the
mutations.

## Budgets and fan-out

- **Token budget: 5K output per issue — hard.** If exceeding, emit
  `RECON-ERROR: token budget exceeded`; never silently truncate — a truncated
  classification looks like a verdict but is not one.
- **Wall clock: ≤ 60s per issue — soft.** Overrunning is not a failure, just a
  signal the brief needs tightening. Do not conflate the two.
- **Fan-out:** one issue per dispatch (mutation surface matches the sandbox);
  up to 5 in parallel per round, in one message per dispatching-subagents —
  the cap bounds status/label churn and the orchestrator's validation load.

## Recon brief template

Copy `references/recon-brief.md` verbatim at dispatch time, filling `<>`
placeholders — paraphrased briefs drift; an identical template makes
cheap-model fan-out safe and results comparable.

## Token discipline: caveman working, humanizer for the story

Your recon, triage, and coordination chatter runs in the same high-volume orchestration loop as the sibling skills — operate in **caveman mode** (load the `caveman` skill) for that working output to conserve tokens, keeping all machine-precise content byte-exact (labels/fields, JQL, `gh`/MCP commands, the `RECON OK` / `RECON-ERROR` contract, `file:line` refs, code blocks).

But the issue/ticket body IS the story — the durable artifact a human reads and an agent implements from. NEVER write it in caveman. Draft it in full natural prose, then run it through the `humanizer` skill before filing so it reads human-written, not AI-generated (it strips inflated phrasing, rule-of-three, em-dash overuse, vague attributions, and filler). Humanize the Symptom and Desired-behaviour narrative; leave the verified `file:line` evidence, the acceptance-criteria checklist, and the labels/fields exactly as specified — precision there beats prose.
