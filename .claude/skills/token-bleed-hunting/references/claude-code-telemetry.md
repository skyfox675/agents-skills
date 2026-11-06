# Claude Code telemetry reference

What Claude Code emits over OpenTelemetry, which parts the hunt uses, and the derived metrics built from them. Source of truth is the official monitoring docs (`code.claude.com/docs/en/monitoring-usage`). Attribute sets grow between versions, so when a query comes back empty, check the docs and your version before assuming the data isn't there.

## Setup

Telemetry is off until `CLAUDE_CODE_ENABLE_TELEMETRY=1`. The exporter, endpoint and credentials are per-user or per-org infrastructure. They belong in the user's environment, user settings or managed settings, **never in a committed repo file**.

Repo tagging works best user-side too: `OTEL_METRICS_INCLUDE_REPOSITORY=1` in user or managed settings derives the repo from git and tags every repo at once. If the operator wants it per repo, a repo may commit the tag in `.claude/settings.json`:

```json
{
  "env": {
    "OTEL_METRICS_INCLUDE_REPOSITORY": "1"
  }
}
```

That adds `vcs.repository.name`, `vcs.owner.name`, `vcs.repository.url.full` and `vcs.provider.name` to metrics. Recent versions only, and it's off by default. Current versions put the same attributes on events too. Confirm yours does with `sum by (vcs_repository_name) (count_over_time({service_name="claude-code"} | event_name="api_request" [1h]))` in Loki, or the equivalent in your store. Sessions that started before the flag was set stay untagged. If metrics carry them but events don't, attribute from metrics and treat event-only numbers (floor, tool bytes, compactions) as user-wide until a tag reaches events. For a tag that does reach events, or one the harness doesn't derive, use `OTEL_RESOURCE_ATTRIBUTES` (`key=value,key=value`, no spaces, percent-encode special characters). A project-level `OTEL_RESOURCE_ATTRIBUTES` replaces a user-level one rather than merging with it, so check with the user before committing it.

User-side settings the lane assumes:

| Variable | Notes |
|---|---|
| `OTEL_METRICS_EXPORTER`, `OTEL_LOGS_EXPORTER` | `otlp`, `prometheus`, `console`, comma-separated, or `none`. **Events travel on the logs exporter.** Metrics alone can't measure the session floor, tool result sizes or compactions |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `grpc`, `http/json` or `http/protobuf`. Set it explicitly |
| `OTEL_EXPORTER_OTLP_ENDPOINT` (+ per-signal `_METRICS_` / `_LOGS_` variants), `OTEL_EXPORTER_OTLP_HEADERS` | Collector address and auth. User-side only |
| `OTEL_METRIC_EXPORT_INTERVAL` | Default `60000` ms |
| `OTEL_LOGS_EXPORT_INTERVAL` | Default `5000` ms |
| `OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE` | Default `delta`. Prometheus needs cumulative: set `cumulative`, or convert in the collector |
| `OTEL_METRICS_INCLUDE_SESSION_ID` | Default on. Needed for per-session metrics |
| `OTEL_METRICS_INCLUDE_ACCOUNT_UUID` | Default on |
| `OTEL_METRICS_INCLUDE_VERSION` | Default off. Turn on to correlate a floor change with a harness upgrade |

Content logging (`OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_TOOL_DETAILS`, `OTEL_LOG_TOOL_CONTENT`, `OTEL_LOG_ASSISTANT_RESPONSES`, `OTEL_LOG_RAW_API_BODIES`) is off by default. The lane never needs it and never turns it on.

## Metrics the hunt uses

| Metric | Unit | Key attributes |
|---|---|---|
| `claude_code.token.usage` | tokens | `type` = `input` \| `output` \| `cacheRead` \| `cacheCreation`; `model`; `query_source` = `main` \| `subagent` \| `auxiliary`; `agent.name`, `skill.name`, `plugin.name`, `mcp_server.name`, `mcp_tool.name`; `effort`, `speed` |
| `claude_code.cost.usage` | USD | same as `token.usage` minus `type` |
| `claude_code.session.count` | count | `start_type` = `fresh` \| `resume` \| `continue` |
| `claude_code.active_time.total` | s | `type` = `user` \| `cli` |
| `claude_code.commit.count`, `claude_code.pull_request.count` | count | (none) |
| `claude_code.lines_of_code.count` | count | `type` = `added` \| `removed` |

`input` excludes cache tokens. The four `type` buckets are disjoint, and their sum is the full prompt plus output.

The attribution attributes (`agent.name`, `skill.name`, `plugin.name`, `mcp_server.name`, `mcp_tool.name`) depend on the harness version and may be missing entirely. Check before you build a query on them.

Most backends turn dots into underscores, so a collector's Prometheus exporter typically exposes `claude_code_token_usage_tokens_total`, `claude_code_cost_usage_USD_total` (the unit suffix keeps its case), `claude_code_session_count_total` and `claude_code_active_time_seconds_total`, with labels such as `session_id`, `query_source` and `user_name`. Discover the names rather than assuming them (recipe in [`queries.md`](queries.md)).

### `query_source` values

The docs list `main`, `subagent` and `auxiliary`, but events carry finer values, and metrics and events can disagree in the same deployment:

