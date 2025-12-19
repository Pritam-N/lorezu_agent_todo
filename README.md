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
- 🐛 **Bug Tracking**: Dedicated bug tracking commands with status, severity, assignee, steps to reproduce, and environment
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

**Archiving file**

- Alongside your active DB, todo-cli keeps an archive file for recoverable deletes:
  - `todos-archieved.json` (same folder as your DB)

### VSCode Extension Installation

1. **Install from VSIX:**
   - Open Cursor/VSCode
   - `Cmd+Shift+P` / `Ctrl+Shift+P` → `Extensions: Install from VSIX...`
   - Select the packaged file: `todo-cli-vscode-extension/todo-cli-status-*.vsix`

2. **Or install from source:**
   ```bash
   cd todo-cli-vscode-extension
   npm install
   npm run compile
   # Press F5 to run in Extension Development Host
   ```

**Packaging VSIX locally (recommended)**

```bash
cd todo-cli-vscode-extension
npx --yes @vscode/vsce package --allow-missing-repository
```

---

## 📖 Usage Examples

### Todo CLI Commands

```bash
# Add tasks with metadata
todo add "Fix Celery retries" --p high --due 2025-12-20 --tag backend --tag infra
todo add "Refactor auth middleware" --p med --tag security
todo add "Update documentation" --p low

# Quick add (defaults: priority=med, due=tomorrow)
todo qa "Follow up with recruiter"

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
todo rm 1                  # Remove task (archived to todos-archieved.json)
todo pri 1 high            # Set priority
todo due 1 2025-12-25      # Set due date
todo due 1 none            # Clear due date
todo tag 1 add urgent      # Add tag
todo tag 1 del urgent      # Remove tag

# Bug Tracking (QA-friendly)
todo bug add "Login button not working" --severity critical --env prod --assignee john
todo bug add "API returns 500" --severity high --status in-progress --steps "1. Open app\n2. Click login\n3. See error"
todo bug list                    # List all bugs
todo bug list --status open      # Filter by status
todo bug list --severity critical # Filter by severity
todo bug list --assignee john     # Filter by assignee
todo bug list --env prod          # Filter by environment
todo bug show 1                   # Show detailed bug info
todo bug status 1 in-progress     # Update bug status
todo bug assign 1 jane            # Assign bug to someone
todo bug severity 1 high          # Set bug severity
todo bug steps 1 "1. Open app\n2. Click button"  # Add steps to reproduce
todo bug env 1 staging            # Set environment

# Maintenance
todo clear-done            # Archive completed tasks to todos-archieved.json (safer)
todo clear-done --force    # Permanently delete completed tasks (dangerous)
todo archive done          # Explicitly archive done tasks
todo doctor --fix --restore  # Validate/repair DB (and restore from backups if needed)
todo config                # Show configuration
todo path                  # Show database path
```

### VSCode Extension Usage

1. **Status Bar**: View todo count at bottom-right of editor
2. **Click Status Bar**: Open quick pick with tasks + search
3. **Right-Click Status Bar**: Access configuration menu
4. **Command Palette**: `Cmd+Shift+P` → `Todo CLI: [Command]`

**Quick Pick rules (important)**

- If your search text matches **0 tasks**: `Enter` creates a new task
- If there are matches: arrow onto a task and `Enter` toggles done
- Type `Add: ...` to force-create immediately (even if there are matches)
- `+` button always adds the typed text
- Actions (prefix with `:`): `:e` edit, `:d` delete (archived), `:p` priority, `:t` tag

**Available Commands:**
- `Todo CLI: Refresh Todo Status`
- `Todo CLI: Open Todo List`
- `Todo CLI: Add Todo From Editor`
- `Todo CLI: Configure Database Path`
- `Todo CLI: Show Current Database Path`
- `Todo CLI: Initialize Database`
- `Todo CLI: Select Workspace Folder`
- `Todo CLI: Open Settings`

---

## 🐛 Bug Tracking

### Overview

Bug tracking extends the standard todo system with specialized fields for QA teams and developers to track issues systematically. Bugs are regular tasks with additional metadata: status, severity, assignee, steps to reproduce, and environment. All bugs are automatically tagged with `#bug` and can be filtered and managed using dedicated bug commands.

**Key Features:**
- **Status tracking**: open, in-progress, fixed, closed
- **Severity levels**: critical, high, medium, low
- **Assignment**: Track who's working on each bug
- **Reproduction steps**: Document how to reproduce issues
- **Environment tracking**: dev, staging, prod, etc.
- **Integration**: Bugs appear in regular task lists and can use all standard task features (priority, due dates, tags)

### Creating Bugs

Use `todo bug add` to create a new bug report. All fields are optional except the description:

```bash
# Basic bug report
todo bug add "Login button not working"

# Complete bug with all fields
todo bug add "API returns 500 error" \
  --severity critical \
  --status open \
  --assignee john \
  --env prod \
  --steps "1. Open app\n2. Click login\n3. See 500 error" \
  --p high \
  --due 2025-12-25 \
  --tag backend

# Quick bug creation for QA
todo bug add "UI glitch on mobile" --severity high --env staging
```

**Options:**
- `--severity`: critical, high, medium, low (default: none)
- `--status`: open, in-progress, fixed, closed (default: open)
- `--assignee`: Person responsible for fixing the bug
- `--env`: Environment where bug occurs (dev, staging, prod, etc.)
- `--steps`: Steps to reproduce the bug (supports newlines with `\n`)
- `--p`: Priority level (low, med, high) - separate from severity
- `--due`: Due date in YYYY-MM-DD format
- `--tag`: Additional tags (can be used multiple times)

