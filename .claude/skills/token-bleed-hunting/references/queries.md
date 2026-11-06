# Query recipes

Aggregate queries for the derived metrics in [`claude-code-telemetry.md`](claude-code-telemetry.md), one section per `<telemetry-backend>`. Every recipe returns grouped numbers, never raw events. Run them from a cheap-tier subagent and keep only the result table.

Placeholders: `<repo-key>` / `<repo>` is the `<repo-filter>` attribute and value; `<since>` is the window start as ISO 8601 UTC.

**Prefer events over metrics for token math.** `api_request` events carry all four token buckets, the model, the source and the cost in one record, and they don't depend on counter temporality. Use metrics where events aren't collected, and for the per-PR and per-commit counts.

## Prometheus (metrics only)

Prometheus holds metrics, not events. With it alone you can measure the cache-hit ratio, tokens per session and per PR, cost by model, source, agent and skill, and output share. The session floor, tool result sizes, compactions and error rates need a logs backend too.

**Find the real metric names first.** Exporters translate names (dots to underscores, and sometimes unit and `_total` suffixes), and the Claude Code docs don't fix the result. Discover the names and substitute them into the recipes:

```promql
count by (__name__) ({__name__=~"claude_code.*"})
```

A collector's Prometheus exporter typically yields `claude_code_token_usage_tokens_total` (`TOKENS` below), `claude_code_cost_usage_USD_total` (`COST`), `claude_code_session_count_total` (`SESSIONS`) and `claude_code_active_time_seconds_total`. The commit, pull-request and lines-of-code counters (`PRS`) only appear once a session has committed or opened a PR. Prometheus also needs cumulative counters: set `OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE=cumulative` user-side, or convert delta to cumulative in the collector. Labels lose their dots too, so `agent.name` becomes `agent_name`. Behind a collector, scope to Claude Code with `exported_job="claude-code"`.

**`increase()` can read zero here.** With `session_id` on every series (the default), each session is its own short-lived counter. A series born inside the window at its final value has no earlier sample to increase from, so `increase()` returns 0 even though the series exist. Sum each series' last value instead:

```promql
# Tokens by bucket over the window (per-session-series safe)
sum by (type) (max_over_time(TOKENS{<repo-key>="<repo>"}[7d]))

# Cache-hit ratio, window vs baseline (baseline = the 28 days before the window)
  sum(max_over_time(TOKENS{<repo-key>="<repo>", type="cacheRead"}[7d]))
/ sum(max_over_time(TOKENS{<repo-key>="<repo>", type=~"input|cacheRead|cacheCreation"}[7d]))

  sum(max_over_time(TOKENS{<repo-key>="<repo>", type="cacheRead"}[28d] offset 7d))
/ sum(max_over_time(TOKENS{<repo-key>="<repo>", type=~"input|cacheRead|cacheCreation"}[28d] offset 7d))

# Cost by model and source: premium spend on subagents is the model-mismatch lead
sort_desc(sum by (model, query_source) (max_over_time(COST{<repo-key>="<repo>"}[7d])))

# Cost attributed to agents, skills and MCP servers (empty if your version lacks these labels)
topk(15, sum by (agent_name, skill_name, mcp_server_name) (max_over_time(COST{<repo-key>="<repo>"}[7d])))

# Sessions (one series per session, so count distinct session_id), then tokens per session and per PR
count(count by (session_id) (max_over_time(SESSIONS{<repo-key>="<repo>"}[7d])))
sum(max_over_time(TOKENS{<repo-key>="<repo>"}[7d])) / count(count by (session_id) (max_over_time(SESSIONS{<repo-key>="<repo>"}[7d])))
sum(max_over_time(TOKENS{<repo-key>="<repo>"}[7d])) / sum(max_over_time(PRS{<repo-key>="<repo>"}[7d]))

# Output share
  sum(max_over_time(TOKENS{<repo-key>="<repo>", type="output"}[7d]))
/ sum(max_over_time(TOKENS{<repo-key>="<repo>"}[7d]))
```

`max_over_time` overstates a session that started before the window, because its counter already held pre-window tokens. For exact windowed token math, use the Loki or SQL event recipes, which don't have this problem. If you turned `session_id` off on metrics (`OTEL_METRICS_INCLUDE_SESSION_ID=false`), the counters are long-lived and `increase()` is correct again.

