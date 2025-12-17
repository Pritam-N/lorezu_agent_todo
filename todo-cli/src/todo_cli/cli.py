from __future__ import annotations
import argparse, datetime as dt
from pathlib import Path
from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.columns import Columns
from rich import box
from .model import Task
from .storage import FileLock, load_tasks, save_tasks, sort_tasks
from .ui import pick_tasks_to_done
from .render import render_tasks_table, render_tasks_plain
from .housekeeping import resolve_db_path, init_config
from .config import load_config
from .paths import config_path

console = Console()


class RichHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom help formatter that uses Rich for beautiful output"""

    def _format_action_invocation(self, action):
        """Format action invocation with Rich styling"""
        if not action.option_strings:
            (metavar,) = self._metavar_formatter(action, action.dest)(1)
            return f"[bold cyan]{metavar}[/bold cyan]"
        default = action.option_strings[0]
        if action.nargs != 0:
            args_string = self._format_args(action, action.dest)
            args_string = f" {args_string}" if args_string else ""
            return f"[bold yellow]{default}[/bold yellow]{args_string}"
        return f"[bold yellow]{default}[/bold yellow]"

    def _format_action(self, action):
        """Format action with Rich styling"""
        # Get the help string
        help_text = self._expand_help(action) if action.help else ""

        # Format the action invocation
        parts = []
        if action.option_strings:
            parts.extend(
                [f"[bold yellow]{opt}[/bold yellow]" for opt in action.option_strings]
            )
        if action.metavar or action.dest != argparse.SUPPRESS:
            if action.metavar:
                parts.append(f"[bold cyan]{action.metavar}[/bold cyan]")
            elif action.dest != argparse.SUPPRESS:
                parts.append(f"[bold cyan]{action.dest}[/bold cyan]")

        action_header = " ".join(parts)

        if help_text:
            return f"  {action_header:30}  {help_text}\n"
        return f"  {action_header}\n"


def _print_rich_help(parser: argparse.ArgumentParser, subcommand: str = None) -> None:
    """Print help using Rich formatting"""
    console.print()

    # Title
    title = f"[bold bright_magenta]📋 todo-cli[/bold bright_magenta]"
    if subcommand:
        title += f" [bold cyan]{subcommand}[/bold cyan]"
    console.print(Panel.fit(title, border_style="bright_magenta"))
    console.print()

    # Description
    if parser.description:
        console.print(f"[bold white]{parser.description}[/bold white]")
        console.print()

    # Commands/Arguments table
    if subcommand:
        # Subcommand help - show arguments and options
        positional_args = []
        optional_args = []

        for action in parser._actions:
            # Skip help action and subparsers
            if action.dest == "help" or isinstance(action, argparse._SubParsersAction):
                continue

            # Build option string
            if action.option_strings:
                # Optional argument
                opt_str = ", ".join(
                    [
                        f"[bold yellow]{opt}[/bold yellow]"
                        for opt in action.option_strings
                    ]
                )
                if action.metavar:
                    opt_str += f" [bold cyan]{action.metavar}[/bold cyan]"
                elif (
                    action.nargs
                    and action.nargs != 0
                    and action.dest != argparse.SUPPRESS
                ):
                    opt_str += f" [bold cyan]{action.dest.upper()}[/bold cyan]"

                help_text = action.help or ""
                if action.choices:
                    help_text += f" [dim](choices: {', '.join(action.choices)})[/dim]"

                optional_args.append((opt_str, help_text))
            elif action.dest != argparse.SUPPRESS:
                # Positional argument
                opt_str = f"[bold cyan]{action.metavar or action.dest}[/bold cyan]"
                help_text = action.help or ""
                if action.choices:
                    help_text += f" [dim](choices: {', '.join(action.choices)})[/dim]"
                positional_args.append((opt_str, help_text))

        # Show positional arguments first
        if positional_args:
            console.print("[bold bright_white]Arguments:[/bold bright_white]")
            table = Table(
                show_header=True,
                header_style="bold bright_white",
                box=box.SIMPLE,
                padding=(0, 1),
            )
            table.add_column("Argument", style="bold cyan", width=30)
            table.add_column("Description", style="white")
            for opt_str, help_text in positional_args:
                table.add_row(opt_str, help_text)
            console.print(table)
            console.print()

        # Show optional arguments
        if optional_args:
            console.print("[bold bright_white]Options:[/bold bright_white]")
            table = Table(
                show_header=True,
                header_style="bold bright_white",
                box=box.SIMPLE,
                padding=(0, 1),
            )
            table.add_column("Option", style="bold yellow", width=30)
            table.add_column("Description", style="white")
            for opt_str, help_text in optional_args:
                table.add_row(opt_str, help_text)
            console.print(table)
            console.print()
    else:
        # Main help - show commands
        table = Table(
            show_header=True,
            header_style="bold bright_white",
            box=box.ROUNDED,
            padding=(0, 1),
        )
        table.add_column("Command", style="bold cyan", width=20)
        table.add_column("Description", style="white")

        # Get subcommands
        subparsers = None
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                subparsers = action
                break

        if subparsers:
            for name, subparser in subparsers.choices.items():
                help_text = subparser.description or (
                    subparser.format_help().split("\n")[0]
                    if hasattr(subparser, "format_help")
                    else "No description"
                )
                # Clean up help text
                if help_text.startswith("usage:"):
                    help_text = "No description"
                table.add_row(name, help_text)

        console.print(table)
        console.print()

        # Global options (excluding help and subparsers)
        global_opts = []
        for action in parser._actions:
            if (
                not isinstance(action, argparse._SubParsersAction)
                and action.option_strings
                and action.dest != "help"
            ):
                opt_str = ", ".join(
                    [
                        f"[bold yellow]{opt}[/bold yellow]"
                        for opt in action.option_strings
                    ]
                )
                if action.metavar:
                    opt_str += f" [bold cyan]{action.metavar}[/bold cyan]"
                global_opts.append((opt_str, action.help or ""))

        if global_opts:
            console.print("[bold bright_white]Global Options:[/bold bright_white]")
            table = Table(
                show_header=True,
                header_style="bold bright_white",
                box=box.SIMPLE,
                padding=(0, 1),
            )
            table.add_column("Option", style="bold yellow", width=30)
            table.add_column("Description", style="white")
            for opt_str, help_text in global_opts:
                table.add_row(opt_str, help_text)
            console.print(table)
            console.print()

    # Epilog/Examples
    if parser.epilog:
        console.print(
            Panel(
                parser.epilog.strip(),
                title="[bold]Examples[/bold]",
                border_style="cyan",
            )
        )
        console.print()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def parse_date(s: str) -> str:
    try:
        dt.date.fromisoformat(s)
        return s
    except ValueError:
        console.print()
        console.print(
            Panel(
                f"[bold red]❌ Invalid date format[/bold red]\n\n"
                f"[white]Date: [bold yellow]{s}[/bold yellow]\n"
                f"Expected format: [bold cyan]YYYY-MM-DD[/bold cyan][/white]",
                border_style="red",
            )
        )
        console.print()
        raise SystemExit(1)


def find_task(tasks: List[Task], tid: int) -> Task:
    for t in tasks:
        if t.id == tid:
            return t
    console.print()
    console.print(
        Panel(
            f"[bold red]❌ Task not found[/bold red]\n\n"
            f"[white]No task with ID: [bold yellow]#{tid}[/bold yellow]\n"
            f"Use [bold cyan]todo ls[/bold cyan] to see available tasks.[/white]",
            border_style="red",
        )
    )
    console.print()
    raise SystemExit(1)


def cmd_init(args, _db_path: Path) -> None:
    cfg_p, db_p = init_config(
        db=args.db_path or None, dir_=args.dir or None, force=args.force
    )
    console.print(
        Panel.fit(
            f"[bold green]✨ Initialized todo-cli[/bold green]\n\n"
            f"[cyan]Config:[/cyan] {cfg_p}\n"
            f"[cyan]DB:[/cyan]     {db_p}\n\n"
            f'Next: try [bold]todo add "my task"[/bold] and [bold]todo ls[/bold]',
            title="[bold magenta]📋 todo init[/bold magenta]",
            border_style="green",
        )
    )


def cmd_config(args, db_path: Path) -> None:
    cfg = load_config()
    console.print(
        Panel.fit(
            f"[cyan]Config file:[/cyan]  {config_path()}\n"
            f"[cyan]Configured DB:[/cyan] {cfg.db_path or '[dim](not set)[/dim]'}\n"
            f"[cyan]Resolved DB:[/cyan]   [bold]{db_path}[/bold]\n\n"
            f"[dim]Precedence: --db > TODO_DB env > config > default[/dim]",
            title="[bold magenta]⚙️  todo config[/bold magenta]",
            border_style="cyan",
        )
    )


def cmd_add(args, db_path: Path) -> None:
    with FileLock(db_path.with_suffix(".lock")):
        next_id, tasks = load_tasks(db_path)
        t = Task(
            id=next_id,
            text=args.text.strip(),
            done=False,
            created_at=now_iso(),
            priority=(args.p or "").lower(),
            due=parse_date(args.due) if args.due else "",
            tags=args.tag or [],
        )
        tasks.append(t)
        save_tasks(db_path, next_id + 1, tasks)
    msg = Text()
    msg.append("✅ Added ", style="bold green")
    msg.append(f"#{t.id}", style="bold white")
    msg.append(f": {t.text}", style="white")
    console.print(msg)


def cmd_ls(args, db_path: Path) -> None:
    _, tasks = load_tasks(db_path)
    if args.done:
        tasks = [t for t in tasks if t.done]
    elif args.pending:
        tasks = [t for t in tasks if not t.done]
    if args.tag:
        tasks = [t for t in tasks if args.tag in (t.tags or [])]
    if args.search:
        q = args.search.lower()
        tasks = [t for t in tasks if q in (t.text or "").lower()]
    tasks = sort_tasks(tasks, args.sort)
    if not tasks:
        console.print("[dim]📭 (no tasks)[/dim]")
        return
    title = "Pending" if args.pending else ("Done" if args.done else "All")
    if args.plain:
        render_tasks_plain(tasks)
    else:
        render_tasks_table(tasks, title=title)


def cmd_done(args, db_path: Path) -> None:
    with FileLock(db_path.with_suffix(".lock")):
        next_id, tasks = load_tasks(db_path)
        if args.pick:
            pending = [t for t in tasks if not t.done]
            chosen = pick_tasks_to_done(pending)
            if not chosen:
                console.print("[dim]❌ (cancelled)[/dim]")
                return
            for tid in chosen:
                t = find_task(tasks, tid)
                t.done = True
                t.done_at = now_iso()
            save_tasks(db_path, next_id, tasks)
            msg = Text()
            msg.append("✅ Marked done: ", style="bold green")
            msg.append(", ".join([f"#{x}" for x in chosen]), style="bold white")
            console.print(msg)
            return
        t = find_task(tasks, args.id)
        if args.undo:
            t.done = False
            t.done_at = ""
            msg = Text()
            msg.append("↩️  Undone ", style="bold yellow")
            msg.append(f"#{args.id}", style="bold white")
            console.print(msg)
        else:
            t.done = True
            t.done_at = now_iso()
            msg = Text()
            msg.append("✅ Done ", style="bold green")
            msg.append(f"#{args.id}", style="bold white")
            console.print(msg)
        save_tasks(db_path, next_id, tasks)


def cmd_pick(args, db_path: Path) -> None:
    args.pick = True
    cmd_done(args, db_path)


def cmd_rm(args, db_path: Path) -> None:
    with FileLock(db_path.with_suffix(".lock")):
        next_id, tasks = load_tasks(db_path)
        before = len(tasks)
        tasks = [t for t in tasks if t.id != args.id]
        if len(tasks) == before:
            console.print()
            console.print(
                Panel(
                    f"[bold red]❌ Task not found[/bold red]\n\n"
                    f"[white]No task with ID: [bold yellow]#{args.id}[/bold yellow]\n"
                    f"Use [bold cyan]todo ls[/bold cyan] to see available tasks.[/white]",
                    border_style="red",
                )
            )
            console.print()
            raise SystemExit(1)
        save_tasks(db_path, next_id, tasks)
    msg = Text()
    msg.append("🗑️  Removed ", style="bold red")
    msg.append(f"#{args.id}", style="bold white")
    console.print(msg)


def cmd_edit(args, db_path: Path) -> None:
    with FileLock(db_path.with_suffix(".lock")):
        next_id, tasks = load_tasks(db_path)
        t = find_task(tasks, args.id)
        t.text = args.text.strip()
        save_tasks(db_path, next_id, tasks)
    msg = Text()
    msg.append("✏️  Edited ", style="bold cyan")
    msg.append(f"#{args.id}", style="bold white")
    console.print(msg)


def cmd_pri(args, db_path: Path) -> None:
    p = (args.priority or "").lower()
    if p not in ("low", "med", "high"):
        console.print()
        console.print(
            Panel(
                f"[bold red]❌ Invalid priority[/bold red]\n\n"
                f"[white]Priority: [bold yellow]{args.priority}[/bold yellow]\n"
                f"Must be one of: [bold cyan]low[/bold cyan], [bold cyan]med[/bold cyan], or [bold cyan]high[/bold cyan][/white]",
                border_style="red",
            )
        )
        console.print()
        raise SystemExit(1)
    with FileLock(db_path.with_suffix(".lock")):
        next_id, tasks = load_tasks(db_path)
        t = find_task(tasks, args.id)
        t.priority = p
        save_tasks(db_path, next_id, tasks)
    msg = Text()
    msg.append("🎯 Priority set for ", style="bold cyan")
    msg.append(f"#{args.id}", style="bold white")
    msg.append(f" -> ", style="dim")
    pri_color = "red" if p == "high" else ("yellow" if p == "med" else "blue")
    msg.append(p.upper(), style=f"bold {pri_color}")
    console.print(msg)


def cmd_due(args, db_path: Path) -> None:
    with FileLock(db_path.with_suffix(".lock")):
        next_id, tasks = load_tasks(db_path)
        t = find_task(tasks, args.id)
        if args.date.lower() == "none":
            t.due = ""
            msg = Text()
            msg.append("📅 Cleared due date for ", style="bold yellow")
            msg.append(f"#{args.id}", style="bold white")
            console.print(msg)
        else:
            t.due = parse_date(args.date)
            msg = Text()
            msg.append("📅 Due date set for ", style="bold cyan")
            msg.append(f"#{args.id}", style="bold white")
            msg.append(f" -> {t.due}", style="cyan")
            console.print(msg)
        save_tasks(db_path, next_id, tasks)


def cmd_tag(args, db_path: Path) -> None:
    with FileLock(db_path.with_suffix(".lock")):
        next_id, tasks = load_tasks(db_path)
        t = find_task(tasks, args.id)
        tags = set(t.tags or [])
        if args.action == "add":
            tags.add(args.tag)
            msg = Text()
            msg.append("🏷️  Added tag ", style="bold cyan")
            msg.append(f"#{args.tag}", style="cyan")
            msg.append(f" to #{args.id}", style="white")
            console.print(msg)
        else:
            tags.discard(args.tag)
            msg = Text()
            msg.append("🏷️  Removed tag ", style="bold yellow")
            msg.append(f"#{args.tag}", style="cyan")
            msg.append(f" from #{args.id}", style="white")
            console.print(msg)
        t.tags = sorted(tags)
        save_tasks(db_path, next_id, tasks)


def cmd_clear_done(args, db_path: Path) -> None:
    with FileLock(db_path.with_suffix(".lock")):
        next_id, tasks = load_tasks(db_path)
        before = len(tasks)
        tasks = [t for t in tasks if not t.done]
        save_tasks(db_path, next_id, tasks)
    cleared_count = before - len(tasks)
    msg = Text()
    msg.append("🧹 Cleared ", style="bold yellow")
    msg.append(str(cleared_count), style="bold white")
    msg.append(f" done task{'s' if cleared_count != 1 else ''}", style="white")
    console.print(msg)


def cmd_path(args, db_path: Path) -> None:
    msg = Text()
    msg.append("📁 Database path: ", style="bold cyan")
    msg.append(str(db_path), style="bold white")
    console.print(msg)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="todo",
        description="A tiny local TODO CLI with arrow-key interactive selection and rich table view.",
        epilog="""