**Note:** Bugs automatically receive the `#bug` tag, so they can be filtered with `todo ls --tag bug`.

### Viewing and Filtering Bugs

List all bugs or filter by specific criteria:

```bash
# List all bugs
todo bug list

# Filter by status
todo bug list --status open
todo bug list --status in-progress
todo bug list --status fixed

# Filter by severity
todo bug list --severity critical
todo bug list --severity high

# Filter by assignee
todo bug list --assignee john

# Filter by environment
todo bug list --env prod
todo bug list --env staging

# Combine filters (all must match)
todo bug list --status open --severity critical --env prod
```

**View detailed bug information:**

```bash
# Show complete bug details including steps to reproduce
todo bug show 1
```

This displays a formatted panel with all bug fields, including:
- ID, description, status, severity
- Assignee, environment, priority
- Due date, tags
- Steps to reproduce (if set)
- Creation and completion timestamps

### Managing Bugs

Update bug properties individually as you work on them:

```bash
# Update bug status
todo bug status 1 open              # Mark as open
todo bug status 1 in-progress        # Mark as in progress
todo bug status 1 fixed              # Mark as fixed
todo bug status 1 closed             # Mark as closed

# Assign bug to someone
todo bug assign 1 jane
todo bug assign 1 "John Doe"

# Set or change severity
todo bug severity 1 critical
todo bug severity 1 high
todo bug severity 1 medium
todo bug severity 1 low

# Add or update steps to reproduce
todo bug steps 1 "1. Navigate to login page\n2. Enter credentials\n3. Click submit\n4. Observe error"

# Set environment
todo bug env 1 prod
todo bug env 1 staging
todo bug env 1 dev
```

**Workflow Example:**

```bash
# QA finds a bug
todo bug add "Button not clickable" --severity high --env staging --assignee dev-team

# Developer picks it up
todo bug assign 1 alice
todo bug status 1 in-progress

# Developer fixes it
todo bug status 1 fixed
todo bug env 1 prod  # Move to prod for verification

# QA verifies fix
todo bug status 1 closed
```

### Integration with Regular Tasks

Bugs are fully integrated with the regular task system:

- **Appear in task lists**: Use `todo ls` to see all tasks including bugs
- **Standard task commands work**: `todo edit`, `todo pri`, `todo due`, `todo tag` all work on bugs
- **Filter by bug tag**: `todo ls --tag bug` shows only bugs
- **Archive with tasks**: `todo clear-done` and `todo archive` include bugs
- **Statistics**: Bugs are included in `todo stats` output

**Example:**

```bash
# View all tasks (including bugs)
todo ls --all

# View only bugs using tag filter
todo ls --tag bug

# Edit bug description like any task
todo edit 1 "Updated: Login button not working on mobile Safari"

# Set priority and due date
todo pri 1 high
todo due 1 2025-12-25
```

### Best Practices for QA Teams

1. **Consistent Severity Levels**
   - Use `critical` for production blockers
   - Use `high` for major functionality issues
   - Use `medium` for minor issues or edge cases
   - Use `low` for cosmetic issues

2. **Detailed Steps to Reproduce**
   - Always include steps when creating bugs
   - Use numbered steps with `\n` for line breaks
   - Include expected vs. actual behavior

3. **Environment Tracking**
   - Always specify the environment where the bug was found
   - Update environment when moving bugs through environments

4. **Status Workflow**
   - Start with `open` when creating bugs
   - Move to `in-progress` when work begins
   - Mark as `fixed` when code is ready for testing
   - Mark as `closed` after verification

5. **Assignment**
   - Assign bugs immediately when creating them
   - Reassign when priorities change

6. **Regular Cleanup**
   - Use `todo bug list --status closed` to review closed bugs
   - Archive old closed bugs with `todo archive done`

**Example QA Workflow:**

```bash
# 1. Find bug during testing
todo bug add "Payment fails on Safari" \
  --severity critical \
  --env staging \
  --assignee backend-team \
  --steps "1. Go to checkout\n2. Select payment method\n3. Click pay\n4. See error: 'Payment failed'"

# 2. Check open critical bugs
todo bug list --status open --severity critical

# 3. After fix, verify in prod
todo bug status 5 fixed
todo bug env 5 prod

# 4. Verify fix and close
todo bug status 5 closed
```

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

**Bug Tracking Table:**
```
🐛 Bugs

┌────┬──────────────┬──────────┬───────────┬──────────┬──────────┬────────────────────────┐
│ ID │ Status       │ Severity │ Assignee   │ Env       │ Priority │ Bug Description        │
├────┼──────────────┼──────────┼───────────┼──────────┼──────────┼────────────────────────┤
│  1 │ OPEN         │ CRITICAL │ john       │ prod      │ HIGH     │ Login button not work  │
│  2 │ IN-PROGRESS  │ HIGH     │ jane       │ staging   │ MED      │ API returns 500       │
│  3 │ FIXED        │ MEDIUM   │ —          │ dev       │ LOW      │ UI glitch             │
└────┴──────────────┴──────────┴───────────┴──────────┴──────────┴────────────────────────┘
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
│   └── todo-cli-status-*.vsix     # Packaged extension
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

