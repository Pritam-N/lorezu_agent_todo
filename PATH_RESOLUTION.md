## Database path resolution (single source of truth)

This repo has **two front-ends** that read/write the same JSON DB format:

- **CLI** (`todo-cli/`)
- **VSCode/Cursor extension** (`todo-cli-vscode-extension/`)

The goal is to ensure both resolve the final DB path consistently.

### CLI (`todo`)

Resolution order:

1. `--db /path/to/todos.json`
2. `TODO_DB=/path/to/todos.json` (environment variable)
3. Config file `db_path` (from `todo init`)
4. Default path: `~/Documents/todo-cli/todos.json` (fallback: `~/.todo-cli/todos.json`)

Notes:

- If the config file contains a **relative** `db_path`, it is resolved **relative to the config directory**.

### Extension (Cursor/VSCode)

Resolution order:

1. **Workspace folder** setting: `.vscode/settings.json` → `todo-cli.dbPath` (resource/workspace-folder scoped)
2. **Global** user setting: `todo-cli.dbPath`
3. `TODO_DB=/path/to/todos.json` (environment variable)
4. Config file `db_path`
5. Default path: `~/Documents/todo-cli/todos.json` (fallback: `~/.todo-cli/todos.json`)

Notes:

- Workspace setting is resolved **relative to the workspace folder** if it is a relative path.
- Config file relative `db_path` is resolved **relative to the config directory** (matching CLI behavior).

### Archive file (recoverable deletes)

Both the CLI and extension keep an archive file **next to the resolved DB path**:

- If DB is `.../todos.json` → archive is `.../todos-archieved.json`

This keeps “deleted/archived” tasks in the same place as the active DB when you switch DB locations.


