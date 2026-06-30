---
name: ci-flake-hunting
description: The authoritative method for hunting, root-causing, and fixing CI flakes so the merge queue stops ejecting correct PRs and churn drops. A flake is a test that fails then passes on retry with NO code change explaining it — every red speculative merge-queue build ejects a correct PR and disarms its auto-merge, so a live flake taxes every PR behind it. Encodes the loop — MINE CI history for real flakes → REPRODUCE harsher-than-CI → ROOT-CAUSE the real mechanism (hydration/render race, settle race, mock-order, loading-state race, click-through fragility) → FIX FORWARD (test or component, never mask) → VERIFY by re-running many times → UNSTICK the PRs the flake stranded → REPEAT. And how to tell a true code flake from transient INFRA (CDN/mirror outage, expired token mid-suite, rate-limit/WAF, external-service cap, cloud state-lock, CI-provider billing/outage, upstream bump) which must NOT be code-fixed. Use whenever chasing CI instability, "deflake this spec", "CI keeps ejecting my PR", "is this a flake or real", a shard that intermittently reds the queue, or running the ci-flake-hunter lane. Distinct from ci-speed-hunting (which owns slow-but-green jobs — flake never touches timing/sharding).
---

# CI Flake Hunting (authoritative deflake method)

A serial merge queue ejects the correct PR at the front the moment a flaky speculative build reds, AND disarms its auto-merge — the PR drops to a green-but-unqueued state and sits idle. So every live flake is a tax on *every* PR behind it. Killing one high-frequency flake measurably raises queue throughput; this is among the highest-leverage CI work there is.

This skill pairs with the `ci-speed-hunting` skill (which owns CI *latency* — slow-but-green jobs; it never touches red/flaky jobs, you never touch timing/sharding) and the `test-driven-development` skill where available (whether the resulting test is well-shaped), and builds on the merge-queue mechanics in `driving-prs-to-merge`. Where a "make it pass" instinct conflicts with this skill's fix-forward rule, this skill wins.

## Project bindings

Project-agnostic; the adopting project defines these (the full set lives in `driving-prs-to-merge`). Used here:

| Placeholder | Meaning |
|---|---|
| `<owner>/<repo>` | GitHub repository slug |
| `<integration-branch>` | Branch PRs target and the queue merges into |
| `<ci-workflow>` | The per-PR CI workflow file that gates merge |
| `<e2e-suite>` | The end-to-end / browser test job or matrix where most flakes surface |
| `<e2e-runner>` | The E2E runner and its repeat/stress flags (e.g. Playwright `--repeat-each`, Cypress `--repeat`) |
| `<prod-build-recipe>` | How CI builds the app for E2E (production build + the E2E env), reproduced locally |
| `<merge-strategy>` | Allowed strategy flag — and whether a **merge queue** governs the branch |

## The one rule

**A failing test is a real signal until proven otherwise.** Never `test.skip`, never bump a retry count, never add a bare fixed-duration sleep, never disable a shard, never widen a flaky assertion to "whatever passes". You either (a) prove it is transient INFRA and re-run, or (b) find the real race and fix it forward. There is no third option.

## Step 0 — Is it even a code flake? (classify first, fix second)

Before reproducing anything, decide the bucket. Fixing the wrong bucket wastes hours.

**TRANSIENT INFRA — do NOT code-fix, just re-run** (environmental, not in your code). Generic signature classes:

| Signature class | Typical cause |
|---|---|
| Package-mirror / CDN fetch fails mid-job (`temporary error`, DNS, 5xx from a registry) | upstream mirror or CDN blip — the real step never ran |
| Auth token "expired"/`exp` failures across many jobs at once | a shared test token aged out mid-suite |
| Blanket 403/429 on all requests to one host | rate-limit or a WAF/allow-list rule change, not your code |
| A timeout pinned at a suspiciously round external limit (~Ns cap) | an external-service or function timeout cap, not a regression |
| State-lock / "could not acquire lock" on a shared cloud stack | a concurrent-deploy lock race |
| Jobs fail in seconds at "set up" / artifact download with billing/quota errors | CI-provider spending-limit or platform outage — operator-only |
| A required-version/lint gate reds EVERY PR right after an upstream release | an upstream major bump landed on the base branch |

