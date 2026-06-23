# Skill triggering evals

Each authored skill ships a triggering eval set at `<skill>/evals/triggering.json`, built with the [skill-creator](../skill-creator/SKILL.md) description-optimization method: per skill, **8–10 should-trigger** queries (varied phrasings of the real intent) and **8–10 should-not-trigger** near-misses (keyword overlap, but a *different* skill — usually a sibling — is correct, or none). The point is not "does an obvious query fire" but **disambiguation**: a GitHub query must not trigger the Jira twin, "size this ticket" must hit `technical-recon` not `spelunking-specs`, etc.

File format (one JSON array per skill):

```json
[
  {"query": "...", "should_trigger": true,  "expected": "<this-skill>",   "note": "why"},
  {"query": "...", "should_trigger": false, "expected": "<sibling|none>", "note": "why"}
]
```

## Running the eval

The upstream skill-creator ships `scripts/run_loop` (60/40 train/held-out split, 3 runs per query for a stable trigger rate, auto-proposes description fixes). It is **not** vendored here — this repo only holds the skill-creator pointer. To use it directly, install it (`/plugin install example-skills@anthropic-agent-skills`) and point `--eval-set` at a skill's `evals/triggering.json`.

Without it, the equivalent check used in this repo is a **router eval**: give a fresh agent the full catalog of skill `name`+`description` pairs and one query, ask which single skill it would invoke (or none), and score the choice against `expected`. Run the should/should-not set per skill; a skill passes when its should-trigger queries route to it and its near-misses route to the labelled sibling/none. Failures point at the exact `description` wording to fix (then re-run the failing subset).

Targets: should-trigger rate ≈ 1.0 on the labelled skill; **zero cross-tracker collisions** (gh ⇄ jira); pipeline-stage queries (groom → recon → dispatch) land on the right stage.
