# Todo CLI VSCode Extension

A VSCode extension that displays your todo-cli statistics in the status bar.

## Features

- 📊 **Status Bar Display**: Shows pending tasks, completed tasks, high priority items, and overdue tasks
- 🔄 **Auto-refresh**: Automatically updates every 5 seconds (configurable) with **instant file-watch refresh** when DB changes
- 🎨 **Color Coding**: 
  - Red background for overdue tasks
  - Yellow background for tasks due today or high priority
  - Green background when all tasks are done
- 🖱️ **Interactive**: Click the status bar item to view and interact with your tasks
- ⌨️ **Quick Pick actions**: In the todo list picker:
  - Type to search
  - If your text matches **no task**: `Enter` = **create new task**
  - If you type `Add: something`: `Enter` = **create immediately** (even if there are matches)
  - If your text matches existing tasks: arrow onto one and `Enter` = toggle done
  - Or: type a new task and click the `+` button (top-right) = **add it instantly**
  - Actions (prefix with `:` so typing words doesn’t trigger them): `:e` edit, `:d` delete, `:p` priority, `:t` add tag
- 🗃️ **Recoverable deletes**: Deleted tasks are appended to `todos-archieved.json` next to your DB
- ⚡ **Quick add defaults**: Quick-created tasks default to `priority=med` and `due=tomorrow`
- 🌲 **Explorer Tree View**: Browse todos by **Priority / Due / Tag**
- ⚙️ **Configurable**: Set custom database path (workspace or global) and refresh interval
- ✨ **Auto-initialization**: Automatically creates default database file on first use
- 📁 **Workspace Support**: Per-project database paths via workspace settings
- 🧩 **Multi-root workspaces**: Select which folder’s DB settings are active

## Installation

1. Clone or download this extension
2. Open in VSCode
3. Run `npm install`
4. Press `F5` to open a new window with the extension loaded
5. Or package with `vsce package` and install the `.vsix` file

## Configuration

### Quick Setup: Workspace Database Path

**Easiest Method:**
1. Right-click the Todo status bar item (bottom right)
2. Select "Configure Database Path"
3. Choose "Set Workspace Path"
4. Enter path (e.g., `./todos.json`) or browse for file
5. Done! Setting saved to `.vscode/settings.json`

**See WORKSPACE_SETUP.md file for detailed steps.**

### Settings

Add these settings to your VSCode `settings.json`:

```json
{
  "todo-cli.dbPath": "",  // Path to todo database (empty for default)
  "todo-cli.refreshInterval": 5000,  // Refresh interval in ms
  "todo-cli.showPendingOnly": false  // Show only pending count
}
```

**Workspace vs Global:**
- **Workspace setting** (`.vscode/settings.json`): Per-project database
- **Global setting** (User Settings): Default for all workspaces

## Database Path Resolution

The extension uses the same path resolution as the todo-cli:

1. **Workspace setting**: `.vscode/settings.json` → `todo-cli.dbPath` (per-project)
2. **Global setting**: User Settings → `todo-cli.dbPath` (all workspaces)
3. Environment variable: `TODO_DB`
4. Config file: `~/.config/todo-cli/config.json` (or platform equivalent)
5. Default: `~/Documents/todo-cli/todos.json` or `~/.todo-cli/todos.json`

**Workspace settings take precedence over global settings.**

## Commands

- `Todo CLI: Refresh Todo Status` - Manually refresh the status bar
- `Todo CLI: Open Todo List` - Open quick pick with pending tasks
- `Todo CLI: Add Todo From Editor` - Create a todo from selection/current line
- `Todo CLI: Configure Database Path` - Set workspace or global database path
- `Todo CLI: Show Current Database Path` - Display current path and configuration
- `Todo CLI: Initialize Database` - Create/reset the database file
- `Todo CLI: Select Workspace Folder` - Choose active folder in multi-root workspaces
- `Todo CLI: Open Settings` - Open extension settings

**Right-click the status bar item for quick access to all commands.**

## Activation error: "command 'todo-cli.refresh' already exists"

If you previously had another extension (or a dev-host copy) that registered `todo-cli.*` command IDs, VSCode may fail activation with:

- `Todo CLI Extension failed to activate: Error: command 'todo-cli.refresh' already exists`

This extension now uses a unique command namespace (`todo-cli-status.*`) to avoid collisions. If you still see the error:

- Disable/uninstall the other conflicting extension, or
- Reload VSCode/Cursor after removing older VSIX copies.

## Usage

### First Time Setup

1. **Install the extension** - The extension will automatically create a default database file on first activation
2. **Location**: Default database is created at `~/Documents/todo-cli/todos.json` (or `~/.todo-cli/todos.json`)
3. **Customize**: Right-click status bar → "Configure Database Path" to change location

### Daily Usage

1. The status bar will automatically show your todo statistics
2. Click the status bar item to see pending tasks
3. Right-click for context menu options
4. Use the command palette (`Cmd+Shift+P` / `Ctrl+Shift+P`) to access commands

### Initialize Database Manually

If you need to create/reset the database:
- Command Palette → `Todo CLI: Initialize Database`
- Or right-click status bar → "Initialize Database"

## Status Bar Format

- `$(checklist) 5/3` - 5 pending, 3 done
- `$(checklist) 5 $(warning) 2` - 5 pending, 2 high priority
- `$(checklist) 5 $(error) 1` - 5 pending, 1 overdue
- `$(checklist) 5 $(clock) 2` - 5 pending, 2 due today

## Requirements

- VSCode 1.74.0 or higher
- todo-cli installed and configured

## Development

```bash
npm install
npm run compile
npm run watch  # For development
```

## License

MIT

