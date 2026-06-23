---
description: Emergency load-shedding when sub-agents overload the machine — OOM, runaway pre-push hooks, memory-compressor or swap pressure. Kills the newest agents first (least invested work) until pressure stabilizes, then salvages their worktrees. Example — /kill, /kill 3, /kill all
argument-hint: [count | all]
agent: agent
---

# /kill — emergency agent load-shedding

Arguments: `${input:args}` — empty means **stabilize automatically** (kill newest-first until pressure recovers); a number kills exactly that many newest agents; `all` stops every running sub-agent. This is an emergency command: act immediately, measure, report after — do not ask for confirmation mid-incident.

**Why newest-first (LIFO):** the newest agents have invested the least work; the oldest are closest to a push or PR. Killing newest-first sheds the same load while destroying the least progress — and killed agents' worktrees survive, so their work is salvageable either way (see step 5).

## Steps

1. **Measure once, fast.** Memory pressure (`memory_pressure` on macOS — read the percentage and state; `vm_stat` for compressor/swap activity; on Linux, `free -m` + `/proc/pressure/memory`), load average (`uptime`), and the top memory consumers (`ps aux | sort -rk4` — look for agent-spawned trees: test runners like vitest/playwright/jest workers, bundlers, language servers spawned under worktree paths). One snapshot is enough — the situation is degrading while you measure.

2. **Stop new spending immediately.** No new dispatches, no new pushes (each push may fan out a pre-push hook test suite — that is usually the very load source). If an orchestration loop is running, hold all free slots (see orchestrating-slots backpressure).

3. **Kill newest-first, in waves.** List running sub-agents (TaskList / your harness's running-task view), order by start time descending:
   - Stop the newest agent via the harness (TaskStop or equivalent) — graceful, the harness records the kill.
   - Then sweep its orphans: hook-spawned processes (test runners, watchers) under that agent's worktree path that survived the parent — `kill` (TERM) the process group first, escalate to `-9` only for survivors after a few seconds.
   - Wave size: 1–2 agents, then re-measure (step 4). With an explicit count or `all`, do the whole batch in one wave.
   - **Never touch**: your own session's process tree, other operators' processes, anything not descended from an agent you started. When in doubt about a process's owner, leave it — a missed orphan costs memory; killing the wrong tree costs someone else's work.

4. **Re-measure and repeat.** After each wave, re-read memory pressure and load. Stabilized means: pressure back to normal/warn (not critical), no swap death-spiral, load average heading under core count. If two waves haven't moved the needle, the load source may not be agents — check for runaway non-agent processes and report instead of blindly killing more.

5. **Salvage, then report.** Killed agents' worktrees retain all committed and uncommitted work. For each: `git -C <worktree> log <integration-branch>..HEAD --oneline` + `git status --short` — per the dispatching-subagents salvage protocol, finished work gets pushed/PR'd by you (one at a time, serialized — see why below), partial work resumes from the last commit on re-dispatch, only empty worktrees need a from-scratch re-dispatch. Report: pressure before/after, agents killed (and what each had completed), salvage plan, and the recommended lower slot count.

6. **Prevent the recurrence.** The classic cause is N simultaneous pushes each running a full local pre-push suite — N × the suite's footprint. Recommend to the operator: lower `<slot-count>` (re-issue `/dispatch` with fewer slots), and serialize pushes when slots are high (orchestrator-performed pushes are naturally serial; agent-performed pushes are not). Note the incident in the session log so the next orchestration round starts at the reduced cap.