Run instant queries through the HTTP API so only the result vector comes back:

```bash
curl -sG "$PROM_URL/api/v1/query" --data-urlencode 'query=<promql>' \
  | jq -c '.data.result[] | {m: .metric, v: .value[1]}'
```

## Loki (events)

A collector exporting logs to Loki over OTLP puts every event in one stream, typically `{service_name="claude-code"}`. Event attributes (`event_name`, `session_id`, `query_source`, the token counts) land as **structured metadata, not stream labels**. Filter them in the pipeline (`| event_name="api_request"`), not in the selector. `unwrap` takes one field per query, so pull the four token buckets with four queries.

```logql
# Event volume by type: what is this deployment emitting at all?
sum by (event_name) (count_over_time({service_name="claude-code"} | <repo-key>="<repo>" [7d]))

# Token buckets and cost by model and source (repeat unwrap for input_tokens,
# output_tokens, cache_read_tokens, cache_creation_tokens, cost_usd)
sum by (model, query_source) (sum_over_time(
  {service_name="claude-code"} | event_name="api_request" | <repo-key>="<repo>" | unwrap cache_read_tokens [7d]))

# Tool output bytes and failures by tool
sum by (tool_name) (sum_over_time(
  {service_name="claude-code"} | event_name="tool_result" | <repo-key>="<repo>" | unwrap tool_result_size_bytes [7d]))
sum by (tool_name) (count_over_time(
  {service_name="claude-code"} | event_name="tool_result" | success="false" | <repo-key>="<repo>" [7d]))

# Churn and thrash
sum by (status_code) (count_over_time({service_name="claude-code"} | event_name="api_error" | <repo-key>="<repo>" [7d]))
sum by (tool_name) (count_over_time({service_name="claude-code"} | event_name="tool_decision" | decision="reject" | <repo-key>="<repo>" [7d]))
count_over_time({service_name="claude-code"} | event_name="compaction" | <repo-key>="<repo>" [7d])
sum by (agent_type, model) (sum_over_time(
  {service_name="claude-code"} | event_name="subagent_completed" | <repo-key>="<repo>" | unwrap total_tokens [7d]))
```

Run instant metric queries at the window end (`/loki/api/v1/query` with `time=<end>`). Through Grafana, the datasource proxy path is `/api/datasources/proxy/uid/<loki-uid>/loki/api/v1/…`.

**Session floor.** LogQL can't take each session's first request, so pull the requests stripped to five fields and reduce them locally. `keep` drops every other label (emails, ids beyond the session) and `line_format "-"` drops the body, so nothing else comes back:

```bash
curl -sG <auth> "$LOKI/loki/api/v1/query_range" \
  --data-urlencode 'query={service_name="claude-code"} | event_name="api_request" | <repo-key>="<repo>" | query_source=~"main|repl_main_thread|sdk" | keep session_id, query_source, input_tokens, cache_read_tokens, cache_creation_tokens | line_format "-"' \
  --data-urlencode 'direction=forward' --data-urlencode 'limit=5000' \
  --data-urlencode "start=<lookback-start-ns>" --data-urlencode "end=<window-end-ns>" \
| jq -c --arg since <window-start-ns> '[.data.result[] | .stream as $s | .values[]
    | {ts: .[0], s: $s.session_id, src: $s.query_source,
       f: ([$s.input_tokens, $s.cache_read_tokens, $s.cache_creation_tokens] | map(tonumber) | add)}]
  | group_by(.s) | map(min_by(.ts)) | map(select(.ts >= $since))
  | group_by(.src) | map({src: .[0].src, sessions: length, floor_p50: (map(.f) | sort | .[length/2|floor])})'
```

Start the pull a day before the window (`<lookback-start-ns>`) so a session's true first request is found, then keep only sessions that started in the window. Timestamps are nanosecond strings of equal length, so they compare correctly as strings. If a window holds more than `limit` requests, page by advancing `start` past the last timestamp returned. The output is one row per `query_source`, numbers only.

## OTLP file export (collector `file` exporter)

Claude Code has no file exporter of its own. Point it at an OpenTelemetry Collector that writes both signals to disk:

