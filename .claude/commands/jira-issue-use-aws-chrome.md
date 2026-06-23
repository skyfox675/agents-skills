---
description: "Like /jira-issue-use-aws-browser (correlated browser + read-only AWS full-stack dive), but the browser phase is pinned to the Chrome MCP (claude-in-chrome). Example — /jira-issue-use-aws-chrome \"file export > Download\" clicking Download 403s on staging effort:max"
argument-hint: <breadcrumb> <description of the issue> [model:tier] [effort:level]
allowed-tools: mcp__atlassian__createJiraIssue, mcp__atlassian__searchJiraIssuesUsingJql, mcp__atlassian__getJiraIssue, mcp__atlassian__editJiraIssue, Bash(aws sts get-caller-identity:*), Bash(aws logs tail:*), Bash(aws logs filter-log-events:*), Bash(aws cloudtrail lookup-events:*), mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__read_page, mcp__claude-in-chrome__find, mcp__claude-in-chrome__read_network_requests, mcp__claude-in-chrome__read_console_messages, mcp__claude-in-chrome__javascript_tool, mcp__claude-in-chrome__computer, mcp__claude-in-chrome__gif_creator
---

# /jira-issue-use-aws-chrome — correlated full-stack dive, browser pinned to Chrome

Same as `/jira-issue-use-aws-browser` — the correlated full-stack diagnosis (reproduce in the browser, capture the failing request, chase it through the cloud with read-only AWS calls until the fault layer is found) — except the browser phase uses the **Chrome (`claude-in-chrome`) MCP specifically**, best when the repro needs your real signed-in session. Run the **browser-diagnosis** skill on Chrome; if it is not connected, use `/jira-issue-use-aws-browser` to auto-pick another engine. The AWS ground rules, the correlation method, the trace table, and everything else follow `/jira-issue-use-aws-browser`.