For infra: confirm the signature in the failed job log, re-run the failed jobs (`gh run rerun <id> --failed`), and move on — open NO code PR. If `gh run rerun` says "cannot be rerun; workflow file may be broken", the run is a merge_group/superseded check — re-trigger by refreshing the PR branch (`git fetch origin <integration-branch> && git merge origin/<integration-branch> --no-edit && git push`), which fires a fresh `<ci-workflow>` run.

**REAL CODE FLAKE — root-cause + fix forward** (the rest of this skill). Symptoms: a shard reds intermittently, passes on retry, and the failing spec has render/timing/network-mock surface that this change touches — or that flakes regardless of the change (a latent race).

## Step 1 — MINE: find the actual high-frequency flakes

Don't guess. Pull the data, rank by frequency, fix worst-first. A test runner that retries usually emits a **`flaky`** summary line when a test fails then passes; CI that forbids flaky still exits non-zero. Grep run logs for `flaky` and the spec name. A merge_group red where the SAME sha passed at the PR-checks level is a flake that only surfaces under the speculative build's timing — the queue-killers. Set `REPO=<owner>/<repo>`.

**(a) Recent FAILED jobs across workflows** (the wide net):
```bash
gh run list --repo $REPO --status failure --limit 40 \
  --json databaseId,workflowName,event,headBranch \
  -q '.[] | "\(.databaseId)\t\(.workflowName)\t\(.event)\t\(.headBranch)"'
gh run view <runId> --repo $REPO --log-failed \
  | grep -iE "flaky|✘|✗|expect\(|Timed out|TimeoutError|Error:|retry #|<spec-name>"
```

**(b) Per-PR gate failures** (`<ci-workflow>` — where most live flakes show):
```bash
gh pr checks <PR> --repo $REPO --json name,state,link \
  -q '.[] | select(.state=="FAILURE" or .state=="ERROR") | "\(.name)\t\(.link)"'
```

**(c) merge_group failures** (the queue ejections — highest-leverage flakes):
```bash
gh run list --repo $REPO --event merge_group --status failure --limit 30 \
  --json databaseId,headBranch -q '.[] | "\(.databaseId)\t\(.headBranch)"'
# Cross-check: did the SAME sha pass at the PR gate? If yes → flake-only-in-queue (a top target).
gh run list --repo $REPO --workflow <ci-workflow> --json headSha,conclusion \
  -q '.[] | select(.headSha=="<sha>") | .conclusion'
```

**Raw `gh api`** for fields the CLI doesn't expose — the check-run annotations that quote the failing assertion, and step-level conclusions + durations:
```bash
gh api "repos/$REPO/commits/<sha>/check-runs" \
  -q '.check_runs[] | select(.conclusion=="failure") | "\(.name)\t\(.html_url)"'
gh api "repos/$REPO/check-runs/<checkRunId>/annotations" -q '.[] | "\(.path):\(.start_line)\t\(.message)"'
```

Build a ranked list: `{spec, test, shard, frequency, last-seen}`, worst-first.

## Step 2 — REPRODUCE harsher than CI

A flake you can't reproduce isn't root-caused — it's guessed. Make it fail ON DEMAND.

- Use the **production build**, not the dev server or unit harness — purge/minification, animation/RAF timing, and synthetic events differ. Reproduce CI's build locally via `<prod-build-recipe>`, then run the suspect spec under stress with your runner's repeat flag (`<e2e-runner>` with e.g. `--repeat-each=20`).
- **Amplify the race**: raise the repeat count, change worker count to perturb scheduling, throttle CPU, run under load. If it passes 20× clean locally but reds in CI, you have NOT reproduced it — change the timing knob until it fails. Hydration/animation/mock-order races hide behind a fast local machine.

