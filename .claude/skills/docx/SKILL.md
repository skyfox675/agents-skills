---
name: docx
description: "Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx files). Triggers include: any mention of 'Word doc', 'word document', '.docx', or requests to produce professional documents with formatting like tables of contents, headings, page numbers, or letterheads. Also use when extracting or reorganizing content from .docx files, inserting or replacing images in documents, performing find-and-replace in Word files, working with tracked changes or comments, or converting content into a polished Word document. If the user asks for a 'report', 'memo', 'letter', 'template', or similar deliverable as a Word or .docx file, use this skill. Do NOT use for PDFs, spreadsheets, Google Docs, or general coding tasks unrelated to document generation."
---

# docx (pointer skill)

Pointer skill — the implementation is **not** stored here. The `name` above is the stable local contract; the body lives upstream and is fetched/installed from source so consumers always get the latest version.

- **Canonical source:** https://github.com/anthropics/skills/blob/main/skills/docx/SKILL.md
- **Raw SKILL.md:** https://raw.githubusercontent.com/anthropics/skills/main/skills/docx/SKILL.md
- **What it does:** Comprehensive Word (.docx) operations — create with docx-js, edit via XML unpack/repack, extract and analyze content.
- **License:** Proprietary — see upstream LICENSE.txt for complete terms.

## Installing this skill

- **Claude Code (recommended):** `/plugin marketplace add anthropics/skills`, then `/plugin install document-skills@anthropic-agent-skills` — this skill ships in the **document-skills** plugin.
- **Claude.ai (paid plans):** already available, no install.
- **Claude API:** upload/enable via the Skills API.
- **Cursor / GitHub Copilot:** copy `skills/docx/` from anthropics/skills into your skills dir (`.cursor/skills/`, `.github/skills/`, or the shared `.claude/skills/`).

Do not copy the upstream body into this file; that would freeze the version and defeat the pointer.
