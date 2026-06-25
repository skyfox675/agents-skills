#!/bin/sh
# install.sh — point this repo's git hooks at the hooks/ directory.
#
# Run from anywhere inside the target repo:
#   sh hooks/install.sh
#
# It sets core.hooksPath to this directory and makes the hook scripts
# executable. To uninstall:  git config --unset core.hooksPath
#
# Already using husky or another manager that owns core.hooksPath? Don't run
# this — instead call these scripts from your existing hooks, e.g. add
# `sh "$(git rev-parse --show-toplevel)/hooks/pre-commit"` to .husky/pre-commit.

set -e

dir=$(cd "$(dirname "$0")" && pwd)

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "install.sh: not inside a git repository." >&2
  exit 1
fi

chmod +x "$dir/commit-msg" "$dir/pre-commit" "$dir/pre-push" 2>/dev/null || true
git config core.hooksPath "$dir"

echo "✓ git hooks installed: core.hooksPath -> $dir"
echo "  active: commit-msg, pre-commit (gitleaks), pre-push (lint gate)"
echo
echo "CI templates (copy into .github/workflows/ to enforce server-side):"
echo "  cp $dir/pr-title.yml  .github/workflows/pr-title.yml     # PR title format"
echo "  cp $dir/gitleaks.yml  .github/workflows/gitleaks.yml     # secret scan (recommended)"
echo
echo "Optional local tools (hooks skip-if-absent):"
echo "  brew install gitleaks actionlint"
echo "  npm  i -g markdownlint-cli2"
