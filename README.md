# Todo CLI & VSCode Extension

A powerful, local TODO management system with both a command-line interface and a VSCode/Cursor extension for seamless task tracking.

## 🎯 Overview

**Todo CLI** is a lightweight, local task management tool that stores todos in JSON files. It features a beautiful terminal UI with rich formatting, interactive pickers, and comprehensive task management.

**Todo CLI VSCode Extension** brings your todos directly into your editor with a status bar display, auto-refresh, and quick access to your tasks.

---

## 📦 Components

### 1. Todo CLI (`todo-cli/`)

A Python-based command-line tool for managing todos from any terminal.

### 2. VSCode Extension (`todo-cli-vscode-extension/`)

A TypeScript extension for VSCode/Cursor that displays todo statistics in the status bar.

---

## ✨ Features

### Todo CLI Features

- 🎨 **Beautiful Terminal UI**: Rich table output with color-coded priorities, due dates, and status indicators
- ⌨️ **Interactive Picker**: Arrow-key navigation to mark multiple tasks as done
- 📊 **Statistics Dashboard**: Visual summary panels showing totals, pending, done, high priority, overdue, and due today
- 🏷️ **Tagging System**: Organize tasks with tags for easy filtering
- 📅 **Due Date Management**: Smart date formatting with urgency indicators (overdue, today, soon)
- 🎯 **Priority Levels**: High, medium, and low priority with color coding
- 🔍 **Search & Filter**: Filter by status, tags, or search text
- 📝 **Rich Help System**: Comprehensive help with examples for all commands
- ⚙️ **Flexible Configuration**: Multiple ways to configure database path (CLI args, env vars, config file)

### VSCode Extension Features

- 📊 **Status Bar Display**: Real-time todo statistics in your editor's status bar
- 🔄 **Auto-refresh**: Automatically updates every 5 seconds (configurable)
- 🎨 **Color Coding**: 
  - 🔴 Red background for overdue tasks
  - 🟡 Yellow background for tasks due today or high priority
  - 🟢 Green background when all tasks are done
- 🖱️ **Interactive**: Click status bar to view and interact with tasks
- 📁 **Workspace Support**: Per-project database paths via workspace settings
- ⚙️ **Easy Configuration**: Right-click menu for quick configuration
- ✨ **Auto-initialization**: Automatically creates default database on first use
- 🔧 **Manual Control**: Commands to refresh, configure, and initialize database

---

## 🚀 Quick Start

### Todo CLI Installation

```bash
cd todo-cli
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

### Initialize Todo CLI

```bash
# Explicit DB file path
todo init --db-path ~/Documents/mytodos/todos.json

# Or just a directory (DB becomes DIR/todos.json)
todo init --dir ~/Documents/mytodos
```

### VSCode Extension Installation

1. **Install from VSIX:**
   - Open Cursor/VSCode
   - `Cmd+Shift+P` / `Ctrl+Shift+P` → `Extensions: Install from VSIX...`
   - Select `todo-cli-vscode-extension/todo-cli-status-0.1.1.vsix`

2. **Or install from source:**
   ```bash
   cd todo-cli-vscode-extension
   npm install
   npm run compile
   # Press F5 to run in Extension Development Host
   ```

---

## 📖 Usage Examples

### Todo CLI Commands

```bash
# Add tasks with metadata
todo add "Fix Celery retries" --p high --due 2025-12-20 --tag backend --tag infra
todo add "Refactor auth middleware" --p med --tag security
todo add "Update documentation" --p low

# List tasks
todo ls                    # Show pending tasks (default)
todo ls --all              # Show all tasks
todo ls --done             # Show completed tasks
todo ls --pending --sort priority  # Sort by priority
todo ls --tag backend      # Filter by tag
todo ls --search "auth"    # Search in task text

# Interactive picker
todo pick                  # Arrow-key selection to mark tasks done

# Mark tasks done
todo done 1                # Mark task #1 as done
todo done 1 --undo         # Mark task #1 as undone
todo done --pick           # Interactive picker

# Manage tasks
todo edit 1 "Updated task text"
todo rm 1                  # Remove task
todo pri 1 high            # Set priority
todo due 1 2025-12-25      # Set due date
todo due 1 none            # Clear due date
todo tag 1 add urgent      # Add tag
todo tag 1 del urgent      # Remove tag

# Maintenance
todo clear-done            # Delete all completed tasks
todo config                # Show configuration
todo path                  # Show database path
```

### VSCode Extension Usage

1. **Status Bar**: View todo count at bottom-right of editor
2. **Click Status Bar**: Open quick pick with pending tasks
3. **Right-Click Status Bar**: Access configuration menu
4. **Command Palette**: `Cmd+Shift+P` → `Todo CLI: [Command]`

**Available Commands:**
- `Todo CLI: Refresh Todo Status`
- `Todo CLI: Open Todo List`
- `Todo CLI: Configure Database Path`
- `Todo CLI: Show Current Database Path`
- `Todo CLI: Initialize Database`
- `Todo CLI: Open Settings`

---

## 🎨 UI Features

### Terminal Output (CLI)

The CLI displays tasks in a beautiful table format:

```
📋 TODOs

