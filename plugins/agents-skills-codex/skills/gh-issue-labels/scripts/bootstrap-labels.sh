#!/usr/bin/env bash
# bootstrap-labels.sh — create the gh-issue-labels taxonomy in a GitHub repo.
#
# Idempotent: uses `gh label create --force`, which updates the description/color
# of an existing label instead of failing. Safe to re-run any time the taxonomy
# or your model lineup changes. When a same-named label already exists, the script
# echoes "updating existing label <name>" before overwriting.
#
# Usage:
#   bootstrap-labels.sh [-R owner/repo] workhorse-model [premium-model ...]
#
#   -R owner/repo   Target repository (defaults to the repo of the current
#                   directory, as resolved by gh).
#   Positional args Model identifiers for the agent-model:* family. Required.
#                   The FIRST is the workhorse tier; any others are premium tiers.
#                   Pass ONLY workhorse + premium identifiers — the script has no
#                   way to detect which model is your cheap tier; the convention
#                   (no cheap-tier label) is your responsibility to enforce by
#                   omitting that identifier from the argument list.
#                   Example: sonnet opus fable
#
# Deliberately absent: a label for the cheap model tier. The label family grants
# or pins spending authority only — it must not allow forcing code-writing work
# onto a model tier proven to ship subtle bugs. See SKILL.md.

set -euo pipefail

REPO_ARGS=()
while getopts ":R:h" opt; do
  case "$opt" in
    R) REPO_ARGS=(--repo "$OPTARG") ;;
    h)
      sed -n '2,23p' "$0"
      exit 0
      ;;
    \?)
      echo "Unknown option: -$OPTARG" >&2
      exit 2
      ;;
    :)
      echo "Option -$OPTARG requires an argument" >&2
      exit 2
      ;;
  esac
done
shift $((OPTIND - 1))

if [ "$#" -eq 0 ]; then
  echo "Usage: bootstrap-labels.sh [-R owner/repo] workhorse-model [premium-model ...]" >&2
  echo "  Example: bootstrap-labels.sh -R acme/widgets sonnet opus fable" >&2
  echo "  Pass ONLY workhorse + premium identifiers; omit your cheap-tier model." >&2
  exit 2
fi

MODELS=("$@")
WORKHORSE="${MODELS[0]}"

create_label() {
  local name="$1" color="$2" description="$3"
  # Check for pre-existing label and warn if we're about to overwrite it
  if gh label list "${REPO_ARGS[@]+"${REPO_ARGS[@]}"}" --json name --jq '.[].name' 2>/dev/null \
      | grep -qx "$name"; then
    echo "updating existing label $name"
  fi
  gh label create "$name" \
    "${REPO_ARGS[@]+"${REPO_ARGS[@]}"}" \
    --color "$color" \
    --description "$description" \
    --force
  echo "ok: $name"
}

# --- agent-model:* — per-issue model override ---------------------------------
# Workhorse pin: blue. Premium authorizations: purple (deliberate operator grant).
create_label "agent-model:${WORKHORSE}" "1d76db" \
  "Pin dispatches on this issue to the workhorse model (${WORKHORSE})"

for model in "${MODELS[@]:1}"; do
  create_label "agent-model:${model}" "5319e7" \
    "Operator authorization: dispatch this issue on ${model} (counts as explicit operator instruction)"
done

# --- agent-effort:* — effort directive carried in the dispatch prompt ---------
create_label "agent-effort:low" "c2e0c6" \
  "Quick mechanical change — dispatch brief says keep it minimal"
create_label "agent-effort:medium" "bfd4f2" \
  "Normal multi-step work — standard dispatch brief"
create_label "agent-effort:high" "f9d0c4" \
  "Careful multi-step work — brief requires verifying each acceptance criterion"
create_label "agent-effort:max" "d93f0b" \
  "Maximum thoroughness — brief says be exhaustive, no shortcuts"

# --- lifecycle / coordination ---------------------------------------------------
create_label "agent-claimed" "fbca04" \
  "Active orchestrator lock — paired with assignee + parseable lock comment; do not double-claim"
create_label "do-not-dispatch" "b60205" \
  "Operator hold — never claim, dispatch, or implement; only the operator removes this"
create_label "do-not-rebase" "d4c5f9" \
  "PR opt-out from auto-rebase automation (opt-in; only if the repo runs one) — apply ONLY after a rebase cancels CI, never proactively; remove before merge window"
create_label "ready-to-dispatch" "0e8a16" \
  "Advisory: groomed and dispatchable. NOT authoritative — re-verify assignees are empty before locking"

echo
echo "Done. Taxonomy bootstrapped with models: ${MODELS[*]} (workhorse: ${WORKHORSE})."
echo "Record your project bindings (workhorse/premium models, integration branch, etc.) in CLAUDE.md."
