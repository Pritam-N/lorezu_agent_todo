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

## Usage

```bash
todo add "Fix Celery retries" --p high --due 2025-12-20 --tag backend --tag infra
todo ls --pending --sort priority
todo pick
todo config
```

## DB path precedence

1) `--db /path/to/todos.json`
2) env var `TODO_DB=/path/to/todos.json`
3) config written by `todo init`
4) default: `~/Documents/todo-cli/todos.json` (fallback: `~/.todo-cli/todos.json`)
