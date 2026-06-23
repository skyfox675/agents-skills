---
name: browser-diagnosis
description: "Reproduce and root-cause a front-end bug in a real browser using whichever browser MCP is connected — Chrome (claude-in-chrome), Playwright, Cypress, or Chrome DevTools — not just one. Drive the page as the signed-in user, watch the network and console, capture the failing request/response, shim/mock to isolate the fault, and record a repro, then hand the evidence to the issue being filed. Use whenever a symptom needs live-browser evidence (the toast says failed but it saved, a column shows zero, a click 404s) and from the /…-use-browser command family (and the engine-pinned /…-use-chrome, /…-use-playwright, /…-use-cypress variants), the /…-use-aws-browser commands, and the diagnostician agent. Picks the available MCP automatically and degrades gracefully when none is connected."
---

# Browser Diagnosis (any browser MCP)

Front-end symptoms often can't be root-caused from code alone — the answer is in the real network traffic, the actual API responses, the console, and the DOM as the signed-in user sees it. This skill captures that evidence with **whatever browser MCP the environment has**, so the workflow isn't tied to one tool. Not everyone can run the Chrome (`claude-in-chrome`) MCP; Playwright and Cypress MCPs are common alternatives, and Chrome DevTools MCP is another.

## Pick the browser MCP (in order), then degrade

1. **`claude-in-chrome`** — best when you need the operator's *real signed-in* Chrome session (their cookies, their data). Works in its own new tab group.
2. **Playwright MCP** — a clean automated browser; great when you can log in with test creds or the page is public.
3. **Cypress MCP** — same idea via a Cypress/Playwright-core runner with ARIA snapshots and network intercept.
4. **Chrome DevTools MCP** — strong for network/console/performance inspection.

Use the first one that's connected. If **none** is available: don't fake it — give the operator the exact repro steps to run and ask them to paste the failing request/response and console output, or file with code-only evidence and mark the browser-derived claims unverified. Say which.

## Capability map (do the same step on any MCP)

| Step | claude-in-chrome | Playwright MCP | Cypress MCP | Chrome DevTools MCP |
|---|---|---|---|---|
| Isolate a context | `tabs_context_mcp` then a new tab group | a fresh browser context/tab | its own browser instance | `new_page` |
| Navigate | `navigate` | `browser_navigate` | `cypress_navigate` | `navigate_page` |
| Read network | `read_network_requests` | `browser_network_requests` | `cypress_evaluate` (fetch/XHR shim) or `cy.intercept` in a spec | `list_network_requests` |
| Read console | `read_console_messages` | `browser_console_messages` | `cypress_evaluate` (capture console) | `list_console_messages` |
| Run JS / shim fetch | `javascript_tool` | `browser_evaluate` | `cypress_evaluate` | `evaluate_script` |
| DOM snapshot | `read_page` / `find` | `browser_snapshot` | `cypress_snapshot` (ARIA) | `take_snapshot` |
| Click / type | `computer` | `browser_click` / `browser_type` | `cypress_click` / `cypress_type` | `click` / `fill` |
| Screenshot | `gif_creator` / `computer` | `browser_take_screenshot` | `cypress_screenshot` | `take_screenshot` |

### MCP setup (out of the box)

- **Chrome** — the `claude-in-chrome` extension; tools `mcp__claude-in-chrome__*`.
- **Playwright** — `npx @playwright/mcp@latest`, register under server key `playwright`; tools `mcp__playwright__browser_*`.
- **Cypress** — `npx cypress-mcp --project .` (needs Cypress ≥ 12 in the project and `npx playwright install chromium`), register under server key `cypress`; tools `mcp__cypress__cypress_*`. Cypress has no direct network-reader tool — capture the failing request with a `cypress_evaluate` fetch/XHR shim (the same shim technique, step 2) or `cy.intercept` in a spec.
- **Chrome DevTools** — register the `chrome-devtools-mcp` server under key `chrome-devtools`; tools `mcp__chrome-devtools__*`.

These are the prefixes the bundled commands pre-approve. If your server uses a different key, allowlist its tools in `.claude/settings.json`. Drop the servers you want into your project's `.mcp.json` (`cypress-mcp`'s `--project` points at the app under test, which must have Cypress installed):

```json
{
  "mcpServers": {
    "playwright": { "command": "npx", "args": ["@playwright/mcp@latest"] },
    "cypress":    { "command": "npx", "args": ["cypress-mcp", "--project", "."] },
    "chrome-devtools": { "command": "npx", "args": ["chrome-devtools-mcp@latest"] }
  }
}
```

## Ground rules (every MCP)

- **Isolate.** Work in a fresh context/tab group, never the operator's existing tabs. With `claude-in-chrome`, call `tabs_context_mcp` first and never reuse tab IDs across sessions; with Playwright/Cypress, use a fresh context. One agent, one context — that's what keeps concurrent diagnostics from colliding.
- **Act like a careful signed-in user.** Navigate, inspect, and read freely. Mutate only to reproduce the symptom, preferably against test/disposable data. Never do irreversible or outward-facing actions (payments, emails/invites to real people, deletes with no undo) — surface those as "needs operator repro." Track every mutation and clean up; if residue can't be cleaned, list it in the issue so it isn't mistaken for organic data.
- **Dialog hazard.** Native `alert`/`confirm`/`prompt` dialogs can freeze some MCP sessions — avoid the elements that trigger them, or pre-dismiss/handle them with the MCP's dialog tool.
- **Redact.** Network captures carry auth headers, cookies, and tokens — strip them from every excerpt. Quote the minimal request/response slice that proves the finding.
- **Rabbit-hole guard.** If the same probe fails 2–3 times (MCP unresponsive, page won't load, element won't match), stop and report what you tried rather than thrashing.

## Method

1. **Reproduce first.** Navigate to the surface and perform the user's steps, watching network and console (filter the console — full dumps drown the signal).
2. **Trace the failing call.** Capture the exact request (method, URL/operation, payload) and response (status, body). A `fetch`/XHR shim via the MCP's JS-eval tool that logs each outbound call is the reliable way to see what the client actually sent — for a GraphQL API log the operation name + variables; for REST the method + path + body. Shims live until reload, so reload to clean up.
3. **Mock to isolate.** Stub a response to test "is it the API or the rendering," inject `DataTransfer` for upload paths, or drive state the UI can't reach. Note which findings came from mocked vs live behaviour.
4. **Record the repro** (screenshot or GIF) when the symptom is visual or sequence-dependent; name the file after the issue topic.

## Evidence the diagnosis hands back

The failing request/response pair (redacted), console errors with timestamps, the repro steps as a numbered list exactly as performed, screenshots or the recording path, the environment/account signed in, and **which browser MCP produced the evidence**. Separate "what the client sent" from "what the server returned" — that boundary is usually the diagnosis itself. Any leftover test data goes in a "Residue" line.

## Token discipline

Working output in caveman (load the `caveman` skill); the evidence excerpts, request/response slices, and repro steps stay byte-exact (they're the proof). Durable prose written into the issue goes through the `humanizer` skill, per the issue-filing skill.