┌────┬────────┬──────────┬──────────────────────┬──────────────────┬────────────────────────┐
│ ID │ Status │ Priority │ Due Date             │ Tags             │ Task                   │
├────┼────────┼──────────┼──────────────────────┼──────────────────┼────────────────────────┤
│  1 │   ○    │   HIGH   │ ⚠️  2025-12-15 (2d) │ #backend #infra  │ Fix Celery retries    │
│  2 │   ○    │   MED    │ 📅 2025-12-20       │ #security        │ Refactor auth         │
│  3 │   ✓    │   LOW    │ —                    │ —                │ Update docs           │
└────┴────────┴──────────┴──────────────────────┴──────────────────┴────────────────────────┘
```

**Statistics Dashboard:**
```
┌────────┐ ┌─────────┐ ┌──────┐ ┌──────────────┐ ┌──────────┐
│   5    │ │    3    │ │  2   │ │      1       │ │    2     │
│ Total  │ │ Pending │ │ Done │ │ High Priority│ │ Overdue  │
└────────┘ └─────────┘ └──────┘ └──────────────┘ └──────────┘
```

### Status Bar (Extension)

- `$(checklist) 5/3` - 5 pending, 3 done
- `$(checklist) 5 $(warning) 2` - 5 pending, 2 high priority
- `$(checklist) 5 $(error) 1` - 5 pending, 1 overdue
- `$(checklist) 5 $(clock) 2` - 5 pending, 2 due today

---

## ⚙️ Configuration

### Database Path Resolution

Both CLI and extension use the same resolution order:

1. **CLI**: `--db` flag
2. **Extension**: Workspace setting (`todo-cli.dbPath` in `.vscode/settings.json`)
3. **Extension**: Global setting (`todo-cli.dbPath` in User Settings)
4. **Both**: Environment variable (`TODO_DB`)
5. **Both**: Config file (`~/.config/todo-cli/config.json`)
6. **Both**: Default (`~/Documents/todo-cli/todos.json` or `~/.todo-cli/todos.json`)

### Extension Settings

Add to VSCode `settings.json`:

```json
{
  "todo-cli.dbPath": "",              // Path to database (empty for default)
  "todo-cli.refreshInterval": 5000,   // Refresh interval in ms
  "todo-cli.showPendingOnly": false   // Show only pending count
}
```

**Workspace vs Global:**
- **Workspace**: Per-project database (`.vscode/settings.json`)
- **Global**: Default for all workspaces (User Settings)

---

## 📁 Project Structure

```
lorezu_agent_todo/
├── todo-cli/                    # Python CLI application
│   │── cli.py                  # Command-line interface
│   │── render.py               # Beautiful table rendering
│   │── storage.py              # Database operations
│   │── model.py                # Task data model
│   └── ...
│   └── pyproject.toml
│
├── todo-cli-vscode-extension/      # VSCode/Cursor extension
│   ├── src/
│   │   └── extension.ts            # Extension main file
│   ├── package.json
│   └── todo-cli-status-0.1.1.vsix # Packaged extension
│
└── README.md
```

---

## 🛠️ Development

### CLI Development

```bash
cd todo-cli
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Extension Development

```bash
cd todo-cli-vscode-extension
npm install
npm run compile
npm run watch  # For development
```

**Package Extension:**
```bash
npm install -g vsce
vsce package
```

---

## 📝 Task Data Format

Tasks are stored in JSON format:

```json
{
  "version": 1,
  "next_id": 3,
  "tasks": [
    {
      "id": 1,
      "text": "Fix Celery retries",
      "done": false,
      "created_at": "2025-12-17T19:31:11+00:00",
      "done_at": "",
      "priority": "high",
      "due": "2025-12-20",
      "tags": ["backend", "infra"]
    }
  ]
}
```

---

## 🎯 Use Cases

### CLI Use Cases

- **Quick task capture**: `todo add "Quick note"`
- **Project management**: Organize tasks by tags and priorities
- **Terminal workflow**: Perfect for developers who live in the terminal
- **Scripting**: Easy to integrate into automation scripts

### Extension Use Cases

- **Visual feedback**: Always see your todo count in the editor
- **Quick access**: Click to view tasks without leaving the editor
- **Project-specific todos**: Different databases per workspace
- **Team collaboration**: Share `.vscode/settings.json` for team todos

---

## 🔧 Advanced Features

### CLI Advanced

- **Custom sorting**: `--sort created|due|priority`
- **Plain output**: `--plain` for scripting
- **File locking**: Safe concurrent access
- **Atomic writes**: Data integrity guaranteed

### Extension Advanced

- **Workspace isolation**: Separate todos per project
- **Auto-refresh**: Configurable update interval
- **Path resolution**: Smart fallback chain
- **Error handling**: Graceful degradation

---

## 📚 Documentation

- **CLI Help**: `todo --help` or `todo COMMAND --help`
- **Extension Setup**: See `todo-cli-vscode-extension/WORKSPACE_SETUP.md`
- **Troubleshooting (extension commands)**: See `todo-cli-vscode-extension/FIND_COMMAND.md`
- **Troubleshooting (CLI + extension)**: See `todo-cli/TROUBLESHOOTING.md`
- **DB path resolution**: See `PATH_RESOLUTION.md`

---

## 🤝 Contributing

Contributions welcome! Both components are open source and MIT licensed.

---

## 📄 License

MIT License - See LICENSE files in respective directories.

---

## 🎉 Quick Links

- **CLI**: `todo-cli/`
- **Extension**: `todo-cli-vscode-extension/`
- **Install Extension**: Use the `.vsix` file in the extension directory
- **CLI Commands**: Run `todo --help` after installation

---

**Happy task managing! 🚀**

