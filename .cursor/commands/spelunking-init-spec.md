# /spelunking-init-spec — map the codebase into living specs

> Operate in caveman mode (load the `caveman` skill) — a deep-dive spawns many agents over a large repo. Keep references, `file:line`, frontmatter, and the `_index.md` table byte-exact; the spec prose is the exception (humanizer — see the spelunking-specs skill).

Arguments: the text you type after the command

Parse them as:

- Optional **paths or domain names** scoping the dive (no args = the whole repo). Use a path/domain to deep-dive just that area.
- Optional `model:<tier>` / `effort:<level>`, anywhere — these pin the **recon agents'** tier (default `sonnet`; `opus` for large or tangled codebases).

Example: `/spelunking-init-spec` (whole app) · `/spelunking-init-spec src/payments billing` (scoped)

The **spelunking-specs** skill is the protocol — the numeric reference scheme (`domain.subdomain.instance`, an address, not a version; git versions the specs), the spec-file anatomy, the auto-discovered taxonomy, the reality+standards+drift content, and the verification bar all come from it. Consult it before starting.

## Steps

1. **Locate the spec set.** Find `<specs-dir>` (default `specs/`). If `_index.md` exists, read it first — a deep-dive resumes and extends the existing set rather than overwriting it (numbers are never reassigned). If absent, start fresh.

2. **Map & propose the taxonomy.** Spawn survey agent(s) to walk entry points, module/package boundaries, routes, schemas, and build config and propose the domain list **auto-discovered from the code's own vocabulary** — no seed list. Assign each accepted domain the next free number and seed `_index.md`. **Detect the stack while mapping:** if behaviour is convention-, config-, or runtime-wired, the survey and authoring agents run the spelunking-specs skill's **spelunk loop** — enumerate machine-names via the framework's introspection CLI, follow them by string across source, config, and templates, and observe the live page (browser MCP + the framework's debug output) — instead of static call-graph reading. Allowlist whatever introspection CLI the stack ships in `.claude/settings.json` (a routes/container/config-debug command, a module/package list) plus the browser MCP; with no running instance or CLI access, recon degrades to static + committed config and marks runtime-only claims `draft`.

3. **Author per domain, in parallel.** Dispatch one agent per domain (per the dispatching-subagents skill, single message), each given the taxonomy so cross-references resolve. Each writes its domain's subtree — overview + subdomain/instance leaves — as `specs/<ref>-<slug>.spec.md`, every non-trivial claim carrying a verified `file:line`, every spec marked `confidence: draft`.

4. **Verify, don't trust.** Run a verification pass (fresh agent / adversarial per claim) that re-reads the cited `file:line` for load-bearing claims. Confirmed specs flip `draft → verified`; unconfirmed claims drop into the spec's Drift & open-questions section. Never publish `verified` on an unchecked claim.

5. **Write the index and report.** Sync `_index.md` (ref ⇄ domain/title/file/confidence + the cross-domain conventions), set each spec's `last_reviewed` to the current commit (`git rev-parse HEAD`), then report: the domain map, the confidence spread, and the top drift/open-questions — the latter are candidates the operator may file as issues (via the issue-filing skill); recon recommends, it does not auto-file or modify application code.

Run each spec's prose through the `humanizer` skill before writing (the specs are durable team docs); keep evidence, references, and frontmatter exact.
