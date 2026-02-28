# repo-template-cpp-family

C/C++ template family with CMake-only project models and cross-platform dependency bootstrap scripts.

## What This Repository Provides

- One scaffold CLI (`tools/scaffold.py`) for multiple project architectures.
- Models:
  - `lib`
  - `exe`
  - `engine-app`
  - `workspace` (multi-lib + multi-exe)
  - `plugin-shared`
  - `plugin-addon` (runtime loadable)
- Built-in generated setup scripts for dependency doctor/install:
  - `tools/setup/bootstrap.sh`
  - `tools/setup/bootstrap.ps1`
  - `tools/setup/bootstrap.cmd`

## Quickstart

```bash
python3 tools/scaffold.py \
  --model lib \
  --lang cpp \
  --project-name demo_project \
  --output-dir /tmp/demo_project \
  --setup
```

### Setup Modes

- `--setup`: run dependency doctor after scaffold
- `--setup-install`: best-effort install + doctor after scaffold

### Language Scope

`--lang c|cpp` controls primary compiled language and CMake defaults only.
Helper scripts in `tools/` can use any language (for example Python).

## Interface Contract

`tools/scaffold.py` flags:

- `--model {lib,exe,engine-app,workspace,plugin-shared,plugin-addon}`
- `--lang {c,cpp}`
- `--project-name <name>`
- `--output-dir <path>`
- `--engine-linkage {shared,static}`
- `--plugin-prefix <prefix>` (default `addon_`)
- `--plugin-suffix <suffix>` (default `_plugin`)
- `--cmake-preset {native,ninja}` (default `native`)
- `--without-doctrine`
- `--force`
- `--setup`
- `--setup-install`

## Validation

```bash
bash tools/validate-generated.sh
```

This script scaffolds all models and runs doctor + configure/build/test smoke checks.
For offline environments, run `VALIDATE_OFFLINE=1 bash tools/validate-generated.sh`.

## Related

For a simpler single-architecture starter, use `repo-template-cpp-cmake`.