## Step 3 — ROOT-CAUSE the real mechanism

Name the actual race. The recurring mechanism classes:

- **Async cache/store hydration vs network** — a client cache hydrates asynchronously while the network result also lands → double render / stuck busy state / empty list. Fix: make the non-deterministic subsystem deterministic in E2E (gate it off / use a deterministic exchange) so the order is fixed.
- **Duplicate dispatch from a mock** — a mock that replays in the wrong order dispatches twice.
- **Accessibility/settle race** — an a11y or content scan runs while the container is *visible* but its inner content/animation hasn't settled → intermittent violation. Fix: await the settled inner element BEFORE scanning.
- **Loading-state races** — asserting on content before the loading state clears. Fix: wait the real signal (element present + not busy), never a fixed sleep.
- **Click-through fragility** — a test that clicks through N screens to reach a target accumulates timing fragility; navigating directly to the target route is deterministic.

Write the mechanism down in one sentence before touching code. If you can't, you haven't found it.

## Step 4 — FIX FORWARD (test OR component — whichever is the true cause)

- If the **test** races (asserts too early, wrong wait, brittle path) → fix the test: deterministic waits on real signals, direct navigation, gate non-deterministic subsystems in E2E. The behaviour under test stays covered.
- If the **component** races (a genuine hydration/render bug users could hit) → fix the component. A flake is sometimes a real bug wearing a costume.
- NEVER mask: no skip, no fixed-duration sleep as a "fix", no retry bump, no assertion loosened to noise, no shard disabled.
- Honor `test-driven-development` where available: the test must still verify behaviour through the public interface.

## Step 5 — VERIFY (prove it's dead)

Re-run the previously-flaky spec **MANY** times in a production build — repeat-each ≥ 20 (more for high-frequency flakes), 100% green, **zero** `flaky` lines. One green run is not proof. If it still flakes, you fixed the wrong thing — back to Step 3.

## Step 6 — SHIP

