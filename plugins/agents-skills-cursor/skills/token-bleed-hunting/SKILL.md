---
name: token-bleed-hunting
description: The authoritative method for hunting TOKEN BLEED — tokens an AI coding agent spends that buy no work — from OpenTelemetry metrics and events (Claude Code first-class) and local session transcripts, then fixing it forward in the repo's harness config so every future session is cheaper at the same capability. Encodes the loop — MINE telemetry for one repo against a rolling baseline, normalized per session and per unit of work → DIAGNOSE the bleed class (cache-busting / low cache-hit ratio, bloated always-loaded context, unbounded tool output, model-tier mismatch, retry and permission churn, compaction thrash, subagent overspawn, redundant re-reads, verbose output) → CONFIRM the cause in transcripts and tie it to a file → PROVE the fix keeps capability → FIX FORWARD via a PR that records the baseline and projected saving → VERIFY after merge that the saving landed → REPEAT. And the hard lines — cut waste, never work; harness config only, never application code; aggregate numbers only, never prompt or transcript content. Use whenever chasing agent token spend or cost, "where are our tokens going", "why did the Claude bill jump", a low cache-hit ratio, a high session start floor, CLAUDE.md or MCP bloat, huge tool results, querying claude_code.token.usage / cost.usage / api_request in any backend, checking whether a token-saving change worked, or running the token-bleed-hunter lane. Distinct from ci-speed-hunting (CI wall-clock time) and caveman (this session's output style).
---

# Token Bleed Hunting

Every agent session in a repo pays for the same always-loaded context, the same tool definitions, the same instructions, before it does anything. Bleed in that shared layer is a tax on every session, every subagent and every loop tick, forever. A fix there pays back on every session after it merges. That is the leverage this lane exists for.

**Token bleed** is spend that buys no work: a cache prefix rewritten when it could have been read, a 200 KB test log the agent skims for one line, a top-tier model listing files, a permission prompt re-asked forty times, a session that compacts and then re-reads everything it just forgot. It is not "a lot of tokens". A hard task that spends a lot of tokens well is not bleed.

This skill builds on `MODEL-DEFAULTS.md` (the tier policy a model-mismatch fix applies), `driving-prs-to-merge` (PR mechanics) and `caveman` (its own token discipline). Where a "just make it cheaper" instinct conflicts with the capability rule below, this skill wins.

## Project bindings

Project-agnostic; the adopting project defines these in its own `CLAUDE.md`.

