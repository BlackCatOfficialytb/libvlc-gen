# Contributing

> Ownership: All projects owned or managed by org user `BlackCatOfficialytb`.

## Table of Contents

- [Humans](#humans)
- [Agents (including OpenClaw/NanoClaw)](#agents-including-openclawnanoclaw)
- [Getting Started & Development Workflow](#getting-started--development-workflow)
- [Coding Guidelines & Quality Checks](#coding-guidelines--quality-checks)
- [Pull Request Standards](#pull-request-standards)

---

## Humans

All contributions allowed: bug fixes, features, docs, refactors, tests.
Open an issue first for breaking changes. Keep PRs small and scoped to one change.

---

## Agents (including OpenClaw/NanoClaw)

### Scope & Permissions

- **Prohibited by default:** Adding, modifying, or removing features, refactors, dependency adds/updates, build/config changes, or large rewrites without explicit prior authorization.
- **Allowed without pre-approval:** Bug fixes, vulnerability patches, typo/docs fixes, and regression tests covering the fix.
- **Conditional approval:** Small feature add/modify *only* with explicit human approval in a linked issue before opening the PR.

### Execution Requirements

Each agent PR must strictly fulfill the following criteria:

1. **Linkage:** Link the relevant bug report, issue, or human approval.
2. **Minimalism:** Keep the diff minimal and strictly scoped to the targeted problem.
3. **Dependencies:** Add zero new dependencies unless explicitly authorized.
4. **Verification:** Include clear, step-by-step verification and reproduction instructions.
5. **Identification:** End the PR body with `🤖🤖🤖` to clearly identify agent origin. (Any commit that are from agent don't have `🤖🤖🤖` at the end will be automatically rejected)

---

## Getting Started & Development Workflow

1. **Environment Setup:** Ensure your local environment matches the target project runtime and dependencies. Do not upgrade core toolchains or configuration files unless requested.
2. **Issue Tracking:** Always reference an existing issue or open a new one before starting work on non-trivial changes.
3. **Branching Strategy:** Create a dedicated, descriptive branch for your fix or feature (e.g., `fix/memory-leak` or `docs/update-readme`).

---

## Coding Guidelines & Quality Checks

Before submitting any code changes, ensure you meet the following baseline requirements:

- **Style Consistency:** Adhere strictly to the existing formatting, naming conventions, and architectural patterns of the repository.
- **Linter & Formatting:** Run project-standard linters and formatters. Zero linter warnings or errors are tolerated.
- **Testing:**
  - All existing unit and integration tests must pass successfully.
  - Write regression or unit tests covering any bug fix or new logic introduced.
- **Performance & Safety:** Avoid introducing blocking operations, memory leaks, or unhandled exceptions.

---

## Pull Request Standards

- **Title Format:** Use a concise, informative title communicating the exact purpose of the change (e.g., `fix: resolve null pointer exception in user auth`).
- **Comprehensive Description:** Explain clearly:
  - **What** was changed.
  - **Why** the change was necessary.
  - **How** it was tested and verified.
- **Redundancy Check:** Check existing PRs to ensure duplicate implementations are avoided.

<!-- ponytail: manual 🤖🤖🤖 check, add CI check when abused -->