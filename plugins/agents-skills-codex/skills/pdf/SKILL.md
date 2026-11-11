---
name: pdf
description: "Use this skill whenever the user wants to do anything with PDF files. This includes reading or extracting text/tables from PDFs, combining or merging multiple PDFs into one, splitting PDFs apart, rotating pages, adding watermarks, creating new PDFs, filling PDF forms, encrypting/decrypting PDFs, extracting images, and OCR on scanned PDFs to make them searchable. If the user mentions a .pdf file or asks to produce one, use this skill."
---

# pdf (pointer skill)

Pointer skill — the implementation is **not** stored here. The `name` above is the stable local contract; the body lives upstream and is fetched/installed from source so consumers always get the latest version.

- **Canonical source:** https://github.com/anthropics/skills/blob/main/skills/pdf/SKILL.md
- **Raw SKILL.md:** https://raw.githubusercontent.com/anthropics/skills/main/skills/pdf/SKILL.md
- **What it does:** Comprehensive PDF manipulation — extract text/tables, merge/split, rotate, watermark, fill forms, encrypt/decrypt, extract images, OCR scanned PDFs, create new PDFs.
- **License:** see the anthropics/skills repo LICENSE.

## Installing this skill

- **Claude Code (recommended):** `/plugin marketplace add anthropics/skills`, then `/plugin install document-skills@anthropic-agent-skills` — this skill ships in the **document-skills** plugin.
- **Claude.ai (paid plans):** already available, no install.
- **Claude API:** upload/enable via the Skills API.
- **Cursor / GitHub Copilot:** copy `skills/pdf/` from anthropics/skills into your skills dir (`.cursor/skills/`, `.github/skills/`, or the shared `.claude/skills/`).

Do not copy the upstream body into this file; that would freeze the version and defeat the pointer.
