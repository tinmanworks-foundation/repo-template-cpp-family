# AGENTS.md

This repository is the source for generating C/C++ template repositories.

## Agent Rules

1. Keep scaffold CLI contract stable unless intentionally versioned.
2. Keep generated outputs doctrine-aligned.
3. Treat setup scripts as cross-platform contracts (`sh`, `ps1`, `cmd`).
4. Validate all model scaffolds before release.
5. Preserve low-friction defaults and explicit error messaging.
