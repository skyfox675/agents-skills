---
name: ci-speed-hunting
description: The authoritative method for hunting, diagnosing, and fixing CI SLOWNESS so the merge queue drains faster and throughput rises — the target is wall-clock latency, NOT correctness (a job that is GREEN but slow). Encodes the loop — MINE CI timing for the real long poles → DIAGNOSE the bottleneck class (under-sharded matrix, cold cache, missing/too-broad path-filter tier, serial needs-chain, redundant rebuild) → PROVE the fix keeps identical coverage → FIX FORWARD → VERIFY the before/after delta at unchanged coverage → REPEAT. And the hard line — speed comes from doing the same work faster or skipping PROVABLY irrelevant work, NEVER from deleting tests, narrowing greps, dropping shards, or removing a gate. Use whenever chasing CI latency, "CI is too slow", "speed up the checks", "why does the merge queue take so long", re-sharding an E2E matrix, adding or fixing a cache, tuning changed-paths tiering, or running the ci-speed-hunter lane. Distinct from ci-flake-hunting (which owns failures and flakes — speed never touches a red job).
---

# CI Speed Hunting (authoritative latency-reduction method)

A serial merge queue can only drain as fast as the merge-gating critical path completes, so the wall-clock long pole is a tax on *every* PR in flight. Shaving minutes off the critical path raises queue throughput for the whole team — the same leverage the flake hunter gets from killing an ejecting flake, from the other direction.

This skill pairs with the `ci-flake-hunting` skill (which owns failures, flakes, and flake-vs-infra classification — it touches RED jobs; you touch SLOW green jobs, and the two never overlap) and builds on the merge-queue mechanics in the `driving-prs-to-merge` skill. Where a "just make it faster" instinct conflicts with this skill's coverage-is-sacred rule, this skill wins.

## Project bindings

Project-agnostic; the adopting project defines these (the full set lives in `driving-prs-to-merge`). Used here:

| Placeholder | Meaning |
|---|---|
| `<owner>/<repo>` | GitHub repository slug |
| `<integration-branch>` | Branch PRs target and the queue merges into |
| `<ci-workflow>` | The per-PR CI workflow file that gates merge (e.g. `pr-checks.yml`) |
| `<summary-check>` | The rollup check whose completion the critical path ends at |
| `<e2e-suite>` | The end-to-end / browser test job or matrix (often the long pole) |
| `<merge-strategy>` | Allowed strategy flag — and whether a **merge queue** governs the branch |

## The one rule

**Coverage is sacred. Speed never costs verification.** You make CI faster by doing the *same work faster* (caching, parallelism, right-sized runners, build-once) or by *skipping work that provably cannot affect the diff* (a correct changed-paths tier). You NEVER make it faster by checking less: no deleted test, no `test.skip`, no narrowed `--grep`, no shard with fewer specs, no gate pulled from the summary check's `needs:`, no loosened assertion, no `timeout-minutes` cut so low it kills a legitimately slow run. If a change saves time by checking less, it is out of bounds — that is regressing coverage, not speeding CI.

## Step 0 — Is this a SAFE speed win? (classify before you touch a workflow)