Examples:
  # Quick start
  todo add "Fix Celery retries" --p high --due 2025-12-20 --tag backend --tag infra
  todo add "Refactor auth middleware" --p med --tag security
  todo ls --pending --sort priority
  todo pick              # interactive arrow-key selection; marks selected as done
  todo done 1
  todo ls --all

  # Storage override
  todo --db /path/to/todos.json ls
  TODO_DB=/path/to/todos.json todo ls

Interactive Picker Keys:
  ↑ / ↓ : move
  Space : toggle selection
  Enter : confirm
  Esc   : cancel

For more information, see: https://github.com/yourusername/todo-cli
        """,
        formatter_class=RichHelpFormatter,
        add_help=False,  # We'll handle help manually
    )
    p.add_argument(
        "--db", type=str, default="", help="DB JSON path (overrides config/env)"
    )
    p.add_argument(
        "--help",
        "-h",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit",
    )
    sub = p.add_subparsers(
        dest="cmd", required=True, title="commands", metavar="COMMAND"
    )

    sp = sub.add_parser(
        "init",
        help="Initialize config and DB location",
        description="Initialize the todo-cli configuration and database location.",
        epilog="""
Examples:
  # Explicit DB file path
  todo init --db-path ~/Documents/mytodos/todos.json

  # Or just a directory (DB becomes DIR/todos.json)
  todo init --dir ~/Documents/mytodos

  # Overwrite existing config
  todo init --dir ~/Documents/mytodos --force
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument(
        "--db-path", type=str, default="", help="DB JSON file path to store todos"
    )
    sp.add_argument(
        "--dir",
        type=str,
        default="",
        help="Directory to create/use (DB file will be DIR/todos.json)",
    )
    sp.add_argument("--force", action="store_true", help="Overwrite existing config")
    sp.set_defaults(fn=cmd_init)

    sp = sub.add_parser(
        "config",
        help="Show config and resolved DB path",
        description="Display configuration file location and resolved database path.",
        epilog="""
Examples:
  todo config

The resolved DB path follows this precedence:
  1. --db flag
  2. TODO_DB environment variable
  3. Config file setting
  4. Default: ~/Documents/todo-cli/todos.json
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.set_defaults(fn=cmd_config)

    sp = sub.add_parser(
        "add",
        help="Add a new task",
        description="Add a new task to your todo list.",
        epilog="""
Examples:
  todo add "Fix Celery retries"
  todo add "Refactor auth middleware" --p high
  todo add "Update docs" --p med --due 2025-12-20
  todo add "Deploy to prod" --p high --due 2025-12-15 --tag backend --tag infra
  todo add "Code review" --tag security --tag urgent

Priority values: low, med, high
Date format: YYYY-MM-DD (e.g., 2025-12-20)
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument("text", type=str, help="Task description")
    sp.add_argument(
        "--p",
        type=str,
        default="",
        metavar="PRIORITY",
        help="Priority: low, med, or high",
    )
    sp.add_argument(
        "--due",
        type=str,
        default="",
        metavar="DATE",
        help="Due date in YYYY-MM-DD format",
    )
    sp.add_argument(
        "--tag",
        action="append",
        default=[],
        metavar="TAG",
        help="Add a tag (can be used multiple times)",
    )
    sp.set_defaults(fn=cmd_add)

    sp = sub.add_parser(
        "ls",
        help="List tasks (table by default)",
        description="List tasks in a beautiful table format. Shows pending tasks by default.",
        epilog="""
Examples:
  todo ls                    # Show pending tasks
  todo ls --all              # Show all tasks
  todo ls --done             # Show only completed tasks
  todo ls --pending          # Show only pending tasks
  todo ls --tag backend      # Filter by tag
  todo ls --search "auth"    # Search in task text
  todo ls --sort priority    # Sort by priority
  todo ls --sort due         # Sort by due date
  todo ls --sort created     # Sort by creation date (default)
  todo ls --plain            # Plain text output (no table)

Sort options: created, due, priority
        """,
        formatter_class=RichHelpFormatter,
    )
    g = sp.add_mutually_exclusive_group()
    g.add_argument(
        "--all", action="store_true", help="Show all tasks (done and pending)"
    )
    g.add_argument("--done", action="store_true", help="Show only completed tasks")
    g.add_argument(
        "--pending", action="store_true", help="Show only pending tasks (default)"
    )
    sp.add_argument(
        "--tag", type=str, default="", metavar="TAG", help="Filter tasks by tag"
    )
    sp.add_argument(
        "--search",
        type=str,
        default="",
        metavar="TEXT",
        help="Search for text in task descriptions",
    )
    sp.add_argument(
        "--sort",
        type=str,
        default="created",
        choices=["created", "due", "priority"],
        help="Sort order (default: created)",
    )
    sp.add_argument(
        "--plain",
        action="store_true",
        help="Output in plain text format instead of table",
    )
    sp.set_defaults(fn=cmd_ls)

    sp = sub.add_parser(
        "done",
        help="Mark task(s) as done or undone",
        description="Mark a task as done by ID, or use interactive picker to select multiple tasks.",
        epilog="""
Examples:
  todo done 1                # Mark task #1 as done
  todo done 1 --undo         # Mark task #1 as undone
  todo done --pick           # Interactive picker to mark multiple tasks

Interactive Picker Keys:
  ↑ / ↓ : move
  Space : toggle selection
  Enter : confirm
  Esc   : cancel
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument(
        "id",
        type=int,
        nargs="?",
        default=None,
        metavar="ID",
        help="Task ID to mark as done",
    )
    sp.add_argument("--undo", action="store_true", help="Mark task as undone instead")
    sp.add_argument(
        "--pick", action="store_true", help="Use interactive picker to select tasks"
    )
    sp.set_defaults(fn=cmd_done)

    sp = sub.add_parser(
        "pick",
        help="Interactive picker to mark tasks as done",
        description="Open an interactive picker dialog to select and mark multiple tasks as done.",
        epilog="""
Examples:
  todo pick

Interactive Picker Keys:
  ↑ / ↓ : move
  Space : toggle selection
  Enter : confirm
  Esc   : cancel

This is equivalent to: todo done --pick
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.set_defaults(fn=cmd_pick)

    sp = sub.add_parser(
        "rm",
        help="Remove a task",
        description="Permanently delete a task from your todo list.",
        epilog="""
Examples:
  todo rm 1                 # Remove task #1
  todo rm 5                 # Remove task #5

Note: This permanently deletes the task. Use 'todo done' to mark as done instead.
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument("id", type=int, metavar="ID", help="Task ID to remove")
    sp.set_defaults(fn=cmd_rm)

    sp = sub.add_parser(
        "edit",
        help="Edit task description",
        description="Update the text description of a task.",
        epilog="""
Examples:
  todo edit 1 "Fix Celery retries and add logging"
  todo edit 3 "Updated: Refactor auth middleware"
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument("id", type=int, metavar="ID", help="Task ID to edit")
    sp.add_argument("text", type=str, metavar="TEXT", help="New task description")
    sp.set_defaults(fn=cmd_edit)

    sp = sub.add_parser(
        "pri",
        help="Set task priority",
        description="Set or update the priority level of a task.",
        epilog="""
Examples:
  todo pri 1 high           # Set task #1 to high priority
  todo pri 2 med            # Set task #2 to medium priority
  todo pri 3 low            # Set task #3 to low priority

Priority values: low, med, high
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument("id", type=int, metavar="ID", help="Task ID")
    sp.add_argument(
        "priority",
        type=str,
        choices=["low", "med", "high"],
        metavar="PRIORITY",
        help="Priority level: low, med, or high",
    )
    sp.set_defaults(fn=cmd_pri)

    sp = sub.add_parser(
        "due",
        help="Set or clear due date",
        description="Set or clear the due date for a task.",
        epilog="""
Examples:
  todo due 1 2025-12-20     # Set due date for task #1
  todo due 2 2025-01-15      # Set due date for task #2
  todo due 3 none            # Clear due date for task #3

Date format: YYYY-MM-DD (e.g., 2025-12-20)
Use "none" to clear the due date.
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument("id", type=int, metavar="ID", help="Task ID")
    sp.add_argument(
        "date",
        type=str,
        metavar="DATE",
        help="Due date in YYYY-MM-DD format, or 'none' to clear",
    )
    sp.set_defaults(fn=cmd_due)

    sp = sub.add_parser(
        "tag",
        help="Add or remove a tag from a task",
        description="Add or remove tags to organize and filter your tasks.",
        epilog="""
Examples:
  todo tag 1 add backend     # Add 'backend' tag to task #1
  todo tag 1 add infra        # Add 'infra' tag to task #1
  todo tag 2 add security    # Add 'security' tag to task #2
  todo tag 1 del backend      # Remove 'backend' tag from task #1

Use 'todo ls --tag TAG' to filter tasks by tag.
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument("id", type=int, metavar="ID", help="Task ID")
    sp.add_argument(
        "action",
        type=str,
        choices=["add", "del"],
        metavar="ACTION",
        help="Action: 'add' to add tag, 'del' to remove tag",
    )
    sp.add_argument("tag", type=str, metavar="TAG", help="Tag name")
    sp.set_defaults(fn=cmd_tag)

    sp = sub.add_parser(
        "clear-done",
        help="Delete all completed tasks",
        description="Permanently remove all tasks marked as done from your todo list.",
        epilog="""
Examples:
  todo clear-done            # Remove all completed tasks

Warning: This permanently deletes all done tasks. This action cannot be undone.
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.set_defaults(fn=cmd_clear_done)

    sp = sub.add_parser(
        "path",
        help="Print resolved database path",
        description="Display the resolved database file path based on current configuration.",
        epilog="""
Examples:
  todo path                  # Print the resolved DB path

Useful for scripts or to verify which database file is being used.
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.set_defaults(fn=cmd_path)

    return p


def run(argv: List[str]) -> int:
    parser = build_parser()

    # Check for help flags before parsing
    if "--help" in argv or "-h" in argv:
        help_idx = argv.index("--help") if "--help" in argv else argv.index("-h")
        subcommand = None

        # Check if there's a command before --help
        if help_idx > 0:
            potential_cmd = argv[help_idx - 1]
            # Check if it's a valid subcommand
            for action in parser._actions:
                if isinstance(action, argparse._SubParsersAction):
                    if potential_cmd in action.choices:
                        subcommand = potential_cmd
                        break

        # Print appropriate help
        if subcommand:
            for action in parser._actions:
                if isinstance(action, argparse._SubParsersAction):
                    if subcommand in action.choices:
                        _print_rich_help(action.choices[subcommand], subcommand)
                        return 0
        else:
            _print_rich_help(parser)
            return 0

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        # Handle argument errors with Rich
        if e.code == 2:  # argparse error
            console.print()
            console.print(
                Panel(
                    "[bold red]❌ Invalid arguments[/bold red]\n\n"
                    "[white]Use [bold cyan]todo --help[/bold cyan] for usage information.\n"
                    "Or [bold cyan]todo COMMAND --help[/bold cyan] for command-specific help.[/white]",
                    border_style="red",
                )
            )
            console.print()
        raise

    db_path = resolve_db_path(args.db)
    if args.cmd == "done" and not getattr(args, "pick", False) and args.id is None:
        console.print()
        console.print(
            Panel(
                "[bold red]❌ Error[/bold red]\n\n"
                "[white]todo done requires an ID, or use: [bold cyan]todo done --pick[/bold cyan][/white]",
                border_style="red",
            )
        )
        console.print()
        raise SystemExit(1)
    args.fn(args, db_path)
    return 0
