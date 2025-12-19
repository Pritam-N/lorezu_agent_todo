# todo-cli

A tiny local TODO CLI you can use from any IDE terminal.

- Stores tasks in a JSON file.
- **Arrow-key interactive picker** to mark tasks done.
- **Rich table output** for clear navigation.
- `todo init` to set DB path + housekeeping.

## Install (editable)

```bash
cd todo-cli
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

## Initialize (recommended)

```bash
# Explicit DB file path
todo init --db-path ~/Documents/mytodos/todos.json

# Or just a directory (DB becomes DIR/todos.json)
todo init --dir ~/Documents/mytodos
```

### Archive file (recoverable deletes)

todo-cli keeps an archive file next to your active DB:

- `todos-archieved.json` (same folder as your DB)

## Usage

```bash
todo add "Fix Celery retries" --p high --due 2025-12-20 --tag backend --tag infra
todo qa "Quick add"             # defaults: priority=med, due=tomorrow
todo ls --pending --sort priority
todo pick
todo config
```

## Bug Tracking

Dedicated commands for QA teams to track bugs with status, severity, assignee, steps to reproduce, and environment:

```bash
# Create a bug
todo bug add "Login button not working" --severity critical --env prod --assignee john

# List bugs with filters
todo bug list --status open
todo bug list --severity critical
todo bug list --assignee john

# Manage bugs
todo bug show 1                  # Show detailed bug info
todo bug status 1 in-progress     # Update status
todo bug assign 1 jane            # Assign to someone
todo bug severity 1 high          # Set severity
todo bug steps 1 "1. Open app\n2. Click button"  # Add steps
todo bug env 1 staging            # Set environment
```

Bugs are regular tasks with additional fields and automatically tagged with `#bug`. See main README.md for complete bug tracking documentation.

## DB path precedence

1) `--db /path/to/todos.json`
2) env var `TODO_DB=/path/to/todos.json`
3) config written by `todo init`
4) default: `~/Documents/todo-cli/todos.json` (fallback: `~/.todo-cli/todos.json`)
