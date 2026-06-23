---
description: "Like /jira-issue-use-browser, but pinned to the Cypress MCP — use when your project runs the Cypress MCP for browser automation. Example — /jira-issue-use-cypress \"Composer > Save\" saving toasts failure but the record persists"
argument-hint: <breadcrumb> <description of the issue> [model:tier] [effort:level]
allowed-tools: mcp__atlassian__createJiraIssue, mcp__atlassian__searchJiraIssuesUsingJql, mcp__atlassian__getJiraIssue, mcp__atlassian__editJiraIssue, mcp__cypress__cypress_navigate, mcp__cypress__cypress_snapshot, mcp__cypress__cypress_screenshot, mcp__cypress__cypress_click, mcp__cypress__cypress_type, mcp__cypress__cypress_evaluate, mcp__cypress__cypress_get_url, mcp__cypress__cypress_wait_for
---

# /jira-issue-use-cypress — file a groomed Jira issue, browser repro pinned to Cypress

Same as `/jira-issue-use-browser`, except the browser deep-dive uses the **Cypress MCP specifically** — for projects standardized on Cypress. Run the **browser-diagnosis** skill on the Cypress MCP; if it is not connected, stop and say so, or use `/jira-issue-use-browser` to auto-pick another engine. The Cypress MCP tools are pre-approved above — add the server to your MCP config under the key `cypress` (`npx cypress-mcp --project .`, needs Cypress ≥ 12 and `npx playwright install chromium`); capture network with a `cypress_evaluate` fetch shim per the browser-diagnosis skill. Everything else — argument parsing, the filing flow, the ground rules, and the evidence captured — follows `/jira-issue-use-browser`.
