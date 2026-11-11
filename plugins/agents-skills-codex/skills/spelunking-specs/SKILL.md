---
name: spelunking-specs
description: "Deep-dive an unknown or evolving codebase and distil it into living spec documents — spawn agents (one per discovered domain) to ingest the code, infer the conventions, standards, assumptions, and invariants, verify them against real file:line evidence, and write them as numerically-referenced domain specs (1, 1.2, 1.2.3 = domain.subdomain.instance) that live in the repo beside the code and are refined forward over time as more code and issues appear. Each spec captures discovered reality AND the standard it implies, flagging where the code drifts from its own pattern. For convention-, config-, or runtime-wired stacks where relationships are machine-names, hooks, events, and DI bindings rather than direct call sites, recon uses the framework's own introspection tooling and live runtime observation to recover the wiring that static reading misses — automating the manual 'spelunking' people otherwise do by hand. Use whenever you need to map, understand, or onboard to an application you don't fully know, establish or update the repo's spec set, or asked to 'deep-dive', 'recon the codebase', 'figure out the conventions/standards', 'spec out the app', or map a framework-heavy or legacy app you can only understand by spelunking. Domains are auto-discovered (no seed list); git versions the specs, the dotted reference is an address, not a version."
---

# Spelunking: turn an unknown app into living specs

A codebase nobody has fully mapped is a liability — every new agent re-derives the same conventions, repeats the same wrong assumptions, and misses the invariants that aren't written down anywhere. Codebase recon is the deep-dive that fixes that: agents ingest the code, infer how it actually works and the standards it follows, verify each claim against real `file:line` evidence, and write it down as a set of **living specs** that live in the repo beside the code. Those specs are then refined forward — each pass and each new feature sharpens them, so the team's shared understanding compounds instead of evaporating.

These specs document **discovered reality** (what the code does, with evidence) *and* **the standard it implies** (the convention a new contributor should follow), and they **flag drift** — where the code violates its own pattern — as open questions rather than silently normalising it. Domains are **auto-discovered** from the codebase, not seeded from a fixed list.

## The spec set: numeric references, git-versioned

Every spec has a **numeric dotted reference** — `domain.subdomain.instance`, each segment a number:

