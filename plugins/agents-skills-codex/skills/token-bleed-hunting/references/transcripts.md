# Transcript forensics

Telemetry gives you the size of the bleed. Transcripts give you the mechanism: which tool call returned 200 KB, which turn rewrote the cache, which file got read nine times. They also hold everything the user typed and every file the agent saw, so handle them as confidential.

## Where they live

Claude Code writes one JSONL file per session under `~/.claude/projects/<escaped-project-path>/<session-id>.jsonl`. The project path is the launch directory with `/`, `.`, `_` and spaces turned into `-`. Subagent transcripts sit in `<session-id>/subagents/`, in the same format, and oversized tool output may be split out into `<session-id>/tool-results/`. Retention follows `cleanupPeriodDays` (default 30 days), so a window older than that has no transcripts.

Worktree sessions get their own project directory (the worktree path, escaped), so a repo's transcripts are spread across its main checkout's directory and one per worktree. Collect all of them for `<transcript-root>`.

**The format is internal and changes between versions.** The field names below match recent versions. Discover before you trust.

## Rules

1. **Never read a transcript into your own context.** Have a cheap-tier subagent run the parser and return its JSON.
2. **The parser's output is the only thing that leaves.** It returns counts, sizes, model names, tool names and paths relative to `--root` only. No text, no tool input or output, no ids, no paths outside the repo.
3. Run Python with `-I` and pass transcript paths as arguments, so nothing in a transcript directory can shadow a module.

## Discover the format (keys, never values)

```bash
python3 -I <skill-dir>/scripts/transcript-stats.py --keys <one-session>.jsonl
```

This prints key paths with counts and no values. Check that what the parser reads still exists:

| Signal | Field (recent versions) |
|---|---|
| Per-request usage | `message.usage.input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens` (split under `cache_creation.ephemeral_5m_input_tokens` / `ephemeral_1h_input_tokens`) on `type: "assistant"` entries |
| Request identity | `message.id` / `requestId`. One response can span several lines that repeat the same usage, so count each id once |
| Model | `message.model`. `<synthetic>` marks harness-generated entries with no API call |
| Tool calls | `message.content[]` blocks with `type: "tool_use"` (`id`, `name`, `input`) |
| Tool results | `message.content[]` blocks with `type: "tool_result"` (`tool_use_id`, `content`, `is_error`) on `type: "user"` entries |
| Subagent turns | files under `subagents/`, or `isSidechain: true` |
| Compaction | `isCompactSummary: true`, or `type: "system"` with `subtype: "compact_boundary"` |
| Timing | `timestamp` (ISO 8601) |

If a field moved, fix the parser and say so in the tick report. Never fall back to reading raw lines.

## Run the parser

```bash
python3 -I <skill-dir>/scripts/transcript-stats.py \
  --root <repo-root> --ttl 300 \
  <transcript-root>/*.jsonl <transcript-root>/*/subagents/*.jsonl
```

`--root` limits named file paths to the repo. A `Read` outside it, or one whose path can't be resolved, is never named and never counted as a repeat read. `--ttl` is the cache TTL in seconds for idle-gap detection; use `3600` where the 1-hour TTL applies. A request counts as an idle-gap rewrite when it follows a longer gap and at least half its prompt-side tokens are cache writes.

Each response is counted once across all files passed, so a resumed or forked session that copies earlier messages doesn't double them. Subagent files feed the totals but not `sessions` or the floor, so gate `<min-sessions>` on `sessions`. Unreadable files are skipped and counted in `unreadable`.

Output (abridged):

```json
{
 "sessions": 12, "subagent_files": 4, "unreadable": 0,
 "totals": {
  "requests": 4800, "sidechain_requests": 150,
  "input": 90000, "output": 3500000, "cache_read": 1900000000, "cache_write": 30000000,
  "cache_hit_ratio": 0.984, "floor_p50": 42000, "floor_p90": 61000,
  "idle_gap_rewrites": 180, "compactions": 40,
  "by_model": {"<model>": {"requests": 3000, "prompt_tokens": 1200000000, "output": 2400000}},
  "tools_by_result_bytes": {"Read": {"calls": 400, "errors": 12, "result_bytes": 16000000}}
 },
 "per_file": {"s1": {"floor": 40000, "compactions": 9, "repeat_reads": {"docs/large-spec.md": 9}}}
}
```

Files are numbered in output, `s1…sN` for sessions and `a1…aN` for subagent files, never named by id.

## From signal to mechanism

| Parser signal | What to look at next (by asking the subagent for counts, not content) |
|---|---|
| High `floor_p50` | The always-loaded chain: line and byte counts of every `CLAUDE.md`/`AGENTS.md` that loads for this repo, the number of MCP tools, total skill and agent description length. Measure files in the repo, not the transcript |
| `idle_gap_rewrites` high | Gap length distribution. If most gaps are just over 5 minutes, a 1-hour TTL may pay. If they're hours long, it won't |
| Low `cache_hit_ratio` with few gaps | Model switches (`by_model` mixing in one session), MCP connects mid-session (telemetry `mcp_server_connection`), hook output that differs per turn |
| One tool dominates `result_bytes` | The command or path pattern behind it: for `Bash`, the first word of each command and its result size; for `Read`, repo-relative paths and sizes. Patterns, not outputs |
| `repeat_reads` | Whether the file is large and whether a summary or map exists for it |
| Many `compactions` | What filled the context before each one: tool result bytes since the previous compaction, by tool |
| High `errors` on one tool | Error types and the command or path pattern. A stale instruction or a broken hook usually explains a repeating one |
| Expensive model on subagents | `by_model` restricted to subagent files, plus which agent definitions dispatched them |

Every finding you take into Step 3 should end as a pointer to a harness-config `file:line`, plus numbers.