**SAFE — same work, faster** (do these freely, they can't lose coverage):

| Lever | What it does | Risk to watch |
|---|---|---|
| Warm a cold cache | restore an artifact instead of rebuilding (package store, build cache, incremental-compile info, browser binaries) | **cache key must capture every input** — a key that misses an input serves stale artifacts |
| Re-balance a matrix | move specs from the long-pole shard to idle shards so max-shard-time drops | total specs run is unchanged; only the assignment moves |
| Build-once / share artifact | build the bundle once, fan it to N shards via an artifact | every consumer shard must get the identical artifact |
| Parallelize a serial `needs:` | a job that doesn't consume an upstream result shouldn't wait on it | the dependency must be genuinely absent, not just usually-satisfied |
| Right-size a runner | move a CPU-bound long pole to a larger runner | cost tradeoff — note it in the PR |
| Right-size `timeout-minutes` | a 20-min timeout on a 4-min job delays nothing but masks creep; tighten to a safe margin | too tight = kills slow-but-valid runs (a coverage loss disguised as speed); never below the job's real p99 |

**CONDITIONAL — skipping work** (safe ONLY if the skip is provably irrelevant to the diff):

| Lever | Safe when | Unsafe when |
|---|---|---|
| Add/tighten a changed-paths tier (a paths-filter) so a job skips on unrelated diffs | the filter glob is a **superset** of every input the job actually verifies (incl. transitive) | the filter misses a transitive input → a diff that breaks the job skips it → silent coverage hole |
| Gate a heavy job behind a cheap tier gate | the cheap gate is a strict prerequisite (a failing cheap gate guarantees the heavy job would fail too) | the heavy job can fail independently of the gate |

**OUT OF BOUNDS — not a speed fix, it's a coverage cut** (never): deleting/skipping tests, narrowing `--grep`, dropping a shard's specs, removing a job from the summary check's `needs:`, loosening an assertion, disabling a gate. If the only way to make it faster is to check less, stop — wrong job.

For the CONDITIONAL bucket the proof obligation is on you (Step 3). When unsure whether a skip is safe, treat it as unsafe and find a SAFE lever.

## Step 1 — MINE: find the actual wall-clock long poles

Don't guess where CI is slow. Pull per-job and per-step durations, reconstruct the critical path, rank by wall-clock contribution, fix the long pole first. Set `REPO=<owner>/<repo>`.

**(a) Per-job durations on a recent successful run** (slow ≠ broken — time GREEN runs):

```bash
gh run list --repo $REPO --workflow <ci-workflow> --status success --limit 20 \
  --json databaseId,headSha,createdAt,updatedAt \
  -q '.[] | "\(.databaseId)\t\(.headSha[0:9])\t\(.createdAt)\t\(.updatedAt)"'
# per-job started/completed → duration (seconds), slowest first. (BSD/macOS date shown;
# on GNU/Linux use: date -d "<ts>" +%s)
gh api "repos/$REPO/actions/runs/<runId>/jobs" --paginate \
  -q '.jobs[] | "\(.name)\t\(.started_at)\t\(.completed_at)"' \
  | awk -F'\t' '{ "date -j -f %Y-%m-%dT%H:%M:%SZ "$2" +%s" | getline s; \
                  "date -j -f %Y-%m-%dT%H:%M:%SZ "$3" +%s" | getline e; \
                  printf "%5d  %s\n", e-s, $1 }' | sort -rn | head -25
```

**(b) Per-step durations inside one slow job** (where the time goes within the long pole):

```bash
gh api "repos/$REPO/actions/runs/<runId>/jobs" --paginate \
  -q '.jobs[] | select(.name|test("<job-name>")) | .steps[] | "\(.name)\t\(.started_at)\t\(.completed_at)"'
# eyeball: browser install? build? the test run itself? cache restore?
```

**(c) Critical path** — the long pole is the slowest *chain*, not the slowest *job*. If CI is tiered with serial gate barriers, a fast job stuck behind a slow gate still finishes late. Map the chain that ends latest:

```bash
gh api "repos/$REPO/actions/runs/<runId>/jobs" --paginate \
  -q '.jobs[] | select(.name|test("gate|<summary-check>|<e2e-suite>")) | "\(.completed_at)\t\(.name)"' | sort
```

**(d) Matrix shard balance** — a matrix finishes at its SLOWEST shard; an unbalanced matrix wastes the fast shards' idle time. List shard durations and look for one far slower than its siblings.

**(e) merge_group timing** — the queue runs the same gate on a synthetic branch; confirm the PR-level long pole is also the queue long pole (it usually is):

```bash
gh run list --repo $REPO --event merge_group --status success --limit 10 \
  --json databaseId,createdAt,updatedAt -q '.[] | "\(.databaseId)\t\(.createdAt)\t\(.updatedAt)"'
```

Build a ranked list: `{job-or-chain, wall-clock, % of critical path, bottleneck class}`, worst-first. **Don't trust `timeout-minutes`** — that's the ceiling, not the runtime. Always measure. Re-derive your baseline from live data each tick; the suite grows, so last week's long pole may not be this week's.

## Step 2 — DIAGNOSE the bottleneck class

Name the mechanism. The recurring classes:

- **Serial `needs:` that could overlap.** A job waits on a gate it doesn't actually consume (e.g. a build that needs only source + lockfile, sitting behind a unit-test barrier). If a heavy job's real inputs are ready before the barrier, the barrier is pure idle wait.
- **Under-balanced matrix.** One shard runs far longer than its siblings, so the whole matrix waits on it. Re-balance spec assignment, or split the heavy shard — total work unchanged.
- **Cold cache / redundant rebuild.** A cache that restores but was last saved on a stale key → the job rebuilds from scratch every run. Or two jobs each rebuild the same artifact instead of sharing one (the build-once anti-pattern). Watch for **save-on-default-branch-only** cache policies: a PR after a lockfile/config change hits a cold key and pays the full rebuild.
- **Missing or too-broad tier gate.** A heavy job runs on every PR even when the diff can't affect it (no path filter), OR a filter is so broad it never skips. A *correct* tighter filter skips provably-irrelevant runs.
- **Dep/browser reinstall in the hot path.** A browser install or full dependency install inside the timed job rather than from a warm cache.
- **Oversized timeout masking creep.** Not a direct win, but right-size with a safe margin so regressions surface.

Write the class + the expected saving in one sentence before touching YAML. If you can't estimate the saving from the timing data, you haven't diagnosed it — back to Step 1.

## Step 3 — PROVE the speed-fix keeps identical coverage

This is the step that separates a speed fix from a coverage regression. For the chosen lever, satisfy the matching proof:

- **Cache add/change** → the cache **key hashes every input** that changes the artifact. List the inputs; if any source/config that affects the output is absent, a stale hit serves wrong artifacts. Prefer adding inputs over loosening.
- **Re-shard / re-balance** → enumerate the specs before and after; the **set of specs run is identical**, only the shard assignment moved. No spec lands in zero shards.
- **Parallelize a `needs:`** → confirm the job **does not read** any output/file produced by the barrier you're removing it from (grep its steps for use of the upstream's artifacts).
- **Add/tighten a path filter** → the filter glob is a **superset of every file the job verifies**, including transitive inputs. When in doubt, widen the filter.
- **Right-size a timeout** → new value is above the job's observed p99 with margin.