```yaml
receivers:
  otlp:
    protocols: { grpc: {}, http: {} }
exporters:
  file:
    path: /var/lib/otelcol/claude-code.jsonl
    rotation: { max_megabytes: 100, max_backups: 20 }
service:
  pipelines:
    metrics: { receivers: [otlp], exporters: [file] }
    logs:    { receivers: [otlp], exporters: [file] }
```

Each line is one export batch in OTLP JSON. Attribute values arrive as `{"stringValue": …}`, `{"intValue": "…"}` or `{"doubleValue": …}`. Integers come as strings, so convert before summing.

**Step 1: flatten events** to one compact record per event, filtered to the repo. Save as `events.jq`:

```jq
def kv: (. // []) | map({(.key): (.value | to_entries[0].value)}) | add // {};
def n: (. // 0) | tonumber;
.resourceLogs[]?
| (.resource.attributes | kv) as $res
| .scopeLogs[]?.logRecords[]?
| (.attributes | kv) as $a
| select(($res[$rk] // $a[$rk]) == $rv)
| ($a["event.name"] // .body.stringValue // "" | sub("^claude_code\\."; "")) as $ev
| {ev: $ev,
   ts: ($a["event.timestamp"] // (.timeUnixNano // "0" | tonumber / 1e9 | floor | todate)),
   session: ($a["session.id"] // $res["session.id"]),
   model: $a.model, src: $a.query_source, tool: $a.tool_name, ok: ($a.success | tostring),
   input: ($a.input_tokens | n), output: ($a.output_tokens | n),
   cread: ($a.cache_read_tokens | n), cwrite: ($a.cache_creation_tokens | n),
   cost: ($a.cost_usd | n), result_bytes: ($a.tool_result_size_bytes | n)}
```

**Step 2: roll up** one window, `[$since, $until)`, to the derived metrics. Save as `rollup.jq`:

```jq
def total(f): map(f) | add // 0;
. as $all
| map(select(.ts >= $since and .ts < $until)) as $win
| ($win | map(select(.ev == "api_request"))) as $req
| ($win | map(select(.ev == "tool_result"))) as $tr
# Floor: each session's first main-thread request ever, kept only if the session started in the window.
| ($all | map(select(.ev == "api_request" and ((.src // "") | test("^(main|repl_main_thread)$")))) | group_by(.session)
    | map(min_by(.ts) | select(.ts >= $since and .ts < $until) | .input + .cread + .cwrite)
    | sort) as $floors
| {
    sessions: ($req | map(.session) | unique | length),
    requests: ($req | length),
    tokens: {input: ($req | total(.input)), output: ($req | total(.output)),
             cacheRead: ($req | total(.cread)), cacheCreation: ($req | total(.cwrite))},
    cache_hit_ratio: (($req | total(.cread)) / ([($req | total(.input + .cread + .cwrite)), 1] | max) * 1000 | round / 1000),
    floor_sessions: ($floors | length),
    floor_p50: ($floors[($floors | length) / 2 | floor] // 0),
    cost_by_model_source: ($req | group_by([.model, .src])
      | map({key: "\(.[0].model)/\(.[0].src)", value: (total(.cost) * 100 | round / 100)}) | from_entries),
    tools: ($tr | group_by(.tool)
      | map({key: .[0].tool, value: {calls: length, failed: (map(select(.ok == "false")) | length),
                                     result_bytes: total(.result_bytes)}}) | from_entries)
  }
```

Flatten once, then roll up the window and the baseline from the same records. Feed the rollup everything retained, not only the window: the floor needs to see a session's true first request, so a session that started before `$since` doesn't count its mid-session prefix as a floor.

```bash
jq -c --arg rk <repo-key> --arg rv <repo> -f events.jq /var/lib/otelcol/claude-code*.jsonl > events.ndjson
jq -s --arg since <window-start> --arg until <now> -f rollup.jq events.ndjson
jq -s --arg since <baseline-start> --arg until <window-start> -f rollup.jq events.ndjson
```

Window bounds are compared as strings, so pass them in the same ISO 8601 UTC form `event.timestamp` uses, such as `2026-01-01T00:00:00.000Z`. Records without `event.timestamp` fall back to the record's `timeUnixNano`. The flattened records hold no prompt text or tool input, but they do hold session ids, so keep `events.ndjson` in the job temp dir and delete it after the tick.