- `1` — a top-level **domain** (e.g. whatever discovery names #1).
- `1.2` — a **subdomain** within it.
- `1.2.3` — a specific **instance/spec** (the leaf).

The reference is an **address, not a version** — git is the version history, so specs carry no version number and are never duplicated per-revision. Each leaf reference is one Markdown file:

```
<specs-dir>/
  _index.md                       # the registry — number ⇄ domain/title/file/confidence
  1.1.1-session-refresh.spec.md
  1.1.2-session-expiry.spec.md
  1.2.1-oauth-google.spec.md
  2.1.1-user-schema.spec.md
  3.1.1-structured-logging.spec.md
```

The number is canonical; the `-slug` is a human convenience (a slug rename is cosmetic, done with `git mv`). `<specs-dir>` defaults to `specs/` at the repo root (a project may bind it elsewhere).

**Numbers are assigned once and never renumbered.** A reference is a citation target — issues, PRs, other specs, and agents point at `1.2.3` — so renumbering breaks every pointer the way renaming a public API does. New domains/subdomains/instances take the next free number and append; deprecated specs are marked deprecated in frontmatter, not deleted or renumbered.

### `_index.md` — the registry

Numbers are opaque without a key, so `_index.md` is the entry point: a table mapping every reference to its domain, title, file, and confidence, plus a short statement of the repo-wide conventions that span domains. Every recon pass keeps it in sync.

```markdown
| Ref | Domain | Title | File | Confidence |
|-----|--------|-------|------|------------|
| 1   | auth   | Authentication (domain overview) | 1-auth.spec.md | verified |
| 1.1 | auth   | Sessions | 1.1-sessions.spec.md | verified |
| 1.1.1 | auth | Session refresh | 1.1.1-session-refresh.spec.md | draft |
```

### Spec file anatomy

Frontmatter, then the body:

```yaml
---
ref: 1.1.1
domain: auth
title: Session refresh
confidence: draft | verified | stable
last_reviewed: <commit SHA or ISO date>
sources:                              # file:line, an introspection command, or a runtime observation — all reproducible
  - src/auth/session.ts:88-140
  - "cli: <framework debug command> → resolved service/route binding"
  - "runtime: /login render → template suggestion → handler (debug output)"
status: current | drift-flagged | deprecated
related: [1.1.2, 1.2.1]
---
```

Body sections:

1. **Purpose & scope** — what this slice of the app is responsible for, in plain terms.
2. **Discovered behaviour** — how it actually works today, each non-trivial claim anchored to a verified `file:line`.
3. **Conventions & standards** — the pattern a contributor should follow here (naming, error handling, boundaries, the "house style" this domain exhibits). This is the prescriptive half.
4. **Assumptions & invariants** — what the code relies on being true; what must never break.
5. **Interfaces & contracts** — inputs/outputs, events, schemas, the public surface other domains depend on (link their refs).
6. **Drift & open questions** — where the code violates the convention in §3, gaps, suspected dead code, or things recon couldn't confirm. These are candidates for issues (file via the issue-filing skill), never silently "corrected" in the spec.

Confidence is honest: `draft` = inferred, not fully verified; `verified` = claims checked against the code this pass; `stable` = verified and unchanged across passes.

## How a deep-dive runs (spawn agents when possible)

Recon parallelises — spawn agents if the runtime allows it; otherwise do the phases inline.

1. **Map & propose the taxonomy.** One or more survey agents walk the repo (entry points, package/module boundaries, routes, schemas, build config) and propose the domain list with evidence — purely auto-discovered, no seed list. You assign each accepted domain its number and seed `_index.md`. Discovery names the domains from the code's own vocabulary (a `payments/` module → a payments domain), not from a generic checklist.
2. **Author per domain, in parallel.** Dispatch one agent per domain (per the dispatching-subagents skill) to write that domain's subtree of specs — its overview plus the subdomain/instance leaves — each claim carrying `file:line` evidence, each spec marked `draft`. Give each agent the taxonomy so cross-domain references resolve.
3. **Verify, don't trust.** Specs are agent-inferred and can hallucinate a convention that isn't there. Run a verification pass (a fresh agent, or an adversarial reviewer per finding) that re-reads the cited `file:line` for the load-bearing claims; confirmed specs flip `draft → verified`, unconfirmed claims drop to a Drift/open-question line. Do not publish `verified` on an unchecked claim.
4. **Write the index and report.** Update `_index.md`, then report the domain map, the confidence spread, and the top drift/open-questions for the operator.

## When the wiring isn't in the call graph (the "spelunk" problem)

Some stacks don't reveal themselves to static reading. Many frameworks and platforms wire behaviour by **naming convention, hook/event systems, dependency-injection containers, and configuration that lives in a database or config store** — not by call sites you can grep. The relationships are *string machine-names*, not function references: a handler fires because it is named to match a convention, a service binds by its id in a config file, a field or component attaches to an entity by a machine-name stored in the database. Grepping for callers finds almost nothing — so people map these apps by hand: hit a page, scatter logs, guess the custom (often non-conforming) machine-names, follow each relationship to the next, and repeat until they know enough. That is **spelunking**, and it is automatable — it's a recon loop that was missing the right tools.

Three moves, run as a loop, replace the manual spelunk:

1. **Enumerate the dynamic surface with the framework's own introspection.** Most frameworks ship a CLI/console that dumps the wiring the source hides — turning "guess the machine-name" into "list the machine-names": the route table, the service/DI container, registered hooks/events/listeners, entity and field/component definitions, and the exported configuration graph. Use whatever the stack provides — a routes dump, a container or event-dispatcher debug command, a config export, a module/plugin/package list, framework system checks, or an introspection/actuator endpoint. The move is the same everywhere: ask the framework what it wired instead of guessing.
2. **Follow relationships by machine-name, not call graph.** Once introspection hands you the names — hook/handler prefixes, service ids, route names, entity/field/config machine-names — grep those *strings* across the whole tree: source, config, templates, and exported configuration. The machine-name IS the edge; the spec records that name-graph explicitly.
3. **Observe runtime for what only exists at render time.** Drive the page with the browser MCP and turn on the framework's debug/inspection output — template-suggestion comments, render-tree or component dumps, query logs, route/DI debug panels. These name the template or handler that produced a given piece of output, which resolves to its preprocessor/controller, which resolves to the module/package that defined it. Read the DOM/network, then map the rendered output back to the code that produced it. This automates the "go to the page and scatter console.logs" step.

**The loop (automated spelunk):** seed from a page/route/entity → introspect to enumerate its machine-names → resolve each name to its definition and its references → for every still-unknown name, introspect or observe again → stop when the domain's name-graph closes (a pass surfaces no new unknowns). Each leaf spec records that name-graph in Discovered behaviour and cites **both** the `file:line` **and** the introspection command / runtime observation that proved it (see Sources) — so the next agent reproduces the finding instead of re-spelunking.

**No running instance or CLI/DB access?** Recon degrades gracefully: read the source plus any exported/committed configuration files statically, mark the runtime-only claims `draft`, and list in Drift & open questions the exact introspection commands a human (or a later run with access) should run. Say so — a static-only map of a dynamically-wired app is honestly low-confidence, and pretending otherwise is the worst outcome.

## Forward-refining: specs are living, never silently rewritten

Recon is meant to run again — on a schedule, after big merges, or targeted at a changed area. On a re-run (see the `/spelunking-refresh-spec` command):

- **Read the existing specs first**, then diff understanding against the current code. Update in place; git is the changelog, so don't keep version copies.
- **New domain/subdomain/instance** → append the next free number, add to `_index.md`.
- **Code now contradicts a spec** → update the Discovered-behaviour and bump/restate the convention, and note the change is a *refinement*; if the contradiction looks like a regression rather than an intended change, flag it in Drift & open questions instead of rewriting the standard to match possibly-broken code.
- **Confidence transitions** with evidence: re-verified ⇒ `verified`/`stable`; can't re-confirm ⇒ back to `draft` with a note. Stale `last_reviewed` is a signal a spec needs a pass.
- **Never renumber, never delete a reference** — deprecate it (`status: deprecated`, pointer to the successor ref).

## Scope boundary

Recon writes specs (under `<specs-dir>`) and reads code; it does **not** modify application code, file issues automatically (it *recommends* them in Drift sections for the operator to file via the issue-filing skill), or assert issue-level LoE (that is the technical-recon skill). This skill maps the codebase; it is not the issue pipeline. It composes with that pipeline only by being a context source a human or a later recon can read — wiring spec-reads into other skills is deliberately out of scope here.

## Anti-patterns

- **Conventions with no evidence.** A standard asserted without a `file:line` is a guess; publish it as `draft` in Drift, not as `verified`.
- **Renumbering or deleting references.** Breaks every citation; deprecate instead.
- **Normalising drift.** Rewriting the spec to match code that broke its own pattern hides a bug; flag it.
- **One giant spec.** The numeric leaves exist so specs stay small and citable; a 2,000-line `1-auth.spec.md` defeats the addressing.
- **Versioning the filename.** Git versions specs; the number is an address. No `-v2`, no semver in the name.
- **Static-only recon of a convention/DB/runtime-wired app.** Grepping call sites in a framework that wires by convention produces near-empty specs — the wiring is in machine-names, hooks, the DI container, and config. Use the framework's introspection and runtime observation (the spelunk loop), or mark the gaps `draft` and say what you couldn't reach.

## Token discipline: caveman working, humanizer for the specs

Recon spawns many agents over a large codebase — operate in **caveman mode** (load the `caveman` skill) for working output (survey notes, the batch coordination, status, the report), keeping machine-precise content byte-exact (references, `file:line`, frontmatter keys, the `_index.md` table, code blocks).

But the specs are durable documents the whole team and every future agent will read — their prose (purpose, conventions, assumptions, drift narrative) is the product. Draft it naturally and run each spec through the `humanizer` skill before writing, so the spec set reads human-authored, not machine-dumped. Leave `file:line` evidence, references, and frontmatter exactly as captured.