If you cannot produce the proof, the change is unsafe — pick a different lever. "Every run was green in my test" is not proof; reason about the worst-case diff, not the happy path.

## Step 4 — FIX FORWARD (faster, never less)

- Land the smallest change that removes the bottleneck: add the cache, re-balance the matrix, drop the spurious `needs:` edge, add the correct path filter, share the build artifact.
- **Edit workflow YAML carefully** — a mis-indent or wrong key breaks every PR. Validate with `actionlint` if available; otherwise re-read the diff against the surrounding job. Delegate the mechanical edit to a workhorse sub-agent only after you've named the exact change — never the cheap tier for workflow YAML.
- NEVER buy time by checking less (Step 0 OUT OF BOUNDS).
- Keep the change reviewable and single-purpose — one bottleneck per PR.

## Step 5 — VERIFY (prove faster AND unchanged coverage)

A speed fix is two claims; verify both:

1. **Faster** — trigger a real run and pull the same Step-1 timing. The long-pole job/chain dropped by ~the predicted amount; cite before→after numbers. One run suffices for a deterministic structural change (sharding, a `needs:` edge); for a cache win, confirm a **warm** run (the first run still pays the miss).
2. **Coverage unchanged** — same jobs run, same shard count covers the same specs, same gates still in the summary check's `needs:`, the pass/fail and (for tests) spec/assertion count identical. If the test count dropped, you cut coverage — revert.

If either fails, you fixed the wrong thing — back to Step 2.

## Step 6 — SHIP + REPEAT

- One PR per coherent speed change. Conventional commit, e.g. `ci: re-shard e2e 4→8 — <saving>` or `perf(ci): cache the build on PR — <saving>`.
- Base `<integration-branch>`, hooks intact, auto-merge (`gh pr merge --auto <merge-strategy>`; omit the strategy flag under a merge queue). If the project runs an auto-rebase automation, apply `do-not-rebase` only after observing a rebase-cancelled run (see `driving-prs-to-merge` / the issue control-field skill). Never `--admin`/`--no-verify`/force past the queue; respond to any `<bot-reviewer>` comments.
- PR body: state the before→after wall-clock with measured numbers AND an explicit "coverage unchanged: same N specs / same gates" line so the reviewer can confirm the line wasn't crossed.
- Then back to Step 1 with refreshed timing. The bottleneck set is never "done" — this is a CONTINUOUS lane.

## Good vs bad speed fixes (concrete)

