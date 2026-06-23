---
description: "Like /gh-issue-use-aws-browser (correlated browser + read-only AWS full-stack dive), but the browser phase is pinned to the Cypress MCP. Example — /gh-issue-use-aws-cypress \"file export > Download\" clicking Download 403s on staging effort:max"
argument-hint: <breadcrumb> <description of the issue> [model:tier] [effort:level]
allowed-tools: Bash(gh issue create:*), Bash(gh issue list:*), Bash(gh label list:*), Bash(aws sts get-caller-identity:*), Bash(aws logs tail:*), Bash(aws logs filter-log-events:*), Bash(aws cloudtrail lookup-events:*), mcp__cypress__cypress_navigate, mcp__cypress__cypress_snapshot, mcp__cypress__cypress_screenshot, mcp__cypress__cypress_click, mcp__cypress__cypress_type, mcp__cypress__cypress_evaluate, mcp__cypress__cypress_get_url, mcp__cypress__cypress_wait_for
---

# /gh-issue-use-aws-cypress — correlated full-stack dive, browser pinned to Cypress

Same as `/gh-issue-use-aws-browser` — the correlated full-stack diagnosis (reproduce in the browser, capture the failing request, chase it through the cloud with read-only AWS calls until the fault layer is found) — except the browser phase uses the **Cypress MCP specifically**, for projects standardized on Cypress. Run the **browser-diagnosis** skill on Cypress; if it is not connected, use `/gh-issue-use-aws-browser` to auto-pick another engine. The Cypress MCP tools are pre-approved above — add the server to your MCP config under the key `cypress` (`npx cypress-mcp --project .`, needs Cypress ≥ 12 and `npx playwright install chromium`); capture network with a `cypress_evaluate` fetch shim per the browser-diagnosis skill. The AWS ground rules, the correlation method, the trace table, and everything else follow `/gh-issue-use-aws-browser`.
