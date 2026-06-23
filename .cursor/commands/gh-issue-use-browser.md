# /gh-issue-use-browser — file a groomed GitHub issue with a live-browser diagnosis

Arguments: the text you type after the command — parsed exactly like `/gh-issue` (see `gh-issue.md` in this commands directory): breadcrumb first, optional `model:`/`effort:` tokens anywhere, the rest is the description. The filing flow — codebase recon, duplicate check, groomed anatomy, labels, report — is `/gh-issue`'s, unchanged. This command adds one phase: a **browser deep-dive** run between recon and drafting. Typing this command IS the operator's consent to act in their authenticated browser session for diagnosis. (Tracking work in Jira instead? Use `/jira-issue-use-browser`.)

## The browser deep-dive

Run the **browser-diagnosis** skill. It reproduces and root-causes the symptom with whichever browser MCP is connected — Chrome (`claude-in-chrome`), Playwright, Cypress, or Chrome DevTools — and if none is available it falls back to operator-run repro steps. The skill owns the protocol: context/tab isolation, careful-user mutation rules, the dialog hazard, token/cookie redaction, the rabbit-hole guard, and the method (reproduce → trace the failing request via a fetch/XHR shim → mock to isolate → record a repro). The Chrome and Playwright tools are pre-approved above; if you run the Cypress or DevTools MCP, allowlist its tools in `.claude/settings.json`.

If the dive is substantial, dispatch it as the **diagnostician** agent (read-only, its own context) running that skill — its deliverable is findings, not code.

## Evidence into the issue

Browser findings go in the evidence section alongside the `file:line` pointers: the failing request/response pair (redacted), console errors with timestamps, the repro steps as a numbered list exactly as performed, screenshots or the recording path, which environment/account the session was signed into, and which browser MCP produced the evidence. Separate "what the client sent" from "what the server returned" — that boundary usually IS the diagnosis. Any leftover test data goes in a "Residue" line.

Everything else — dedupe etiquette, model/effort pins, never-claim-at-filing, the final report — follows `/gh-issue` exactly.
