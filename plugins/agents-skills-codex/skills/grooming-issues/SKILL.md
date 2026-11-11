---
name: grooming-issues
description: "Interactively groom an issue that is not yet ready for development — engage the engineering/project lead with questions to assert the intent, scope, and direction of the ask until ≥90% certain the written story reflects what they want, then fill the issue body to the six-section groomed anatomy. Captures the WHAT and WHY (product/spec intent), upstream of the technical-recon skill which decides the HOW and the LoE. Hard rule: never modify acceptance criteria that have already been written unless the operator explicitly asks — existing AC is an approved contract. Use whenever a lead hands you one or more raw, vague, or half-written issues to 'groom', 'flesh out', 'clarify', 'tighten the story', or 'get ready for tech review' before any technical recon or dispatch; asks via an interactive question tool when one is available, otherwise via emoji-answerable issue comments, and resumes on rerun once the lead answers."
---

# Grooming Issues: capture the intent before anyone sizes or builds it

An issue can exist — a title, a paragraph, maybe a stakeholder's wish — long before it is buildable. Grooming is the pass that turns that into a story the team can trust: through questions to the engineering/project lead, it pins the intent, scope, and direction until the written issue **faithfully reflects the ask**, then writes that into the body in the six-section groomed shape. It captures the *what* and *why*. It deliberately does **not** decide the *how* or the cost — that is the technical-recon skill, which runs next.

The pipeline: a raw issue → **grooming** (this skill: intent to ≥90%, body groomed) → **technical-recon** (dev-side approach + LoE) → dispatch (per the orchestrating-slots and issue-locking skills). Grooming hands a clean story to recon; recon hands a sized, vetted issue to dispatch.

Compose with the siblings: the six-section anatomy and label taxonomy come from the issue-filing skill (gh-issue-filing / jira-issue-filing); the emoji-answerable clarification loop is the same one the technical-recon skill documents (reuse its comment format and template); when grooming completes, the technical-recon skill picks the issue up.

## Project bindings

Define in the adopting project's CLAUDE.md; referred to by placeholder.

| Binding | Meaning | Example |
|---|---|---|
| `<groomed-state>` | Label/status meaning "story is groomed, ready for technical recon" | a `groomed` label, or a `Ready for Tech Review` status |
| `<needs-input-state>` | "questions are pending the lead's answers" | `needs-spec-input` |
| `<ac-section-heading>` | The heading that marks the acceptance-criteria block in the body | `## Acceptance criteria` |

Grooming reuses the issue-filing skill's body anatomy and the technical-recon skill's question channels; it adds no labels of its own beyond the two states above.

## The one hard rule: do not touch existing acceptance criteria

If the issue already has acceptance criteria written, **leave them exactly as they are** — verbatim — unless the operator explicitly tells you to change them in this run. Existing AC is a contract that stakeholders may have negotiated and approved; an agent silently rewriting, tightening, or "improving" it changes the scope of work without anyone agreeing to the change. This has shipped the wrong thing in practice.

So:

- **AC already present** → preserve it byte-for-byte. If grooming surfaces that the AC looks wrong, incomplete, or contradicts the lead's stated intent, do **not** edit it — raise it as a question (`**Decision needed: the current AC says X but you described Y — keep / replace / add?**`) and let the lead decide. Only act on AC when the operator's answer authorizes it.
- **No AC yet** → you may draft acceptance criteria as part of grooming, but each item must be independently testable (issue-filing skill), and present the drafted AC for the lead's confirmation rather than treating it as settled.
- **Operator says "rewrite the AC"** (or similar explicit instruction this run) → then, and only then, edit it; record `ac=operator-edited` in the contract and note what changed in a comment.

Everything else in the body — title, symptom/context, desired behaviour, out-of-scope, open-questions-now-resolved, traceability hint — grooming may write and improve freely toward the issue-filing anatomy.

## Reach ≥90% that the story reflects the ask

