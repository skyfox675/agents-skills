# /figma-refresh-spec — detect design drift and produce a re-touch list

> Operate in caveman mode (load the `caveman` skill). Keep ids, keys, token deltas, and mapped code paths byte-exact; spec prose through humanizer.

Arguments: the text you type after the command — an optional scope (a page, flow, component set, or id; none = all specs whose source changed or are stalest). A `model:` token pins the tier (default `sonnet`).

The **figma-specs** skill is the protocol; this is its drift pass. Consult it first.

## Steps

1. **Read the existing specs in scope** (from `design-specs/_index.md`). A refresh is a resume — read before changing anything.
2. **Re-pull each via the Figma MCP and diff by stable id**: `get_variable_defs` for token/property values; the code target comes from the spec's repo-owned `code:` map (re-run `scout` if the mapped file has moved). Classify per the figma-specs skill — moved/reorganized, renamed, changed, added, removed, code-moved.
3. **Update specs in place:** for **moves**, update only the `locator` (no code change); for **changes**, record the before→after delta + the mapped code path; append new ids (with a scout-proposed mapping); deprecate removed ones. Never re-key.
4. **Re-sync `_index.md` and report two lists:** "reorganization only — ignore" and "real changes — re-touch" (each delta with its code file). The second list is what the team acts on; `/gh-issue-recon` or `/dispatch` can pick it up to file or fix.

Run any rewritten prose through the `humanizer` skill; ids/keys/deltas stay byte-exact.
