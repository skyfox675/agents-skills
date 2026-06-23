---
description: "Like /jira-issue-use-browser, but pinned to the Chrome MCP (claude-in-chrome) — use when you want your real signed-in Chrome session for the repro. Example — /jira-issue-use-chrome \"Composer > Save\" saving toasts failure but the record persists"
argument-hint: <breadcrumb> <description of the issue> [model:tier] [effort:level]
agent: agent
---

# /jira-issue-use-chrome — file a groomed Jira issue, browser repro pinned to Chrome

Same as `/jira-issue-use-browser`, except the browser deep-dive uses the **Chrome (`claude-in-chrome`) MCP specifically** — best when the repro needs your real signed-in Chrome session (your cookies, your data). Run the **browser-diagnosis** skill on the Chrome MCP; if it is not connected, stop and say so, or use `/jira-issue-use-browser` to auto-pick another engine. Everything else — argument parsing, the filing flow, the ground rules, and the evidence captured — follows `/jira-issue-use-browser`.