## SQL: ClickHouse via the collector's `clickhouse` exporter

These queries assume the exporter's default tables: `otel_logs` (`Timestamp`, `Body`, `ResourceAttributes` and `LogAttributes` as `Map(String, String)`) and `otel_metrics_sum` (`MetricName`, `Attributes`, `ResourceAttributes`, `Value`, `TimeUnix`). They haven't been run against a live store, so check the table and column names against your schema first. Other SQL stores need the same logic with their own map-access syntax.

Attributes can land in `LogAttributes` or `ResourceAttributes` depending on the version and on how the repo tag was set. The `if(LogAttributes[…] != '', …, ResourceAttributes[…])` filter below checks both.

```sql
-- Window token buckets, cache-hit ratio and cost by model and source
WITH
  if(LogAttributes['<repo-key>'] != '', LogAttributes['<repo-key>'], ResourceAttributes['<repo-key>']) AS repo
SELECT
  LogAttributes['model']        AS model,
  LogAttributes['query_source'] AS src,
  count()                                                  AS requests,
  sum(toUInt64OrZero(LogAttributes['input_tokens']))          AS input,
  sum(toUInt64OrZero(LogAttributes['output_tokens']))         AS output,
  sum(toUInt64OrZero(LogAttributes['cache_read_tokens']))     AS cache_read,
  sum(toUInt64OrZero(LogAttributes['cache_creation_tokens'])) AS cache_write,
  round(cache_read / greatest(input + cache_read + cache_write, 1), 3) AS cache_hit_ratio,
  round(sum(toFloat64OrZero(LogAttributes['cost_usd'])), 2)  AS cost_usd
FROM otel_logs
WHERE match(LogAttributes['event.name'], 'api_request$')
  AND repo = '<repo>'
  AND Timestamp >= parseDateTimeBestEffort('<since>')
GROUP BY model, src
ORDER BY cost_usd DESC;

-- Session floor: prompt-side tokens on each session's first main-thread request.
-- Scan a day before the window so a session's true first request is found, then keep
-- only sessions that started inside the window.
SELECT
  count()                           AS sessions,
  quantileExact(0.5)(floor_tokens)  AS floor_p50,
  quantileExact(0.9)(floor_tokens)  AS floor_p90
FROM (
  SELECT
    LogAttributes['session.id'] AS s,
    min(Timestamp)              AS started,
    argMin(toUInt64OrZero(LogAttributes['input_tokens'])
         + toUInt64OrZero(LogAttributes['cache_read_tokens'])
         + toUInt64OrZero(LogAttributes['cache_creation_tokens']), Timestamp) AS floor_tokens
  FROM otel_logs
  WHERE match(LogAttributes['event.name'], 'api_request$')
    AND LogAttributes['query_source'] IN ('main', 'repl_main_thread')
    AND if(LogAttributes['<repo-key>'] != '', LogAttributes['<repo-key>'], ResourceAttributes['<repo-key>']) = '<repo>'
    AND Timestamp >= parseDateTimeBestEffort('<since>') - INTERVAL 1 DAY
  GROUP BY s
  HAVING started >= parseDateTimeBestEffort('<since>')
);

-- Tool output and failures by tool
SELECT
  LogAttributes['tool_name'] AS tool,
  count() AS calls,
  countIf(LogAttributes['success'] = 'false') AS failed,
  sum(toUInt64OrZero(LogAttributes['tool_result_size_bytes'])) AS result_bytes,
  quantileExact(0.9)(toUInt64OrZero(LogAttributes['tool_result_size_bytes'])) AS result_bytes_p90
FROM otel_logs
WHERE match(LogAttributes['event.name'], 'tool_result$')
  AND if(LogAttributes['<repo-key>'] != '', LogAttributes['<repo-key>'], ResourceAttributes['<repo-key>']) = '<repo>'
  AND Timestamp >= parseDateTimeBestEffort('<since>')
GROUP BY tool
ORDER BY result_bytes DESC
LIMIT 15;

-- Churn: API errors by status and retry attempt, and repeated permission rejects
SELECT LogAttributes['status_code'] AS status, LogAttributes['attempt'] AS attempt, count() AS n
FROM otel_logs
WHERE match(LogAttributes['event.name'], 'api_error$')
  AND if(LogAttributes['<repo-key>'] != '', LogAttributes['<repo-key>'], ResourceAttributes['<repo-key>']) = '<repo>'
  AND Timestamp >= parseDateTimeBestEffort('<since>')
GROUP BY status, attempt ORDER BY n DESC;

SELECT LogAttributes['tool_name'] AS tool, count() AS rejects, uniqExact(LogAttributes['session.id']) AS sessions
FROM otel_logs
WHERE match(LogAttributes['event.name'], 'tool_decision$')
  AND LogAttributes['decision'] = 'reject'
  AND if(LogAttributes['<repo-key>'] != '', LogAttributes['<repo-key>'], ResourceAttributes['<repo-key>']) = '<repo>'
  AND Timestamp >= parseDateTimeBestEffort('<since>')
GROUP BY tool ORDER BY rejects DESC LIMIT 15;

-- Compactions per session, and subagent spend by agent type
SELECT
  countIf(match(LogAttributes['event.name'], 'compaction$')) / greatest(uniqExact(LogAttributes['session.id']), 1) AS compactions_per_session
FROM otel_logs
WHERE if(LogAttributes['<repo-key>'] != '', LogAttributes['<repo-key>'], ResourceAttributes['<repo-key>']) = '<repo>'
  AND Timestamp >= parseDateTimeBestEffort('<since>');

SELECT LogAttributes['agent_type'] AS agent_type, LogAttributes['model'] AS model,
       count() AS runs, sum(toUInt64OrZero(LogAttributes['total_tokens'])) AS tokens
FROM otel_logs
WHERE match(LogAttributes['event.name'], 'subagent_completed$')
  AND if(LogAttributes['<repo-key>'] != '', LogAttributes['<repo-key>'], ResourceAttributes['<repo-key>']) = '<repo>'
  AND Timestamp >= parseDateTimeBestEffort('<since>')
GROUP BY agent_type, model ORDER BY tokens DESC;

-- Idle-gap rewrites: requests after a gap longer than the cache TTL (<ttl> seconds:
-- 300, or 3600 where the 1-hour TTL applies) that rewrote most of the prefix
SELECT countIf(gap_s > <ttl> AND cwrite * 2 >= side AND side > 0) AS idle_gap_rewrites,
       sumIf(cwrite, gap_s > <ttl> AND cwrite * 2 >= side)       AS idle_gap_write_tokens
FROM (
  SELECT
    toUInt64OrZero(LogAttributes['cache_creation_tokens']) AS cwrite,
    toUInt64OrZero(LogAttributes['input_tokens'])
      + toUInt64OrZero(LogAttributes['cache_read_tokens']) + cwrite AS side,
    dateDiff('second',
      lagInFrame(Timestamp, 1, Timestamp) OVER (PARTITION BY LogAttributes['session.id'] ORDER BY Timestamp
                                                ROWS BETWEEN 1 PRECEDING AND CURRENT ROW),
      Timestamp) AS gap_s
  FROM otel_logs
  WHERE match(LogAttributes['event.name'], 'api_request$')
    AND LogAttributes['query_source'] IN ('main', 'repl_main_thread')
    AND if(LogAttributes['<repo-key>'] != '', LogAttributes['<repo-key>'], ResourceAttributes['<repo-key>']) = '<repo>'
    AND Timestamp >= parseDateTimeBestEffort('<since>')
);

-- Pull requests and commits in the window (delta temporality: sum the points)
SELECT MetricName, sum(Value) AS n
FROM otel_metrics_sum
WHERE MetricName IN ('claude_code.pull_request.count', 'claude_code.commit.count')
  AND if(Attributes['<repo-key>'] != '', Attributes['<repo-key>'], ResourceAttributes['<repo-key>']) = '<repo>'
  AND TimeUnix >= parseDateTimeBestEffort('<since>')
GROUP BY MetricName;
```

With cumulative temporality, take `max(Value) - min(Value)` per series instead of `sum(Value)`.

## Usage the lane can see without telemetry

If no backend is set up yet, transcripts alone ([`transcripts.md`](transcripts.md)) give tokens by bucket, the floor, tool result sizes, compactions and the per-model split, but not cost or per-PR normalization. Run the hunt on transcripts and open the setup PR from [`claude-code-telemetry.md`](claude-code-telemetry.md) § Setup first.
