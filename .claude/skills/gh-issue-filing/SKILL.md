---
name: gh-issue-filing
description: "Write and triage GitHub issues that AI sub-agents can implement without asking a single follow-up question — the six-section groomed-issue format (verified file:line evidence, literal acceptance criteria, traceability hint), the filing-time label taxonomy, duplicate and cross-reference etiquette between concurrent operators, follow-up filing instead of scope creep, and the recon protocol that classifies stub issues into ready-to-dispatch / needs-spec-input / blocked via a sandboxed cheap-model decision tree with a machine-parseable output contract. Use whenever you are about to file, draft, groom, split, enrich, or triage a GitHub issue or a batch of them — when an operator reports a bug or pastes an error, when a feature request needs to become trackable work, when you discover adjacent work mid-task that must become a follow-up issue rather than scope creep, or when an issue queue needs triage before dispatch — even if the user just says \"file this\", \"make a ticket\", or \"write that up\"."
---

# Filing GitHub Issues That Agents Can Ship

Issues filed here feed the multi-agent pipeline (claimed per gh-issue-locking,
dispatched per dispatching-subagents, scheduled per orchestrating-slots,
merged per driving-prs-to-merge; labels per gh-issue-labels). This skill
covers both ends of intake: writing groomed issues, and recon-triaging stubs.

## Project bindings

Define these once in the adopting project's CLAUDE.md, alongside the sibling
skills' shared bindings (integration branch, worktree convention, toolchain
bootstrap, CI gate names, bot reviewers, operator logins). The body refers to
them by placeholder; example values are illustrations, not requirements.

| Binding | Meaning | Example |
|---|---|---|
| `<repo-slug>` | `--repo` target for `gh` commands | `acme/widgets` |
| `<type-labels>` | exactly-one type label set | `bug`, `enhancement` |
| `<priority-labels>` | exactly-one priority ladder | `priority:P0`…`priority:P3` |
| `<security-label>` | flag for authn/authz/data-isolation/OWASP-class issues | `security` |
| `<lane-labels>` | shared-surface vs isolated work | `lane:plumbing`, `lane:leaf` |
| `<component-labels>` | component/subsystem label namespace | `subsystem:*` |
| `<triage-labels>` | terminal triage states | `ready-to-dispatch`, `needs-spec-input`, `blocked` |
| `<claim-label>` / `<hold-label>` | active-work lock (gh-issue-locking) / operator hold (gh-issue-labels); neither applied at filing | `agent-claimed` / `do-not-dispatch` |
| `<breaking-change-labels>` | CI breaking-change acknowledgment gates, if any | `db:…` / `api:breaking-change-acknowledged` |
| `<traceability-scheme>` | requirement-ID format + doc location, if formal traceability exists | `REQ-<PREFIX>-<N>` in `docs/specs/` |
| `<shared-surfaces>` | enumerated contention-prone files defining the plumbing lane | DB schema, new migrations, API schema, design tokens, shared-types package, root manifest/lockfile |
| `<crown-jewel-invariant>` | hardest invariant; mentioning it auto-escalates to P0 | "tenant isolation" |
| `<subsystem-tiers>` | security-critical (auto-P0) / core (partial → P1) / deferred (auto-stall without logged decisions) | auth/payments vs core feature modules vs deferred/experimental areas… |
| `<decision-records>` | where architectural decisions for deferred areas are logged | `docs/specs/_subsystems/` |
| `<design-source>` | UI source of truth a UI spec must anchor to | `design-system/` folder |
| `<cheap-model>` / `<default-model>` | recon model tier / escalation tier | `haiku` / `sonnet` |
| `<second-tracker>` | optional second tracker + ref syntax; route by where work was filed | Jira, `Refs PROJ-N` |

Single-tracker projects drop `<second-tracker>`. Projects without formal
traceability drop `<traceability-scheme>` but keep the explicit "no requirement
needed" escape described below.

## Core principle: the issue body IS the spec

Dispatch briefs point at the issue body; they never paraphrase it — paraphrases
go stale the moment the issue is edited, and stale paraphrases have caused
shipped rework. So the body must clear this bar: **a sub-agent can pick the
issue up and ship a PR without asking the operator anything**. Every skipped
section becomes a clarifying-question round-trip; every round-trip is a lost
dispatch cycle. Keep design debate OUT of the body — agents treat body text as
instructions, so embedded debate becomes accidental requirements. Spec goes in
the body; discussion in comments.

## The six mandatory sections

### 1. Title

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

A markdown checklist where each item is **independently testable**. The
implementing agent self-verifies against this list before opening the PR, so
an untestable criterion ("works well") is a no-op.

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
- **Reference implementation** — "mirrors PR #N's pattern" when a shipped PR
  established the approach; prevents pattern divergence across the codebase.
- **Dependency** — `Depends on #N` when another PR must land first; recon's
  BLOCK rule consumes this exact phrase mechanically.

## Labels at filing time

- Exactly one of `<type-labels>`, exactly one of `<priority-labels>` — the
  exactly-one constraints make `gh issue list` filterable and the dispatch
  queue deterministic.