| Placeholder | Meaning |
|---|---|
| `<owner>/<repo>` | GitHub repository slug |
| `<integration-branch>` | Branch fix PRs target |
| `<telemetry-backend>` | Where OTel lands: `prometheus`, `otlp-file` (a collector's file exporter), or `sql` (ClickHouse or another SQL store behind a collector). Recipes for each in [`references/queries.md`](references/queries.md) |
| `<telemetry-access>` | How the hunter queries it: an HTTP endpoint, a CLI, or a file path. Credentials come from the environment, never a file in the repo |
| `<repo-filter>` | The attribute that tags this repo's sessions. Preferred: `vcs.repository.name=<repo>` (needs `OTEL_METRICS_INCLUDE_REPOSITORY=1`). Fallback: a custom `OTEL_RESOURCE_ATTRIBUTES` key such as `repo=<repo>` |
| `<transcript-root>` | Where this repo's session transcripts live on the machine running the lane. Absent → metrics-only, and findings carry lower confidence |
| `<window>` | The analysis window. Default `7d` |
| `<baseline-window>` | The comparison window before it. Default the prior `28d` |
| `<min-sessions>` | Minimum sessions in a window before any number is trusted. Default `20` |

If `<repo-filter>` is not set, the lane's first job is a PR that sets it in the repo's `.claude/settings.json` `env` block (see [`references/claude-code-telemetry.md`](references/claude-code-telemetry.md) § Setup). Without it, nothing measured can be attributed to this repo.

## The one rule

**Cut waste, never work.** A cheaper session that ships a bug, misses a constraint or asks the user three extra questions costs more than it saved. You make sessions cheaper by sending the same information in fewer tokens, sending it once instead of many times, keeping the cache warm, or giving mechanical work to a cheaper model. You never do it by making the agent know less or check less.

Out of bounds, always:

- Deleting an instruction that encodes a real constraint (security, testing, a gotcha someone hit) because it is long. Move it to an on-demand location with a pointer, or tighten its wording. Don't drop it.
- Removing a skill, agent, command or MCP server that sessions in the window still use.
- Downgrading the model on work that needs reasoning: design, review, debugging, anything `MODEL-DEFAULTS.md` puts on workhorse or premium.
- Capping or filtering tool output so tightly that the agent loses the signal it needs, such as the failing test's name and assertion.
- Widening a permission allowlist to a destructive or outward-facing command to stop a prompt from repeating. Read-only commands only.
- Turning prompt caching off, or turning on prompt, tool-detail or raw-body logging.

## Step 0: classify the bleed

Name the class before you open a file. Each class has a metric signal, a transcript confirmation and a harness-config lever.

| Class | Metric signal | Confirm in transcripts | Lever (harness config) |
|---|---|---|---|
| **Cache-busting** | Low cache-hit ratio; `cacheCreation` large relative to `cacheRead`; repeated near-full-prefix writes within a session | What changed in the prefix between turns: a model or effort switch mid-session, an MCP server connecting late, a tool denied mid-session, a hook or instruction injecting volatile text (timestamps, live status dumps) | Stop the churn: pin the model per agent, load MCP servers up front, keep volatile text out of always-loaded files and hook output |
| **Idle-gap re-writes** | Cache writes cluster after idle gaps longer than the cache TTL | Turn timestamps show long pauses before full re-writes | `promptCacheTtl` / `subagentPromptCacheTtl` `1h` in project settings, but only where the gap pattern repeats (a 1h write costs more than a 5m one) |
| **Always-loaded bloat** | High **session floor**: input + cache tokens on each session's first request | Size of the `CLAUDE.md`/`AGENTS.md` chain, tool count, skill and agent description lengths, MCP servers loaded | Move rarely-needed sections to a skill or referenced doc; trim descriptions; disable MCP servers with zero calls in the window |
| **Unbounded tool output** | High `tool_result_size_bytes` by `tool_name`; input tokens jump after specific tools | Which commands or reads return the bulk: full test logs, lockfiles, generated or vendored files, minified bundles | An instruction or agent prompt to use quiet flags, tail or grep logs; `permissions.deny` on reads of generated paths; ignore files; a hook that truncates output |
| **Model-tier mismatch** | `cost.usage` by `model` × `query_source` / `agent.name`: premium spend on subagents or agents whose tool mix is mostly read, grep, glob and list | The work really is mechanical (lookups, listing, fixed-command-and-parse) | `model:` in that agent's frontmatter, or the dispatch instruction, set per `MODEL-DEFAULTS.md` |
| **Retry and permission churn** | `api_error` rate and `attempt` > 1; `tool_result` with `success=false` repeating; the same `tool_decision` reject recurring | A hook failing on every call, an instruction naming a path or command that no longer exists, a read-only command re-prompted every session | Fix the hook or the stale instruction; allowlist the read-only command |
| **Compaction thrash** | Many `compaction` events per session; tokens re-climb after each | Long-running loops that keep raw logs in the main thread, then re-read after compacting | Delegate the bulky reads to subagents that return conclusions; split the agent; shrink the floor |
| **Subagent overspawn** | `query_source=subagent` share high; `subagent_completed` `total_tokens` large and repeated for the same `agent_type` | Several subagents each loading the same files to answer overlapping questions | Tighter dispatch instructions: one investigator, a narrower brief, cheap tier for lookups |
| **Redundant re-reads** | High `Read` count per session relative to distinct files | The same large file read many times in one session | A map or summary the agent can read once; instructions that point at the right section |
| **Verbose output** | High `output` tokens per request (output is the most expensive token type) | Whole files echoed back, long recaps, repeated plans | Output-style or terse-mode instructions in always-loaded config |

Several classes usually overlap. Rank by tokens and cost, not by how interesting the class is.

## Step 1: MINE

Pull aggregates, never raw event streams. Every query in [`references/queries.md`](references/queries.md) returns numbers grouped by a few attributes. Run them through a cheap-tier read-only subagent and keep only the table it returns.

For `<window>` and `<baseline-window>`, filtered by `<repo-filter>`:

1. **Volume.** Sessions, requests, tokens by `type` (`input`, `output`, `cacheRead`, `cacheCreation`), cost by `model`.
2. **Normalize.** Raw totals rise with usage, so compare rates: tokens and cost per session, per active hour (`active_time.total`), and per unit of output (`commit.count`, `pull_request.count`, `lines_of_code.count`). A spend increase with flat output is a lead. A spend increase that tracks output usually isn't.
3. **Derived metrics** (formulas in the telemetry reference): cache-hit ratio, session floor, output share, subagent share, per-tool result bytes, error and retry rate, compactions per session.
4. **Attribution.** Group the token and cost metrics by `agent.name`, `skill.name`, `mcp_server.name` and `query_source`. A bleed that lives in one agent or one skill is a fix with a clear file to edit.

Build a ranked list: `{class, signal, window value, baseline value, tokens/window, cost/window, share of window spend}`, worst first. Re-derive the baseline from live data each tick. Usage changes, models change, the floor drifts.

Fewer than `<min-sessions>` in either window → report "insufficient sample" and stop the tick. Small samples produce confident nonsense.

## Step 2: DIAGNOSE and CONFIRM

Metrics say how much. Transcripts say why. For the top-ranked class, pick three to five sessions where the signal is worst and have a cheap-tier subagent parse them per [`references/transcripts.md`](references/transcripts.md), returning counts and sizes only, never content.

Write one sentence before touching any file: the mechanism, the file that causes it, and the expected saving. For example: *"Cache-hit ratio 38% vs 71% baseline: a hook in `.claude/settings.json:14` prints a fresh timestamp into context each turn, which rewrites the prefix. Expected: ratio back above 65%, about 1.2M cache-write tokens/week saved."*

If you can't name a file in this repo's harness config, it is not yours to fix. Report it and move on:

- **User-level or global config** (the user's home settings, their personal memory, their own MCP servers) → report.
- **Application code, scripts, test runners, CI** → report. The output may be noisy, but the fix belongs to that code's owner.
- **Harness behavior** (a version that changed its system prompt, a bug) → report, with the version observed.

## Step 3: PROVE capability is unchanged

Each lever has a proof obligation. If you can't produce the proof, pick another lever.

- **Trimming always-loaded context** → list every removed or moved block. Each one is either a duplicate (cite the other copy), stale (cite the missing path or command), or moved to an on-demand location that a pointer still reaches (cite the pointer). Nothing silently disappears.
- **Disabling an MCP server, skill or agent** → zero uses in the window: no `tool_result` with that server's tools, no `skill_activated`, no matching `agent.name`. Cite the query.
- **Model downgrade** → the agent's tool mix and task are mechanical per `MODEL-DEFAULTS.md`. State the rollback criterion in the PR: an increased `success=false` rate or retry rate on that agent after merge.
- **Output caps and quiet flags** → the agent still sees what it needs to decide: the failing test's name and assertion, the error line, the summary count. Show the before and after on one real command.
- **Permission allowlist** → every added pattern is read-only. No write, delete, network-publish or credential command.
- **Cache TTL change** → the idle-gap pattern repeats across sessions, and the projected re-write saving exceeds the higher write price (arithmetic in the PR).

Then project the saving: affected tokens per window × the fraction removed × the price for that token type. Show the arithmetic. A projection without arithmetic is a guess.

## Step 4: FIX FORWARD

- **One bleed per PR.** Smallest change that removes it. Fresh branch off `origin/<integration-branch>`, conventional commit such as `perf(agents): move release runbook out of CLAUDE.md`.
- **Edit harness config only.** Validate what you touch: JSON parses, YAML frontmatter is valid, every pointer you added resolves, and any generated mirrors the repo keeps are regenerated by its own sync command.
- **Label `token-bleed`**, hooks intact, **no auto-merge**: the PR watcher lanes drive CI and review.
- **PR body** in normal prose through `humanizer`: the mechanism, the evidence as aggregate numbers, the capability proof, the projection arithmetic. End it with this machine-readable block, which the VERIFY step reads back:

```text
<!-- token-bleed
class: always-loaded-bloat
metric: session_floor_tokens
baseline: 41200 (p50, 28d, 312 sessions)
target: 29000
projected_saving: 3.8M tokens/7d
verify_after: 7d
rollback_if: tool_result failure rate on main up >2pts
-->
```

## Step 5: VERIFY after merge

Every tick, before mining, list merged PRs labeled `token-bleed` with no verdict yet. For each one whose `verify_after` has elapsed with at least `<min-sessions>` sessions since merge, re-run the block's `metric` over the post-merge window and comment one verdict:

- **landed**: the metric reached the target, or got within 20% of the projected saving. Add label `token-bleed-verified`.
- **partial**: some real movement, short of that. Record it, then re-rank. The remainder may be a different class.
- **no effect**: within noise. Re-diagnose. The mechanism named in Step 2 was wrong.
- **regressed**: tokens went up, or the `rollback_if` condition fired. This is your regression. Open the follow-up PR that undoes or corrects your change yourself. Don't hand it to another lane.

Late-arriving changes muddy the comparison. Note any other merged harness-config change in the same window in the verdict comment.

## Step 6: REPEAT

Back to Step 1 with fresh numbers. Bleed is never "done". New instructions, new MCP servers, new agents and new model versions keep moving the floor, so this is a continuous lane, not a one-off sweep.

## Privacy: aggregates only

The repos this lane works in may be public, and transcripts contain everything a user typed, every file an agent read, and often secrets.

- PRs, comments, reports and commit messages carry **aggregate numbers, metric and attribute names, model names, tool names, and paths of files inside this repo** (the fix's harness-config `file:line`, and a repo file that sessions re-read or that floods tool output). The PR lands in this same repo, so its readers can already see those paths. Nothing else from telemetry or transcripts.
- Name an MCP server or tool only if this repo's own config defines it. Describe one the user configured themselves as "a user-level MCP server", without naming it.
- Never quote prompt text, assistant text, tool input or output, file contents seen in a session, or error message bodies. Name the error type, not its message.
- Never include identifiers: emails, account, user, organization or session ids, request ids, host paths.
- Transcript parsing happens locally in a subagent whose return contract is numbers and tool or file names only. Its raw output never goes into a PR.
- Never enable `OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_TOOL_DETAILS`, `OTEL_LOG_TOOL_CONTENT`, `OTEL_LOG_ASSISTANT_RESPONSES` or `OTEL_LOG_RAW_API_BODIES`. The lane is designed to work without them.

## Lane boundary

Your lane is exactly one thing: **the tokens this repo's agent sessions spend, and the harness config that decides them.**

| Not yours | Route to |
|---|---|
| CI wall-clock time | `ci-speed-hunting` |
| A PR's red checks, conflicts, queue health | `pr-checks` |
| Flakes, post-merge reds, transient infra | `ci-flake-hunting` |
| Deploy health | `deploy-watching` |
| Review threads on any PR, including yours | `pr-comments` |
| Application code, scripts, user-level or global config, harness bugs | report only |

The agents and skills in a repo are harness config, so when another lane's agent definition is the bleed (it reads logs into the main thread, or runs on a premium model for mechanical work), the fix is yours. Make the smallest change that keeps that lane's rules intact, and say in the PR which lane it touches.

## Singleton per repo

Exactly one `token-bleed-hunter` per repo. Two collide on the same config files, open duplicate PRs for the same bleed, and double the telemetry queries. If another is running on this repo, defer. Hunters on different repos are fine. They filter to different `<repo-filter>` values.

## Other harnesses

Claude Code is the first-class target. For another harness, map its counters onto the same four buckets (fresh input, cache read, cache write, output) and the same derived metrics. Harnesses that emit the OpenTelemetry GenAI semantic conventions report `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens` on their spans. Where a harness reports no cache split, the cache classes can't be measured: say so instead of guessing. The bleed classes, the capability rule and the privacy rule don't change.

## Token discipline (caveman)

A token hunter that bleeds tokens is a joke nobody wants to pay for. Load the `caveman` skill.

- Never pull raw metric series, event streams or transcripts into your context. Subagents run the queries and parsers and return the ranked table.
- Cheap tier for every query and parse (`caveman:cavecrew-investigator` or a cheap-tier subagent per `MODEL-DEFAULTS.md`). Workhorse for the config edit, once you have named the exact change. Never the cheap tier for edits.
- The tick should cost a small fraction of the bleed it finds. If telemetry reports your own lane's spend (`agent.name=token-bleed-hunter`), include it in the tick report.
- Status line: `window 7d; 214 sessions; cache-hit 38% (base 71%); floor 41k; top=cache-busting ~1.2M tok/wk → hook timestamp → PR #x; verified #y landed`.

Caveman compresses prose only. Queries, metric and attribute names, file paths and numbers stay byte-exact. Commit messages and PR bodies are normal prose through `humanizer`.

## The bar: a real saving vs noise

Before opening a PR, all four must hold:

1. **Measured.** Window vs baseline from telemetry, normalized per session or per unit of work, over at least `<min-sessions>`.
2. **Attributable.** Tied to a `file:line` in this repo's harness config and confirmed in transcripts.
3. **Capability-safe.** The Step 3 proof is done and stated in the PR.
4. **Material.** The PR states the saving as tokens, cost and share of window spend, so a reviewer can tell a 0.3% polish from a 30% leak.