| Value seen | Meaning | Counts as "main" for the floor? |
|---|---|---|
| `main` (metrics), `repl_main_thread` (events) | The interactive main conversation | yes |
| `sdk` | A headless or SDK-driven run (`claude -p`, Agent SDK) | separately: it has its own floor |
| `subagent` | A subagent's requests | no |
| `auxiliary`, `generate_session_title` and similar | Harness helper calls | no |

Group by `query_source` once, see which values your version emits, and set the floor's "main" match from that (for example `main|repl_main_thread`).

## Events the hunt uses

Every event carries `event.name`, `event.timestamp`, `event.sequence` and the standard attributes. In Loki and most SQL stores fed by a collector they arrive as `event_name`, `session_id` and so on. `prompt.id` ties every event from one user prompt together. `agent_id` and `parent_agent_id` tie subagent events to their parent.

| Event | Attributes used |
|---|---|
| `api_request` | `model`, `query_source`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens` (split into `cache_creation_5m_tokens` / `cache_creation_1h_tokens`), `cost_usd`, `duration_ms`, `effort`, `speed` |
| `api_error` | `model`, `status_code`, `attempt`, `error` (type only, never quote the message) |
| `api_retries_exhausted` | `model` |
| `tool_result` | `tool_name`, `success`, `duration_ms`, `error_type`, `tool_input_size_bytes`, `tool_result_size_bytes`, `mcp_server_scope` |
| `tool_decision` | `tool_name`, `decision`, `source`, `permission_mode` |
| `compaction` | (presence and count per session) |
| `subagent_completed` | `agent_type`, `total_tokens`, `total_tool_uses`, `model` |
| `skill_activated` | skill name, for proving a skill is unused before removing it |
| `mcp_server_connection` | server name and timing, for late connects that bust the cache |
| `user_prompt` | `prompt_length` only. Prompt text is redacted by default, and stays that way |

Standard attributes include `session.id`, `organization.id`, `user.account_uuid`, `user.id`, `user.email`, `terminal.type`, and optionally `app.version`. **Filter and group by them. Never print them in a report.**

## Derived metrics

Compute these for both `<window>` and `<baseline-window>`. Per-day or per-session rates make windows of different lengths comparable.

| Metric | Formula | Bleed it exposes |
|---|---|---|
| Cache-hit ratio | `cacheRead / (input + cacheRead + cacheCreation)` | cache-busting, idle-gap rewrites |
| Write-to-read ratio | `cacheCreation / cacheRead` | same; more sensitive at high hit ratios |
| Session floor | p50 and p90 over sessions of `input + cache_read + cache_creation` on the **first** `api_request` from the main thread (see `query_source` values above), counting only sessions that started inside the window. Report interactive and `sdk` floors separately | always-loaded bloat |
| Tokens per session | all four buckets ÷ `session.count` | overall trend |
| Tokens per PR / commit | all four buckets ÷ `pull_request.count` (or `commit.count`) | spend not buying output |
| Output share | `output / all four buckets`, and output tokens per request | verbose output |
| Subagent share | tokens with `query_source=subagent` ÷ all | subagent overspawn |
| Premium share on mechanical work | cost by `model` × `agent.name` / `query_source` | model-tier mismatch |
| Result bytes by tool | sum and p90 of `tool_result_size_bytes` by `tool_name` | unbounded tool output |
| Failure and retry rate | `tool_result success=false` ÷ all; `api_error` ÷ `api_request`; share with `attempt > 1` | churn |
| Compactions per session | `compaction` count ÷ sessions | compaction thrash |
| Idle-gap rewrites | per session, main-thread `api_request`s preceded by a gap longer than the cache TTL whose `cache_creation_tokens` is at least half of that request's prompt-side tokens (a rewrite of the prefix, not just the new turn) | idle-gap rewrites |

## Prompt caching facts that drive the levers

- The cache matches an **exact prefix**, ordered: system prompt and tool definitions, then `CLAUDE.md` and memory, then the conversation. A change anywhere invalidates everything after it.
- **Busts the cache:** switching model; changing effort on some older models; toggling fast mode; an MCP server connecting or disconnecting mid-session when tools load up front; removing a tool with a deny rule mid-session; a system prompt change (harness upgrade, a different appended system prompt on resume); compaction.
- **Keeps the cache:** editing files, invoking skills and commands, plan mode, permission-mode changes, spawning a subagent (it gets its own prefix). Edits to `CLAUDE.md` don't apply until the next `/clear`, `/compact` or restart, so they don't bust mid-session.
- **TTL:** 5 minutes by default for API-key and cloud-provider usage. Some subscription plans default the main conversation to 1 hour. `promptCacheTtl` and `subagentPromptCacheTtl` (or `CLAUDE_CODE_PROMPT_CACHE_TTL` / `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL`) set `5m` or `1h`.
- **Pricing shape** (check the current pricing page; multipliers can change): a cache read costs about 0.1× the base input price, a 5-minute write about 1.25×, a 1-hour write about 2×, and output is several times input. So a 1-hour TTL pays off only when idle-gap rewrites recur often enough to beat the higher write price, and output tokens are the most expensive tokens a session spends.
