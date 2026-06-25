#!/bin/sh
# Claude Code PreToolUse hook — bridge the git hooks into the agent harness so
# the SAME checks fire BEFORE the model runs `git commit` / `git push`, not only
# at git time. One source of truth: this delegates to ./pre-commit and ./pre-push.
#
# Why bother when the git hooks already gate git? Two reasons:
#   1. Proactive feedback — the model sees the failure and self-corrects before
#      the commit/push instead of after.
#   2. It can't be `--no-verify`'d — a harness hook still runs even if the model
#      passes `git commit --no-verify`, which would skip the git-level hook.
#
# Wire it via .claude/settings.json (see hooks/claude-settings.hooks.json):
#   PreToolUse matcher "Bash" -> command: sh "$CLAUDE_PROJECT_DIR/hooks/claude-code-pretooluse.sh"
#
# Contract: reads the PreToolUse JSON on stdin, classifies the Bash command, and
#   - git ... commit  -> runs pre-commit (secret scan); exit 2 blocks the tool call
#   - git ... push    -> runs pre-push  (lint gate);    exit 2 blocks the tool call
#   - anything else    -> exit 0 (allow)
# Exit 2 is Claude Code's "blocking error" — stderr is fed back to the model.

hookdir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

# Run checks from the project root so relative project gates (make check, etc.)
# and markdownlint resolve correctly.
[ -n "$CLAUDE_PROJECT_DIR" ] && cd "$CLAUDE_PROJECT_DIR" 2>/dev/null || true

# Classify the git subcommand from the tool payload. python3 = no jq dependency;
# if python3 is absent, fall through to allow (the git-level hook still gates).
# NOTE: must be `python3 -c` (not a heredoc) so the tool JSON on this script's
# stdin stays readable by sys.stdin — a heredoc would shadow it.
action=$(python3 -c 'import json, re, sys
try:
    cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "")
except Exception:
    sys.exit(0)
if re.search(r"\bgit\b[^\n;&|]*\bcommit\b", cmd):
    print("commit")
elif re.search(r"\bgit\b[^\n;&|]*\bpush\b", cmd):
    print("push")' 2>/dev/null)

case "$action" in
  commit)
    if ! out=$("$hookdir/pre-commit" 2>&1); then
      printf '%s\n\nPreToolUse: blocked before `git commit` — secret scan failed. Fix the staged changes.\n' "$out" >&2
      exit 2
    fi ;;
  push)
    if ! out=$("$hookdir/pre-push" 2>&1); then
      printf '%s\n\nPreToolUse: blocked before `git push` — lint gate failed. Fix the issues above.\n' "$out" >&2
      exit 2
    fi ;;
esac

exit 0
