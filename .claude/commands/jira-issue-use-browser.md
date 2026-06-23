---
description: "Same as /jira-issue, plus a live-browser deep-dive using whatever browser MCP is connected (Chrome, Playwright, or Cypress): reproduce as the signed-in user, watch network + console, capture the failing request/response, mock to isolate, and record a repro before filing the Jira issue. Example — /jira-issue-use-browser \"Composer > Save\" saving toasts failure but the record persists model:sonnet"
argument-hint: <breadcrumb> <description of the issue> [model:tier] [effort:level]
allowed-tools: mcp__atlassian__createJiraIssue, mcp__atlassian__searchJiraIssuesUsingJql, mcp__atlassian__getJiraIssue, mcp__atlassian__editJiraIssue, mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__read_page, mcp__claude-in-chrome__find, mcp__claude-in-chrome__read_network_requests, mcp__claude-in-chrome__read_console_messages, mcp__claude-in-chrome__javascript_tool, mcp__claude-in-chrome__computer, mcp__claude-in-chrome__gif_creator, mcp__playwright__browser_navigate, mcp__playwright__browser_snapshot, mcp__playwright__browser_network_requests, mcp__playwright__browser_console_messages, mcp__playwright__browser_evaluate, mcp__playwright__browser_take_screenshot, mcp__playwright__browser_click, mcp__playwright__browser_type, mcp__chrome-devtools__navigate_page, mcp__chrome-devtools__list_network_requests, mcp__chrome-devtools__list_console_messages, mcp__chrome-devtools__evaluate_script, mcp__chrome-devtools__take_snapshot
---

# /jira-issue-use-browser — file a groomed Jira issue with a live-browser diagnosis

Arguments: `$ARGUMENTS` — parsed exactly like `/jira-issue` (see `jira-issue.md` in this commands directory): breadcrumb first, optional `model:`/`effort:` tokens anywhere, the rest is the description. The filing flow — codebase recon, duplicate check (JQL), groomed anatomy, fields, report — is `/jira-issue`'s, unchanged. This command adds one phase: a **browser deep-dive** run between recon and drafting. Typing this command IS the operator's consent to act in their authenticated browser session for diagnosis. (Tracking work in GitHub instead? Use `/gh-issue-use-browser`.)

## The browser deep-dive

Run the **browser-diagnosis** skill. It reproduces and root-causes the symptom with whichever browser MCP is connected — Chrome (`claude-in-chrome`), Playwright, Cypress, or Chrome DevTools — and if none is available it falls back to operator-run repro steps. The skill owns the protocol: context/tab isolation, careful-user mutation rules, the dialog hazard, token/cookie redaction, the rabbit-hole guard, and the method (reproduce → trace the failing request via a fetch/XHR shim → mock to isolate → record a repro). The Chrome and Playwright tools are pre-approved above; if you run the Cypress or DevTools MCP, allowlist its tools in `.claude/settings.json`.

If the dive is substantial, dispatch it as the **diagnostician** agent (read-only, its own context) running that skill — its deliverable is findings, not code.

## Evidence into the issue

Browser findings go in the evidence section alongside the `file:line` pointers: the failing request/response pair (redacted), console errors with timestamps, the repro steps as a numbered list exactly as performed, screenshots or the recording path, which environment/account the session was signed into, and which browser MCP produced the evidence. Separate "what the client sent" from "what the server returned" — that boundary usually IS the diagnosis. Any leftover test data goes in a "Residue" line.

Everything else — dedupe etiquette, model/effort pins, never-assign-at-filing, the final report — follows `/jira-issue` exactly.
