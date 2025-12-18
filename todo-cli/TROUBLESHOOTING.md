## Troubleshooting

### CLI: `todo` not found

- Ensure you installed the CLI:
  - `cd todo-cli`
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -e .`
- Confirm the entrypoint exists: `todo --help`

### CLI: DB path confusion

The CLI resolves the DB path in this order:

1. `--db /path/to/todos.json`
2. `TODO_DB=/path/to/todos.json`
3. Config file (`todo init`)
4. Default: `~/Documents/todo-cli/todos.json` (fallback: `~/.todo-cli/todos.json`)

To inspect current resolution:
- `todo config`
- `todo path`

### CLI: DB JSON is corrupt / won't load

The CLI keeps rotating backups on every write:

- `todos.json.1`, `todos.json.2`, … up to `todos.json.5`

To validate and repair:

- Validate only: `todo doctor`
- Repair in-place: `todo doctor --fix`
- Restore from backup if JSON is invalid: `todo doctor --fix --restore`

### CLI: `clear-done` feels scary

It’s now safe by default:

- `todo clear-done` archives completed tasks into `archive.json` (same folder as the DB)
- Permanent delete (dangerous): `todo clear-done --force`

You can also explicitly archive:
- `todo archive done`

### Extension: commands don’t appear in Cursor/VSCode

1. Reload window:
   - Command Palette → `Developer: Reload Window`
2. Search commands via:
   - `Todo CLI:` (category prefix)
   - `@ext:todo-cli-status`
3. Verify extension is installed/enabled in Extensions view.

See: `todo-cli-vscode-extension/FIND_COMMAND.md`

### Extension: shows “No database” or “DB error”

- Right-click the status bar item → `Configure Database Path`
- Or Command Palette:
  - `Todo CLI: Configure Database Path`
  - `Todo CLI: Initialize Database`
  - `Todo CLI: Show Current Database Path`

If you have a multi-root workspace:
- Use `Todo CLI: Select Workspace Folder` to choose which folder’s DB path setting is used.

### Extension: DB path differs between CLI and extension

Both share the same base resolution after editor settings:

- Extension: Workspace setting → Global setting → `TODO_DB` → config file → default
- CLI: `--db` → `TODO_DB` → config file → default

See: `PATH_RESOLUTION.md`


