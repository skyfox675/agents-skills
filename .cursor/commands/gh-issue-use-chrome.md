# /gh-issue-use-chrome — file a groomed GitHub issue, browser repro pinned to Chrome

Same as `/gh-issue-use-browser`, except the browser deep-dive uses the **Chrome (`claude-in-chrome`) MCP specifically** — best when the repro needs your real signed-in Chrome session (your cookies, your data). Run the **browser-diagnosis** skill on the Chrome MCP; if it is not connected, stop and say so, or use `/gh-issue-use-browser` to auto-pick another engine. Everything else — argument parsing, the filing flow, the ground rules, and the evidence captured — follows `/gh-issue-use-browser`.
