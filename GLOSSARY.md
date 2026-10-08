# Glossary

The words this repo uses in a specific way. Most of them look like ordinary English, which is exactly the problem: "watcher" and "hunter" sound interchangeable, and they are not. The distinctions below are load-bearing. Several skills refuse work on the strength of them.

## slot

An arbitrary allocation of one project's compute on one machine. A laptop, a desktop, a server.

A slot is not a CPU core and not a container. It is a number you pick, based on what the machine can actually stand: memory, disk, how many test suites can run at once before everything starts thrashing. One slot holds one concurrent unit of agent work. `/dispatch 8` means eight agents at once, because you decided this box can carry eight.

Slots have kinds, and the split matters:

- **dev** slots pick up new issues.
- **rescue** slots take incidents: red CI, a stuck PR, a broken gate.
- **flex** slots do dev work but yield to an incident when one appears.

When the queue jams, you stop filling slots instead of piling on more. That is backpressure. Adding agents to a jammed queue produces rebase thrash, not throughput.

See `orchestrating-slots` and the `/dispatch` command.

## dispatcher

The thing that turns a groomed ticket into a running implementation agent and, eventually, a merged PR.

It picks the issue (priority first, and file-disjoint from whatever else is in flight), locks it so no one else claims it, resolves which model and effort tier the work deserves, writes the brief, spawns the sub-agent into a slot, and then verifies what comes back rather than believing the report. An agent can say "done" without having done it.

A dispatcher creates work. A watcher tends work that already exists. That is the cleanest way to keep the two apart.

See `dispatching-subagents`, the `/dispatch` command, and the `implementer` agent.

## watcher

A single-lane interval loop over a surface that already exists.

It wakes on a schedule (`/loop <interval> start`), scans everything in its lane, does the one thing it owns, reports a single line, and goes back to sleep. Watchers are reactive. They respond to state sitting on PRs right now, and they do not go looking for trouble elsewhere.

The watchers in this repo:

- `pr-comments` drives review threads to resolved, then arms auto-merge.
- `pr-checks` keeps checks green and the merge queue healthy.
- `pr-cleanup` acts only on closed PRs: close the issue, release the lock, reclaim the disk.
- `deploy-watcher` keeps the integration environment's deploy green: re-runs a transient red, fixes a real one forward, never reverts.
- `branch-ff` keeps the primary checkout fast-forwarded so fresh worktrees start from a current base.

Lanes never cross, and that restraint is the whole design. A watcher that notices something outside its lane logs it and moves on. Two watchers reaching for the same PR is how you get a race and a force-push.

## hunting

A hunter loops like a watcher, but it goes looking for problems nobody reported.

That is the entire difference. A watcher reacts to a queue. A hunter mines history for a pattern, roots it out, and proves it is dead. The loop is always the same shape: mine the data, diagnose the mechanism, prove the fix is safe, fix forward, verify, repeat.

A hunt never finishes. New slowness and new flakes keep appearing as the test suite grows, so the lane is permanent rather than a one-time sweep. Both hunters are singletons: run two and they collide on the same files and double-spend CI minutes re-measuring the same jobs.

**Fix forward** is the rule underneath both hunters. You fix the cause. You do not mask it. No skipped test, no bumped retry count, no gate quietly dropped from the required list.

The two hunters are `ci-speed-hunter` and `ci-flake-hunter`, and they are strictly disjoint. See below.

## ci-speed

Wall-clock time. Specifically **time to merge**: how long the critical path takes to go green, and therefore how fast the merge queue drains.

It has nothing to do with correctness. A ci-speed problem is a job that is **green but slow**. Because a serial queue can only drain as fast as its long pole completes, a minute shaved off the critical path is a minute off every PR queued behind it. That is why it is worth chasing at all.

The levers are caching, matrix balance, building an artifact once and fanning it out, correct changed-paths tiering, and pruning a `needs:` edge nobody actually consumes.

The hard rule: **speed never costs coverage.** If CI got faster because it checked less (a narrowed grep, a dropped shard, a gate pulled from the summary), that is not a speed fix. That is a coverage cut wearing a speed costume.

A ci-speed hunter never touches a red job, and never accepts one. Red is somebody else's lane, always.

See `ci-speed-hunting`.

## flake

A test that fails, then passes on retry, with no code change that explains why.

Three things a flake is not, and confusing them wastes hours:

- **A real regression.** It fails every single time, on that branch, because the diff broke it. That belongs to the PR's author, shepherded by the `pr-checks` watcher.
- **Transient infrastructure.** A package mirror blipped, a shared token expired mid-suite, a host started returning 429. Re-run it. Never open a code PR to "fix" it.
- **A slow job.** That is ci-speed, and it is a different lane entirely.

Flakes are worth hunting because of the merge queue. When a flaky speculative build reds, the correct PR at the front gets ejected and its auto-merge is silently disarmed. It then sits there looking clean and going nowhere. One live flake is a tax on every PR behind it, which is why killing a single high-frequency flake measurably raises throughput.

The fix is always forward: reproduce it harsher than CI until it fails on demand, name the actual race, repair the test or the component, then prove it dead by running it many times over. Masking it (a skip, a bare sleep, a retry bump, a widened assertion) leaves the bug alive and hides the evidence.

See `ci-flake-hunting`.

## The three CI lanes, side by side

The single most common mistake is routing a red job to the speed lane. It never belongs there.

| Lane | Owns | Never touches |
|---|---|---|
| `ci-speed-hunting` | Wall-clock time of jobs that are already **green** | Any red job, of any kind |
| `pr-checks` (watcher) | A given open **PR's** failing checks, conflicts, queue health | The systemic hunt |
| `ci-flake-hunting` | The **instability itself**: queue failures and the ejections they cause, post-merge reds, the recurring flake, transient infra | Timing, sharding, caching |

## Supporting terms

**Lane.** The bounded set of work one agent owns. Everything outside it gets logged and left alone, even when it is obviously broken. Lanes are what let several agents run at once without racing.

**Tick.** One firing of a loop. Ticks are idempotent by design, so a tick that finds nothing to do costs a second and is still worth running. Never skip one because it "probably already ran".

**Primary checkout.** The original clone. Agents work in **worktrees** cut from it, which is why the primary should normally be clean, and why a blocked fast-forward there is treated as an anomaly worth alerting on rather than something to stash away.

**Singleton.** A lane with exactly one agent in it. Two of the same hunter collide on the same files and duplicate the same expensive work.
