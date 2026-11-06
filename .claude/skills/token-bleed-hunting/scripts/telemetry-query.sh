#!/bin/sh
# Run one aggregate PromQL or LogQL query and print numbers only.
#
# Usage:
#   telemetry-query.sh prom  '<promql>'
#   telemetry-query.sh loki  '<logql metric query>' [<unix-time>]
#   telemetry-query.sh floor '<logql selector and filters>' <window-start-unix> [<window-end-unix>]
#
# prom and loki print one line per result series: its grouping labels, a tab,
# and the value. floor pulls each session's api_request events stripped to five
# fields and prints one JSON row per query_source with the session count and
# the p50/p90 floor, counting only sessions that started inside the window.
#
# Environment:
#   PROM_URL          Prometheus API base, e.g. http://localhost:9090 or
#                     https://<grafana>/api/datasources/proxy/uid/<prometheus-uid>
#   LOKI_URL          Loki API base, e.g. http://localhost:3100 or
#                     https://<grafana>/api/datasources/proxy/uid/<loki-uid>
#   TELEMETRY_CURLRC  optional curl config file holding the auth line
#                     (user = "..." or header = "Authorization: Bearer ..."),
#                     mode 600 and outside any repo
#
# Queries must be wrapped in an aggregation (sum, count, topk, ...). A bare
# selector or a bare *_over_time returns every label, including user emails and
# account ids, so it is refused.
set -eu

die() { printf 'telemetry-query: %s\n' "$*" >&2; exit 2; }

fetch() {
  if [ -n "${TELEMETRY_CURLRC:-}" ]; then
    curl -sS -m 60 -G -K "$TELEMETRY_CURLRC" "$@"
  else
    curl -sS -m 60 -G "$@"
  fi
}

# Backends answer some errors in plain text (range limits, auth); show those
# instead of failing inside jq.
reduce() {
  body=$(cat)
  if printf '%s' "$body" | jq -e . >/dev/null 2>&1; then
    printf '%s' "$body" | jq "$@"
  else
    printf 'error: %s\n' "$(printf '%s' "$body" | head -c 300)"
    return 1
  fi
}

require_aggregate() {
  printf '%s' "$1" | grep -Eq '^[[:space:]]*(sum|count|avg|min|max|topk|bottomk|sort|sort_desc|quantile|stddev|stdvar|group)[[:space:]]*(\(|by[[:space:]]*\(|without[[:space:]]*\()' \
    || die "refusing a non-aggregate query; wrap it in sum by (...) / count by (...)"
}

# One line per series: sorted label=value pairs (or "-"), a tab, the value.
VECTOR='if .status != "success" then "error: \(.error // .status)"
  elif .data.resultType == "scalar" then "-\t\(.data.result[1])"
  else .data.result[]
    | ((.metric // {}) | del(.__name__) | to_entries | sort_by(.key)
       | map("\(.key)=\(.value)") | join(",")) as $l
    | "\(if $l == "" then "-" else $l end)\t\(.value[1])"
  end'

mode=${1:-}
[ $# -ge 2 ] || die "usage: telemetry-query.sh prom|loki|floor '<query>' [...]"
query=$2

case $mode in
  prom)
    [ -n "${PROM_URL:-}" ] || die "PROM_URL is not set"
    require_aggregate "$query"
    fetch "$PROM_URL/api/v1/query" --data-urlencode "query=$query" | reduce -r "$VECTOR"
    ;;
  loki)
    [ -n "${LOKI_URL:-}" ] || die "LOKI_URL is not set"
    require_aggregate "$query"
    at=${3:-$(date +%s)}
    fetch "$LOKI_URL/loki/api/v1/query" --data-urlencode "query=$query" --data-urlencode "time=$at" | reduce -r "$VECTOR"
    ;;
  floor)
    [ -n "${LOKI_URL:-}" ] || die "LOKI_URL is not set"
    [ $# -ge 3 ] || die "floor needs <window-start-unix>"
    start=$3
    end=${4:-$(date +%s)}
    # Look back a day so a session's true first request is found.
    lookback=$((start - 86400))
    full="$query | keep session_id, query_source, input_tokens, cache_read_tokens, cache_creation_tokens | line_format \"-\""
    fetch "$LOKI_URL/loki/api/v1/query_range" \
      --data-urlencode "query=$full" --data-urlencode 'direction=forward' --data-urlencode 'limit=5000' \
      --data-urlencode "start=${lookback}000000000" --data-urlencode "end=${end}000000000" \
    | reduce -c --arg since "${start}000000000" '
        if .status != "success" then "error: \(.error // .status)" else
        [.data.result[] | .stream as $s | .values[]
          | {ts: .[0], s: $s.session_id, src: ($s.query_source // "?"),
             f: ([$s.input_tokens, $s.cache_read_tokens, $s.cache_creation_tokens] | map(tonumber? // 0) | add)}] as $rows
        | ($rows | length) as $n
        # First request per session per source: a session often opens with a title-generation call.
        | ($rows | group_by([.s, .src]) | map(min_by(.ts)) | map(select(.ts >= $since))
           | group_by(.src)
           | map((map(.f) | sort) as $f
                 | {query_source: .[0].src, sessions: length,
                    floor_p50: $f[length / 2 | floor], floor_p90: $f[(length * 0.9) | floor]})),
          (if $n >= 5000 then "warning: hit the 5000-request limit; narrow the window or page by start" else empty end)
        end'
    ;;
  *)
    die "unknown mode '$mode' (prom, loki or floor)"
    ;;
esac
