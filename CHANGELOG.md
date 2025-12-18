# Changelog

All notable changes for this repository are documented here.

This repo contains two deliverables:
- **CLI** (`todo-cli/`) — Python package `todo-cli` (command: `todo`)
- **VSCode/Cursor Extension** (`todo-cli-vscode-extension/`) — extension `todo-cli-status`

## [0.1.2] - 2025-12-18

This release corresponds to **extension version 0.1.2** (`todo-cli-vscode-extension/package.json`), plus a large set of CLI + shared repo improvements that ship together in this repo snapshot.

### Added (CLI)

- **`todo stats`** dashboard with `--json` output for scripting.
- **Smart due-date UX** in task lists:
  - Badges like `OVERDUE`, `TODAY`, `IN Nd`
  - `--sort due` now sorts **overdue first**, then upcoming, then no-due.
- **Consistent priority badges** with icons (`🔴 HIGH`, `🟡 MED`, `🔵 LOW`) in table output.
- **Safer completed-task cleanup**:
  - `todo clear-done` now **archives** completed tasks to `todos-archieved.json` by default.
  - `todo clear-done --force` performs permanent deletion.
  - `todo archive done` to explicitly archive done tasks.
- **Backups & recovery**
  - Rotating backups (`todos.json.1 .. todos.json.5`) on writes.
  - `todo doctor` / `todo doctor --fix` / `todo doctor --fix --restore`.
- **Shell completion generation**
  - `todo completion bash|zsh|fish`.
- **Fast capture commands**
  - `todo qa "text"` quick add.
  - `todo today "text"` quick add with due=today.
- **DB migration command**
  - `todo migrate`.

### Changed (CLI)

- `todo done` with **no ID** now defaults to the interactive picker (more ergonomic).
  - `todo done --undo` requires an ID.
- Config precedence and DB path resolution hardened:
  - If config file contains a **relative** `db_path`, it is now resolved **relative to the config directory**.

### Added (Extension)

- **Quick Pick actions** for pending tasks:
  - `Enter` toggles done
  - type `e` edit, `d` delete, `p` priority, `t` add tag
- **Explorer Tree View** (“Todos”) grouped by:
  - Priority buckets
  - Due buckets (Overdue/Today/Soon/Upcoming/None)
  - Tags
- **File watcher refresh**:
  - Refreshes immediately on DB file changes (polling remains as fallback).
- **Multi-root workspace support**:
  - `Todo CLI: Select Workspace Folder` to pick which folder’s DB setting is active.
- **Add from editor**:
  - `Todo CLI: Add Todo From Editor` (uses selection/line + file hint).
- **Safer onboarding**:
  - Auto-creates a default DB JSON on first activation.
  - `Todo CLI: Initialize Database` to create/reset DB on-demand.
- **Improved error UX**:
  - Missing/corrupt DB prompts with actions like Fix Path / Initialize / Open DB / Show Path.

### Changed (Extension)

- Database path resolution now explicitly matches the documented precedence:
  - Workspace-folder setting → global setting → `TODO_DB` → config file → default
  - Config-file relative `db_path` resolves relative to the config directory (matching CLI behavior).
- Extension metadata improvements:
  - Added `publisher`, `homepage`, and `bugs` fields.

### Added (Shared / Repo)

- **`PATH_RESOLUTION.md`**: single source of truth for DB path precedence (CLI + extension).
- **`todo-cli/TROUBLESHOOTING.md`**: consolidated troubleshooting guide.
- **Minimal tests** (`todo-cli/tests/`):
  - parser smoke tests
  - storage/basic behavior tests
  - path resolution tests
  - concurrency smoke test for atomic writes + locking
- **CI** (`.github/workflows/ci.yml`):
  - CLI tests + wheel build
  - extension compile + VSIX packaging

### Fixed

- Extension now properly handles DB config files that store a **relative** `db_path` (common in local setups).

### Notes / Breaking-ish behavior changes

- `todo clear-done` is now **archive-first**; use `--force` to permanently delete.
- `todo done` without args opens the picker instead of erroring.

### Known issues / developer notes

- Editor lint warnings like “import rich could not be resolved” may appear if the Python environment isn’t configured in the IDE; runtime works with deps installed.
- Packaging VSIX inside restricted sandboxes may fail due to global node module access; locally use:
  - `npx --yes @vscode/vsce package --allow-missing-repository`

## [0.1.3] - 2025-12-18

### Fixed (Extension)

- Activation crash on some installs: `command 'todo-cli.refresh' already exists`
  - The extension now uses a unique command namespace (`todo-cli-status.*`) to avoid collisions with other extensions or dev-host copies.

## [0.1.4] - 2025-12-18

### Fixed (Extension)

- Activation failure after install: `No view is registered with id: todo-cli-status.todosView`
  - The extension now falls back to the legacy view id (`todo-cli.todosView`) if an older VSIX/manifest is still present.
  - Added best-effort legacy command aliases (`todo-cli.*`) without crashing when conflicts exist.

## [0.1.5] - 2025-12-18

### Added (Extension)

- Quick add from the status-bar task picker:
  - Open todo list → type a new task → press Enter to create it instantly.

### Improved (Extension)

- Quick add UX in the status-bar picker:
  - When you type any normal text, the “Add: …” row is now the active selection, so **Enter adds by default**.
  - To toggle an existing task while typing, arrow onto the task and press Enter.