One PR per coherent root-cause cluster (don't bundle unrelated flakes — keep each reviewable). Conventional commit, e.g. `test: deflake <spec> — <mechanism>` or `fix: <root-cause> — deflake <spec>`. Base `<integration-branch>`, hooks intact, auto-merge (`gh pr merge --auto <merge-strategy>`; omit the strategy flag under a merge queue). Never `--admin`/`--no-verify`/force past the queue. Then Step 7, then back to Step 1 with refreshed history — a CONTINUOUS lane.

## Step 7 — UNSTICK the strays your fix just freed (AFTER the fix merges)

Killing the flake on the integration branch is only half the job. While it was live, that flake **ejected other correct PRs** from the merge queue and **disarmed their auto-merge**. Those PRs now sit blocked on a **stale failed run from hours ago**, and nothing re-triggers them automatically. The queue looks jammed; it isn't — it's full of PRs blocked on history.

**Once your fix PR has MERGED**, sweep every open PR whose only red is the shard you just fixed: re-run its stale failed `<ci-workflow>` run (`gh run rerun <id> --failed` — cheap, no checkout), and as reruns go green, re-arm any PR that flips to green-but-unarmed (`gh pr merge <pr> --auto`, no strategy flag under a queue). This is the re-arm-after-ejection mechanic the `pr-checks` and `pr-comments` watcher lanes own — coordinate with them rather than duplicating, and follow the discriminator in `driving-prs-to-merge` (a PR with merge_group history for its current head SHA was ejected; one with none was never armed — leave that to the comments lane).

**Two cautions, both load-bearing:**
- **Verify the flake is actually fixed FIRST** — confirm zero `merge_group` failures on the fixed shard *after* your fix's merge time. Re-running before the fix lands just re-catches the flake.
- **Do NOT re-arm in a tight loop.** Each re-arm adds PRs to the queue, which re-forms the speculative chain and CANCELS in-flight merge_group builds → zero merges forever (symptom: repeated `completed/cancelled` merge_group runs). Arm a wave, let the queue build + merge it undisturbed, THEN arm the next wave. A queued PR showing no auto-merge request is normal (the queue consumed it), not a disarm.

## Good vs bad flake handling (concrete)

**BAD — masking (never). Each makes CI green while the bug lives on:**

```ts
test.skip('list renders after load', async () => { ... })   // ❌ coverage silently lost
test.describe.configure({ retries: 3 })                      // ❌ flake just hides behind retries
await page.waitForTimeout(2000)                              // ❌ blind sleep — races the race, slows every run
await expect(rows).toHaveCount(/* anything that passes */)   // ❌ widened until it asserts nothing
```

**GOOD — root-caused, deterministic, behaviour still covered:**

```ts
// ✅ async store-hydration race → make the non-deterministic subsystem deterministic in E2E
const cacheExchange = isE2EMode ? deterministicExchange : normalExchange
// ✅ loading-state race → wait the REAL signal, not a timer
await expect(list).not.toHaveAttribute('aria-busy', 'true')
await expect(firstRow).toBeVisible()
// ✅ settle race → await inner content settled BEFORE the scan
await expect(canvasWrapper).toBeVisible()
await page.waitForFunction(() => !document.querySelector('[data-animating="true"]'))
const results = await scan()
// ✅ click-through fragility → navigate directly to the target route
await page.goto(`/path/to/${id}`)        // not: click home → list → row → tab
```

**GOOD — correctly NOT fixing infra** (Step 0): a scan job reds with a package-mirror `temporary error` → the real step never ran, code is clean. Re-run the failed job, open NO code PR. **BAD** — "fixing" that infra red by editing build config: wastes time, hides a future real finding, and the next run is green anyway. Classify before you touch code.

## Token discipline (caveman)

You run inside the caveman-mode `ci-flake-hunter` agent. CI logs are huge — the main context risk. Load the `caveman` skill and conserve:

- **Never** dump a full `gh run view --log` into context. Always pipe through `grep -iE` with the smallest decisive pattern (spec name, `flaky`, `✘`, `Timed out`). Quote only the one failing assertion line.
- Delegate log trawls + selector hunts to a read-only cheap-tier sub-agent (`caveman:cavecrew-investigator`) and keep only its conclusion.
- Status lines: terse fragments — `mined 12 reds; top=list ops(4/6) → store-hydration race → deflake PR #x (20/20 green)`.

Caveman compresses *prose only* — `gh` commands, selectors, assertion lines, spec names stay byte-exact. Commit messages + PR bodies: normal prose, through the `humanizer` skill.

## The bar — flake vs regression

Before calling something a flake, satisfy ALL three:
1. **Reproduced and explained** as a race (Steps 2–3), OR matched to a known transient-infra signature (Step 0).
2. The failing spec has **zero render-surface overlap** with the change under test (for a PR-eject), OR it flakes on the integration branch independent of any change (latent).
3. **Other PRs merge through the same shard** — it's not a hard wall.

If any fails, treat it as REAL and fix the code. A "flake" you re-run forever without root-causing is an unfixed bug.

## Singleton lane — within flake-hunting only

There is **exactly one** `ci-flake-hunter` active at a time. Two collide on the same flakes, double the RAM of repeat-each production builds, and race on branches. If you are this lane and find another already running, defer to it.

But "singleton" scopes to flake-hunting **only** — you routinely run **alongside** the `ci-speed-hunter` (owns latency: sharding, caching, tiering — never touches red/flaky jobs) and the PR watcher lanes (`pr-checks`, `pr-comments`, `pr-cleanup`). You may both edit the CI workflow or shard scripts, so `git fetch origin <integration-branch> && git merge origin/<integration-branch> --no-edit` before every push and keep your diff strictly the flake fix — leave the speed knobs to speed. **Don't double-fix:** before a hunt, check whether another hunter already has an open PR against the spec/component/workflow you're about to touch (`gh pr list --search "deflake in:title"`); if a file is claimed, stand down and pick the next flake.
