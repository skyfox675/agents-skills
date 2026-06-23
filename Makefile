.PHONY: sync sync-commands sync-agents check check-commands check-agents

# Regenerate every Cursor/Copilot mirror from the canonical Claude sources.
sync: sync-commands sync-agents

# Fail if any mirror is out of date — wire into CI or a pre-commit hook.
check: check-commands check-agents

# Commands: .claude/commands -> .cursor/commands + .github/prompts
sync-commands:
	python3 scripts/sync-commands.py
check-commands:
	python3 scripts/sync-commands.py --check

# Agents: .claude/agents -> .cursor/agents + .github/agents
sync-agents:
	python3 scripts/sync-agents.py
check-agents:
	python3 scripts/sync-agents.py --check
