# AGENTS.md

This repository is the source for generating C/C++ template repositories.

## Agent Rules

1. Keep scaffold CLI contract stable unless intentionally versioned.
2. Keep generated outputs doctrine-aligned.
3. Treat setup scripts as cross-platform contracts (`sh`, `ps1`, `cmd`).
4. Validate all model scaffolds before release.
5. Preserve low-friction defaults and explicit error messaging.
6. For GitHub Project-managed repos, implement only against clear issues; keep issues and commits small and issue-scoped by default (`one issue -> one small commit set`), with documented exceptions for non-diff, discovery-first, or unavoidable architecture-wide work.
7. Do not push directly to protected branches (`master`, `develop`) even with admin credentials or AI automation; use PR flow and release-branch promotion (`release/* -> master`, then `release/* -> develop`).