- `<security-label>` if the issue touches authn/authz, data isolation, or an
  OWASP-class concern.
- A plumbing `<lane-labels>` tag if the work is primarily on a shared surface
  (recon can also set this later).
- `<breaking-change-labels>` pre-flagged if the spec itself calls for breaking
  schema/API/DB changes — discovering the CI acknowledgment gate mid-PR stalls
  the merge; the implementer can add it later, but filing-time is cheaper.

Do not apply `<claim-label>` at filing time — claiming happens when work
starts, per gh-issue-locking; premature claims hide filed-but-unworked issues
from the dispatch filter and show phantom ownership to concurrent operators.
`<hold-label>` is operator-only (see gh-issue-labels) — never apply it.

## Second-tracker routing

When the project uses `<second-tracker>` alongside GitHub Issues, route by
where the work was filed: GitHub issues → GitHub; second-tracker items → second
tracker. Never duplicate the same piece of work across both trackers.

The second tracker here is Jira — for the Jira-native filing flow, see the
jira-issue-filing skill. In PR bodies, cross-reference the second tracker with its
key syntax (e.g. `Refs PROJ-N` for a Jira ticket). GitHub issues close via the
close-on-merge sweep (see gh-issue-locking); second-tracker items transition
per that tracker's own workflow (typically resolved/done on PR merge, but check
project policy).

Single-tracker projects omit the `<second-tracker>` binding and this paragraph.

## One theme per issue; batch filings are independent

Split multi-theme reports into separate issues before filing, not after
dispatch — integration throughput is fastest with small focused PRs, and a
multi-theme issue forces one bloated PR or an agent guessing where to stop.
Batch-file distinct items as separate issues (parallel `gh issue create` is
fine), each with a fully independent body, number, and lock surface; shared
lock comments or cross-issue state break per-issue ownership for
independently-filed issues — the only sanctioned shared-lock shape is the
bundled-issue protocol in gh-issue-locking (one lead lock, sibling
`bundled_with` pointers).

## Cross-references, duplicates, and follow-ups

- **Issue spawned by another issue:** put `Refs #<source>` at the top of the
  new body AND post a forward-link comment on the source ("filed as #N") —
  bidirectional links survive either issue being closed.
- **Refining an existing issue:** comment on it rather than filing a sibling,
  unless scope or owner is materially different — near-duplicate siblings
  split the discussion and the claim/lock surface across two numbers.
- **Pre-filing search:** search open issues for the same symptom, and check
  merged PRs — when PRs land on a non-default integration branch GitHub never
  auto-closes linked issues, so "open" does not mean "unfixed" (see
  driving-prs-to-merge for the close-on-merge sweep).
