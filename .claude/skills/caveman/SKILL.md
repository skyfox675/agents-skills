---
name: caveman
description: "Ultra-compressed communication mode. Cuts token usage ~75% by speaking like caveman while keeping full technical accuracy. Supports intensity levels: lite, full (default), ultra, wenyan-lite, wenyan-full, wenyan-ultra. Use when user says \"caveman mode\", \"talk like caveman\", \"use caveman\", \"less tokens\", \"be brief\", or invokes /caveman. Also auto-triggers when token efficiency is requested."
---

# caveman (pointer skill)

Pointer skill — the implementation is **not** stored here. The `name` above is the stable local contract; the body lives upstream and is fetched/installed from source so consumers always get the latest version.

- **Canonical source:** https://github.com/JuliusBrussee/caveman/blob/main/skills/caveman/SKILL.md
- **Raw SKILL.md:** https://raw.githubusercontent.com/JuliusBrussee/caveman/main/skills/caveman/SKILL.md
- **What it does:** Strips filler and uses terse fragment-based output to cut tokens while keeping technical precision; multiple intensity and language variants.
- **License:** see the JuliusBrussee/caveman repo LICENSE.

## Installing this skill

caveman is a full plugin — hooks, a session flag for auto-activation, a statusline token-savings badge, and slash commands. Copying this `SKILL.md` alone will **not** work. Run the upstream installer, which detects your agents and configures each:

- **macOS / Linux / WSL / Git Bash:** `curl -fsSL https://raw.githubusercontent.com/JuliusBrussee/caveman/main/install.sh | bash`
- **Windows (PowerShell 5.1+):** `irm https://raw.githubusercontent.com/JuliusBrussee/caveman/main/install.ps1 | iex`

Auto-activates in Claude Code, Codex, and Gemini; installs always-on rule files for Cursor, Windsurf, Cline, and Copilot. Full agent list: upstream INSTALL.md.

**Security:** `curl … | bash` runs remote code — review `install.sh` before piping it to a shell. Do not inline the upstream body here.
