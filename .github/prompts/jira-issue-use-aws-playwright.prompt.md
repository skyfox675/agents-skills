---
description: "Like /jira-issue-use-aws-browser (correlated browser + read-only AWS full-stack dive), but the browser phase is pinned to the Playwright MCP. Example — /jira-issue-use-aws-playwright \"file export > Download\" clicking Download 403s on staging effort:max"
argument-hint: <breadcrumb> <description of the issue> [model:tier] [effort:level]
agent: agent
---

# /jira-issue-use-aws-playwright — correlated full-stack dive, browser pinned to Playwright

Same as `/jira-issue-use-aws-browser` — the correlated full-stack diagnosis (reproduce in the browser, capture the failing request, chase it through the cloud with read-only AWS calls until the fault layer is found) — except the browser phase uses the **Playwright MCP specifically**, a clean automated browser for a public page or one reachable with test credentials. Run the **browser-diagnosis** skill on Playwright; if it is not connected, use `/jira-issue-use-aws-browser` to auto-pick another engine. The AWS ground rules, the correlation method, the trace table, and everything else follow `/jira-issue-use-aws-browser`.
