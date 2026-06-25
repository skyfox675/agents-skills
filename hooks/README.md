# Git hook templates

Portable, dependency-free git hooks and matching CI workflows you can drop into
any repo. No husky, no Node, no config files required — the local hooks are
plain POSIX `sh`, and every external tool they call is optional and skips
loudly when it isn't installed. They get stricter as you install tools, and
work in a bare repo without any.

## What's here

| File | Kind | Does |
|---|---|---|
| `commit-msg` | local hook | Enforces Conventional Commits format on the message (dependency-free; replaces a commitlint hook). |
| `pre-commit` | local hook | Scans staged changes for secrets with **gitleaks** (skip-if-absent). |
| `pre-push` | local hook | The lint gate: project gate (`make check` if present) + Claude skill/agent/command frontmatter + **markdownlint** + **actionlint** (all skip-if-absent). |
| `install.sh` | installer | Points `core.hooksPath` at this directory. |
| `pr-title.yml` | CI template | Server-side PR-title Conventional-Commits check; mirrors `commit-msg`. |
| `gitleaks.yml` | CI template | Server-side secret scan on every push/PR; complements the local `pre-commit`. |

The `pre-push` lint gate is the portable stand-in for a monorepo `turbo run
lint`: a content repo has no build toolchain, so it lints what a content repo
actually has — Markdown, workflow YAML, and Claude artifact frontmatter — and
leaves a clearly-marked spot to plug in your project's own command.

## Install

Local hooks (run from inside the target repo):

```sh
sh hooks/install.sh        # sets core.hooksPath -> hooks/
```

Uninstall with `git config --unset core.hooksPath`.

> Already using husky or another manager that owns `core.hooksPath`? Don't run
> the installer. Instead call these from your existing hooks, e.g. add
> `sh "$(git rev-parse --show-toplevel)/hooks/pre-commit"` to `.husky/pre-commit`.

CI workflows (copy the templates you want and commit them):

```sh
cp hooks/pr-title.yml  .github/workflows/pr-title.yml
cp hooks/gitleaks.yml  .github/workflows/gitleaks.yml
```

Optional local tools — the hooks skip these when absent:

```sh
brew install gitleaks actionlint
npm  i -g markdownlint-cli2
```

## Customizing

- **Commit / PR-title types** — edit the `types` list in `commit-msg` and keep
  `pr-title.yml`'s `types` identical so local and server checks agree.
- **Project gate** — in `pre-push`, replace the `make check` block with your
  real lint/test command (`npm run lint`, `pnpm turbo run lint`, `cargo
  clippy`, `go vet ./...`, …).
- **Secret false positives** — add a narrowly-scoped rule to a `.gitleaks.toml`
  at the repo root; don't disable the hook.
- **Action versions** — `pr-title.yml` and `gitleaks.yml` pin third-party
  actions to commit SHAs for supply-chain hygiene; bump deliberately.

## Bypassing

Every local hook honors `git commit --no-verify` / `git push --no-verify`.
Treat it as an emergency-only escape and fix the underlying issue instead —
a bypassed check is invisible debt someone discovers later without context.