- **Two operators filed the same thing:** the later filer yields ("Duplicate
  of #X — closing in favour of that."), unless the original is low-quality —
  then enrich the original and close your own as the dupe. The deterministic
  rule avoids negotiation; the exception preserves the better content.
- **Work discovered mid-task:** file a follow-up (full six sections, `Refs`
  back to the current issue/PR) instead of expanding the current PR.
  Imperative operator phrasing ("update X") during a diagnostic session means
  "file an issue specifying X" unless implementation is explicitly delegated.

## Filing anti-patterns (each named because it happened)

- "X is broken" with no code refs or screenshots — forces twenty questions.
- Design debate in the body — becomes accidental requirements; use comments.
- One issue spanning many themes — throttles the whole merge pipeline.
- The same issue filed under multiple type labels "hoping one matches".
- Claiming (`<claim-label>` or assignee) at file time — see above.

---

# Recon: triaging stub issues into dispatchable work

Not every issue arrives at the grooming bar. Recon is the cheap, sandboxed
classification pass that moves a stub to exactly one terminal triage state.

## The label-encoded triage state machine

An issue is **untriaged** when it carries a `<component-labels>` label but
none of the `<triage-labels>`. One recon pass moves it to exactly one terminal
state:

| Terminal state | Mandatory companions | Must NOT have |
|---|---|---|
| `ready-to-dispatch` | lane label + priority label | — |
| `needs-spec-input` | a multiple-choice question comment | lane or priority labels |
| `blocked` | a comment naming the dependency | `ready-to-dispatch` |

Encoding state in labels makes the queue queryable with one `gh issue list`
call and readable by multiple operators without shared memory. The companion
requirements make partial classification *detectable*: a terminal label
missing its companions is corrupted state, and a `needs-spec-input` issue
carrying lane/priority labels gets picked up by careless filters as if ready.
The dispatch filter selects only `ready-to-dispatch` — but labels go stale (in
practice a stale label persisted after another operator claimed,
double-locking four issues), so verify the assignee field is empty immediately
before locking; see gh-issue-locking. The `ready-to-dispatch` bar is the filing
grooming bar: the body alone lets an agent ship with zero round-trips.

## Why recon runs on `<cheap-model>` — and when it must not

Cheap models ship subtle errors on open-ended work; they are safe only when
the blast radius is capped and the task is mechanical. Recon qualifies only
while all three properties hold:

1. Tool access hard-restricted: read-only repo access plus label/comment
   mutations on a single issue.
2. Decision tree concrete and short (five rules, stop at first match).
3. Output is a single contract line validatable at a glance.

If a recon brief violates any property — e.g. it also asks the agent to
rewrite the issue body — escalate that dispatch to `<default-model>`.

## Sandbox: allowed and forbidden operations

Allowed:

```bash
gh issue view <N> --repo <repo-slug> --json title,body,labels,comments
gh pr list --repo <repo-slug> --state open --search "Closes #<N>"
gh pr list --repo <repo-slug> --state open --label lane:plumbing
git grep …   # plus git log, gh issue list — read-only queries
gh issue edit <N> --repo <repo-slug> --add-label <label> / --remove-label <label>
gh issue comment <N> --repo <repo-slug> --body "…"
```

Forbidden — on attempting any of these, stop and emit `RECON-ERROR: <what was
attempted>`; silent recovery hides sandbox escapes from the orchestrator:

- Edit or Write any repo file.
- Create issues or PRs; close this or any other issue.
- Mutate any other issue or any PR.
- Add or remove assignees — assignment is the lock-time ownership signal owned
  exclusively by the orchestrator (see gh-issue-locking); a recon agent setting
  one forges a claim that other operators will honor.

## The decision tree — apply in order, stop at first match

Ordering encodes precedence: an ambiguous spec stalls *before* lane/priority
effort is spent; lane must be known *before* the lane-contention check; and
priority is computed only for issues that will actually dispatch.
Stop-at-first-match keeps the task inside a cheap model's reliability envelope.

1. **SPEC-CLARITY → `needs-spec-input`** if: hedge words ("appropriate",
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
3. **BLOCK → `blocked`** if: the body says `Depends on #N` and #N is open; OR
   the spec references another requirement mapping to an open issue (chase ONE
   transitive hop only — deeper chains blow the token budget and rarely change
   the verdict); OR it is plumbing-lane while another plumbing PR in flight
   touches the same file — parallel shared-surface PRs (schema, migrations,
   tokens) reliably collide on merge.
4. **PRIORITY** (only if reached): P0 if the subsystem is security-critical
   per `<subsystem-tiers>` OR the text mentions `<crown-jewel-invariant>` OR
   it is a bug with severity high/critical. P1 if partially implemented AND in
   a core-tier subsystem. P2 otherwise.
5. **CLEAR** → add `ready-to-dispatch`. Done.

## Spec-stall comments are multiple-choice, never open-ended

Open-ended questions push spec-writing back onto the operator and stall the
queue indefinitely; multiple-choice with a write-in turns the reply into a
one-token unblock that recon mechanically consumes on re-run. One comment:

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

Then add `needs-spec-input` and STOP — no lane or priority labels.

## Output contract and orchestrator validation

The recon agent ends with exactly one line:

```
RECON OK #<N>: ready-to-dispatch lane:<L> priority:<P>
RECON OK #<N>: needs-spec-input
RECON OK #<N>: blocked (#<dep>)
RECON-ERROR: <message>
```

Validate this line against the labels actually set (`gh issue view <N> --json
labels`) — agents can report `RECON OK` without performing the mutations.

## Budgets and fan-out

- **Token budget: 5K output per issue — hard.** If exceeding, emit
  `RECON-ERROR: token budget exceeded`; never silently truncate — a truncated
  classification looks like a verdict but is not one.
- **Wall clock: ≤ 60s per issue — soft.** Overrunning is not a failure, just a
  signal the brief needs tightening. Do not conflate the two.
- **Fan-out:** one issue per dispatch (mutation surface matches the sandbox);
  up to 5 in parallel per round, in one message per dispatching-subagents —
  the cap bounds label churn and the orchestrator's validation load.

## Recon brief template

Copy `references/recon-brief.md` verbatim at dispatch time, filling `<>`
placeholders — paraphrased briefs drift; an identical template makes
cheap-model fan-out safe and results comparable.

Label bootstrap (the `<triage-labels>`, `<lane-labels>`, etc. used above) is
provisioned by the gh-issue-labels skill's `scripts/bootstrap-labels.sh`.

## Token discipline: caveman working, humanizer for the story

Your recon, triage, and coordination chatter runs in the same high-volume orchestration loop as the sibling skills — operate in **caveman mode** (load the `caveman` skill) for that working output to conserve tokens, keeping all machine-precise content byte-exact (labels/fields, JQL, `gh`/MCP commands, the `RECON OK` / `RECON-ERROR` contract, `file:line` refs, code blocks).

But the issue/ticket body IS the story — the durable artifact a human reads and an agent implements from. NEVER write it in caveman. Draft it in full natural prose, then run it through the `humanizer` skill before filing so it reads human-written, not AI-generated (it strips inflated phrasing, rule-of-three, em-dash overuse, vague attributions, and filler). Humanize the Symptom and Desired-behaviour narrative; leave the verified `file:line` evidence, the acceptance-criteria checklist, and the labels/fields exactly as specified — precision there beats prose.