Read the issue and any linked context first, then ask the lead about whatever is undecided and material: the actual intent behind the request, scope boundaries (what's in, what's explicitly out), the definition of success, edge cases and error behaviour, affected users/surfaces, and any conflict between the existing text and what they describe. Ask until you are **≥90% confident the written story reflects what the lead actually wants** — below that, ask; do not paper over ambiguity with plausible-sounding body text.

Questions go through the same two channels as the technical-recon skill, in priority order:

1. **Interactive ask-question tool, if the run has one** — multiple-choice with a recommended option and a write-in escape, looping until ≥90%, then write the body in the same pass.
2. **No question tool** (the usual fanned-out sub-agent case) — ask via **emoji-answerable comments**: one comment per question, each option tagged with a reaction emoji the lead clicks, a one-line legend at the bottom, kept within the tracker's reaction set (GitHub allows only 👍 👎 😄 🎉 😕 ❤️ 🚀 👀). Use the technical-recon skill's question-comment template verbatim. Then set `<needs-input-state>` and stop.

**Rerun to continue (resume, not restart).** When grooming stalls on posted questions, the lead reacts/answers and reruns the groom command. On rerun, read your prior questions and the lead's reactions/replies first, fold them in, and — if now ≥90% — write the groomed body and move to `<groomed-state>`. Never re-ask an answered question; a written reply overrides a reaction.

## The sandbox

Allowed: read the issue, its comments, and linked context (lightly read the repo only for the context needed to ask good questions — deep code tracing is recon's job, not grooming's); use the interactive ask-question tool if present; post emoji-answerable question comments; edit the issue body's non-AC sections toward the groomed anatomy; set `<groomed-state>` / `<needs-input-state>`.

Forbidden — stop and emit `GROOM-ERROR: <what was attempted>`:

- Modify existing acceptance criteria without an explicit operator instruction this run (the hard rule above).
- Assert a technical approach or a level-of-effort — that is the technical-recon skill; grooming that pre-judges the build biases the estimate.
- Claim/assign the issue, write code, or open a PR.
- Mark the issue ready-to-dispatch — grooming earns `<groomed-state>`, not dispatch-readiness; technical-recon earns that.

## Verdict and handoff

| Verdict | When | State set |
|---|---|---|
| **groomed** | ≥90% on intent; body meets the six-section anatomy; existing AC preserved (or operator-authorized edits applied) | `<groomed-state>` — the issue is ready for `/gh-issue-recon` or `/jira-issue-recon` |
| **needs-spec-input** | Questions are pending the lead's answers, below the 90% bar | `<needs-input-state>` + the question comments; rerun to continue |

## Output contract

Each grooming agent ends with exactly one line:

```
GROOM <id>: verdict=groomed ac=<preserved|added|operator-edited>
GROOM <id>: verdict=needs-spec-input questions=<N> (awaiting the lead's answers; rerun to continue)
GROOM-ERROR: <message>
```

Validate against what was actually written (`gh issue view <N>` / `getJiraIssue`): the body changed, existing AC is byte-identical unless `ac=operator-edited`, and the state moved.

## Anti-patterns

- **Rewriting approved acceptance criteria** because it "reads better" — the headline failure this skill exists to prevent.
- **Grooming past a guess.** Writing confident body text over an unresolved intent question is worse than a stalled issue with clear questions.
- **Doing recon's job.** Implementation approach and LoE belong to the technical-recon skill; grooming that asserts them biases the later estimate.
- **Inventing scope.** Out-of-scope and success criteria the lead never confirmed become accidental requirements once they are in the body.

## Token discipline: caveman working, humanizer for the story

Grooming runs in the same high-volume loop as the sibling skills — operate in **caveman mode** (load the `caveman` skill) for working output (reasoning, the batch summary, status), keeping machine-precise content byte-exact (labels/fields, JQL, `gh`/MCP commands, the `GROOM` contract line, and any existing acceptance-criteria text — which is byte-exact by rule anyway).

But the body you write into the issue is the story a human reads and an implementer builds from — its prose (symptom/context, desired behaviour) is not caveman. Draft it naturally and run it through the `humanizer` skill before saving, so the groomed issue reads human-written. Leave existing AC, any `file:line` refs, and the contract line exactly as captured.