**BAD — buying time by checking less (never):**

```yaml
# ❌ narrow the E2E grep so fewer specs run — coverage silently dropped
env: { E2E_GREP: "@smoke" }            # was the full suite → now skips most specs
# ❌ drop a shard's specs to "balance" — those specs now run nowhere
matrix: { shard: [1, 2] }              # was 1..6; shards 3..6 specs no longer execute
# ❌ remove a slow gate from the summary needs so it resolves sooner
needs: [changes, typecheck, unit]      # e2e dropped → end-to-end no longer gates merge
```

**GOOD — same coverage, faster:**

```yaml
# ✅ build once, fan the bundle to all shards — every shard runs the same specs, stops rebuilding N times
- uses: actions/download-artifact@<pinned>
  with: { name: prod-bundle-${{ github.run_id }} }
# ✅ cache key hashes EVERY input that changes the bundle, so a hit is always valid
key: build-${{ runner.os }}-${{ hashFiles('src/**', 'package.json', '<lockfile>') }}
# ✅ re-balance: spread the long-pole area across more shards — same total specs, lower max-shard time
# ✅ drop a needs edge the job never consumes — the build reads source+lockfile only, not unit results
needs: [tier-1-gate]                   # was tier-2-gate; build now overlaps the unit-test tier
```

A **correct path-filter tier** skips only provably-irrelevant runs: a docs-only PR doesn't need the web E2E shards because no web spec's inputs changed — but the filter glob is a *superset* of the E2E inputs, so any web-source, shared-package, or test-setup change still fires the shards. A filter gated too tightly (on one feature dir) would skip them on a shared-component change those specs exercise → silent coverage hole. When unsure, widen.

## Token discipline (caveman)

You run inside the caveman-mode `ci-speed-hunter` agent. CI timing logs are huge — the main context risk. Load the `caveman` skill and conserve aggressively:

- **Never** dump a full `gh run view --log` into context. Pull only the structured `jobs` timing JSON and reduce it to the ranked duration list. Quote only the long-pole numbers.
- Delegate timing dumps + step-duration parsing to a read-only cheap-tier sub-agent (`caveman:cavecrew-investigator`) and keep only its ranked conclusion.
- Status lines: terse fragments — `mined 12 runs; crit-path 50m; long-pole=build→shards 40m → drop tier-2 needs + re-shard 6→8 → speed PR #x (50m→38m, specs unchanged)`.

Caveman compresses *prose only* — `gh`/`gh api` commands, YAML keys, cache-key expressions, job names, before/after numbers stay byte-exact. Commit messages + PR bodies: normal prose with the numbers, through the `humanizer` skill.

## The bar — a real speed win vs noise

Before claiming a saving, satisfy ALL three:

1. **Measured, not assumed** — before/after durations from `gh api .../jobs`, not the `timeout-minutes` value and not a hunch. Account for runner variance (compare medians over a few runs for cache/timing-sensitive wins).
2. **On the critical path** — speeding a job that isn't the long pole of its tier moves the wall clock by zero. Confirm the job/chain you sped actually gates the summary check's completion.
3. **Coverage provably unchanged** — Step 3 proof done and stated in the PR.

If any fails, it's not shippable. A re-shard that doesn't reduce max-shard time, a cache that never warms, a filter that never skips — all noise.

## Lane boundary — never touch a red job

You and the `ci-flake-hunter` lane share the CI surface. The line is absolute: **the flake hunter owns whether a job passes; you own how fast a passing job runs.** If a job is failing or flaky, it is theirs — log it and move on; never "speed-fix" a red job, and never edit a workflow in a way that changes a job's pass/fail (a too-tight timeout that kills slow runs, a cancel-concurrency that drops a required check, a filter that skips a job the diff breaks). If your speed change turns a job red, you caused a regression — revert immediately. The two lanes run in parallel safely only because neither crosses into the other's territory.

## Singleton lane

There is **exactly one** `ci-speed-hunter` active at a time. Two collide on the CI workflow files, race on edits, and double-spend CI minutes re-timing the same jobs. If you are this lane and find another already running, defer to it. You routinely run *alongside* the flake hunter and the PR watcher lanes (`pr-checks`, `pr-comments`, `pr-cleanup`) — that is expected; just `git fetch origin <integration-branch> && git merge` before every push and keep your diff strictly the speed change.
