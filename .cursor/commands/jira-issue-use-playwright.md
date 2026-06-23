# /jira-issue-use-playwright — file a groomed Jira issue, browser repro pinned to Playwright

Same as `/jira-issue-use-browser`, except the browser deep-dive uses the **Playwright MCP specifically** — a clean automated browser, best for a public page or one you can reach with test credentials. Run the **browser-diagnosis** skill on the Playwright MCP; if it is not connected, stop and say so, or use `/jira-issue-use-browser` to auto-pick another engine. Everything else — argument parsing, the filing flow, the ground rules, and the evidence captured — follows `/jira-issue-use-browser`.
