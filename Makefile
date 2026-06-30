.PHONY: sync sync-commands sync-agents sync-skills check check-commands check-agents check-skills

# Regenerate every Cursor/Copilot/Kiro/OpenCode mirror from the canonical Claude sources.
sync: sync-commands sync-agents sync-skills

# Fail if any mirror is out of date — wire into CI or a pre-commit hook.
check: check-commands check-agents check-skills

# Commands: .claude/commands -> .cursor/commands + .github/prompts
sync-commands:
	python3 scripts/sync-commands.py
check-commands:
	python3 scripts/sync-commands.py --check

# Agents: .claude/agents -> .cursor/agents + .github/agents + .kiro/agents + .opencode/agents
sync-agents:
	python3 scripts/sync-agents.py
check-agents:
	python3 scripts/sync-agents.py --check

# Skills: symlink .kiro/skills + .opencode/skills -> .claude/skills (Cursor/Copilot read it directly)
sync-skills:
	python3 scripts/sync-skills.py
check-skills:
	python3 scripts/sync-skills.py --check
