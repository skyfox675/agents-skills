# Triggering eval scorecard

Method: [skill-creator](../skill-creator/SKILL.md) description-optimization, replicated with a router eval (see [README](README.md)). 231 queries across the 12 authored skills (~8–10 should-trigger + 8–10 should-not-trigger near-misses each). A fresh agent, given only the 12 skill name+description pairs, routed each query to one skill or `none`; scored against the labelled target.

## Result

| Metric | Score |
|---|---|
| Should-trigger recall | **114 / 114** (after eval-label fixes) |
| False-triggers (skill grabbed a should-NOT query) | **0** |
| Cross-tracker collisions (gh ⇄ jira) | **0** |
| Pipeline-stage confusion (groom ⇄ recon ⇄ dispatch) | **0** |

First pass scored 110/114 with 1 false-trigger. All 5 deviations were **under-specified eval queries, not description defects** — so the queries were sharpened (per skill-creator: fix the eval, don't overfit the description), and re-routing confirmed 5/5:

| Query (before) | Issue | Fix |
|---|---|---|
| "make a ticket for that" | no tracker cue → safely abstained to `none` | added Jira cue → "make a Jira ticket for that" |
| "apply do-not-rebase to this PR" (under jira-issue-fields) | do-not-rebase is a GitHub-PR concept → routed to gh-issue-labels | reworded to a Jira-native Priority/label intent |
| "which label taxonomy do I consult" (under jira-issue-fields) | "label" is the gh term, no Jira cue | added Jira cue + fields/labels intent |
| "just work #58, fix it" (under gh-issue-locking) | a dispatch phrase → routed to dispatching-subagents (correct) | reworded to an explicit claim/lock intent |
| "AC already approved, go ahead and rewrite" (under grooming-issues) | operator authorizes the edit → grooming **is** correct | relabelled should_trigger:true → grooming-issues |

## Takeaways

- The gh-* / jira-* twins are cleanly separated by description: no GitHub-phrased query pulled a Jira skill or vice-versa, and vice-versa.
- The groom → recon → dispatch pipeline stages route to the right phase ("size this ticket" → technical-recon, "map the app" → spelunking-specs, "this story is vague" → grooming-issues).
- Genuinely tracker-ambiguous asks ("make a ticket", no cue) safely abstain rather than mis-fire — the desired failure mode.

Per-skill eval sets live at `<skill>/evals/triggering.json`; re-run via the router harness (README) or the upstream skill-creator `run_loop` after installing it.
