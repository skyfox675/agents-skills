---
description: "The full-stack deep dive — /jira-issue plus BOTH the live-browser and read-only AWS diagnosis phases, correlated: reproduce the symptom as the signed-in user, capture the failing request, then chase that exact request through the cloud (edge, logs, service, data) until the fault layer is found. Use for symptoms nobody can place — \"it fails and we don't know which layer\". Example — /jira-issue-use-aws-browser \"file export > Download\" clicking Download 403s on staging effort:max"
argument-hint: <breadcrumb> <description of the issue> [model:tier] [effort:level]
agent: agent
---

# /jira-issue-use-aws-browser — file a groomed Jira issue with a correlated full-stack diagnosis

Arguments: `${input:args}` — parsed exactly like `/jira-issue` (see `jira-issue.md`): breadcrumb first, optional `model:`/`effort:` tokens anywhere, the rest is the description. The filing flow is `/jira-issue`'s, unchanged. The deep-dive phases and ALL their ground rules come from the two siblings and apply verbatim here:

- `jira-issue-use-browser.md` (the **browser-diagnosis** skill) — context isolation, careful-user mutation rules, dialog hazard, residue tracking, token/cookie redaction, rabbit-hole guard, on whichever browser MCP is connected (Chrome, Playwright, or Cypress).
- `jira-issue-use-aws.md` — identity-first, the read-only verb allowlist, `lambda invoke` is forbidden, secrets stay sealed, AccessDenied is a finding.

What this command adds is the **correlation method** — neither side alone finds the faults that live between layers. (Tracking work in GitHub instead? Use `/gh-issue-use-aws-browser`.)

## The correlated dive

Work the stack as one trace, in this order:

1. **Codebase recon first** (per `/jira-issue`): map the breadcrumb to the components, the API operations they call, and the cloud resources behind them. This map tells you what to watch on both sides.

2. **Reproduce in the browser** (per `jira-issue-use-browser`): perform the user's steps in your own tab group and capture the failing request — method, URL/operation, payload, status, response body, and above all any **request/correlation IDs and the precise timestamp**. A fresh repro matters because it generates evidence you can find in logs that are still hot. Record the repro GIF while you're there.

3. **Chase that exact request through AWS** (per `jira-issue-use-aws`): take the correlation ID/timestamp into the logs of each hop the recon map predicts — edge (4xx/5xx, WAF, CDN), service (handler logs around the timestamp), then data (does the row/object/queue message the code expects actually exist, with the key shape the code queries?). CloudTrail for config drift when behavior changed without a deploy.

4. **Bisect by boundary.** At every hop ask: did this layer receive what the previous layer claims it sent, and did it emit what the next layer expected? The boundary where expectation diverges from observation **is** the root cause. Classic splits: client sent the wrong thing (frontend bug), wire rejected it (edge/auth/WAF), service erred (handler logs), service succeeded but data was wrong (mapper/query/state bug), everything worked but the client dropped the result (client-side cache or response-shaping bug).

5. **Mock to confirm, not to guess.** Once you suspect a layer, prove it: stub the API response in the browser to confirm a rendering fault, or re-run the failing read against the data store to confirm a state fault. One confirming probe beats three more hypotheses.

6. **Dispatch as sub-agents when substantial** (per dispatching-subagents): either one diagnostic agent walking the whole trace, or a browser agent and an AWS agent in parallel — in the parallel case YOU own the correlation: give both the same correlation IDs/time window, and join their findings before drafting. Diagnostic agents change no code and no cloud state; each browser agent gets its own tab group.

## Evidence into the issue

The evidence section carries the **trace table** — one row per hop: layer, what was expected, what was observed, the proof (redacted request/response slice, log excerpt with ARN + account/region, or data-store read). Then the verdict: the fault layer, stated plainly, with the one boundary where the trace broke. Classify it (frontend / wire / edge / service / data) — that classification drives the lane label and is what makes the issue dispatchable to the right kind of fix. Operator-action items and residue get their own lines, per the siblings.

Everything else — dedupe etiquette, model/effort pins, never-assign-at-filing, the final report — follows `/jira-issue` exactly.
