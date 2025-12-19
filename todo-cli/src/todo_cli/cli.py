from __future__ import annotations
import argparse, datetime as dt
import json
from pathlib import Path
from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.columns import Columns
from rich import box
from .model import Task
from .storage import (
    FileLock,
    load_tasks,
    save_tasks,
    sort_tasks,
    restore_latest_backup,
    BACKUP_KEEP_DEFAULT,
    archive_path_for_db,
    append_tasks_to_archive,
    save_db,
    migrate_db_data,
)
from .ui import pick_tasks_to_done
from .render import (
    render_tasks_table,
    render_tasks_plain,
    calculate_statistics,
    render_statistics_dashboard,
)
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

    def _style_epilog_block(epilog: str) -> Text:
        """
        Best-effort styling for epilog/example blocks.

        - Commands: bold cyan
        - Headings (lines ending with ':'): bold magenta
        - Comments (# ...): dim
        - Keybind rows (X : ...): highlight key in yellow
        """
        out = Text()
        s = (epilog or "").strip("\n")
        if not s:
            return out

        for line in s.splitlines():
            raw = line.rstrip("\n")
            if not raw.strip():
                out.append("\n")
                continue

            stripped = raw.lstrip()
            indent = raw[: len(raw) - len(stripped)]

            # Headings like "Examples:" / "Interactive Picker Keys:" / "Backups:"
            if stripped.endswith(":") and not stripped.startswith(
                ("todo ", "TODO_DB=")
            ):
                out.append(indent, style="dim")
                out.append(stripped, style="bold bright_magenta")
                out.append("\n")
                continue

            # Comment-only lines
            if stripped.startswith("#"):
                out.append(raw, style="dim")
                out.append("\n")
                continue

            # Command lines (optionally with trailing inline comment)
            is_cmd = stripped.startswith("todo ") or stripped.startswith("TODO_DB=")
            if is_cmd:
                cmd_part = stripped
                comment_part = ""
                # Split "cmd   # comment" (keep spacing before #)
                if "#" in stripped:
                    before, after = stripped.split("#", 1)
                    if before.strip().startswith(("todo ", "TODO_DB=")):
                        cmd_part = before.rstrip()
                        comment_part = "# " + after.strip()

                out.append(indent, style="dim")
                out.append(cmd_part, style="bold cyan")
                if comment_part:
                    out.append("  ", style="dim")
                    out.append(comment_part, style="dim")
                out.append("\n")
                continue

            # Keybind lines like "↑ / ↓ : move"
            if ":" in stripped and any(
                stripped.startswith(prefix)
                for prefix in ("↑", "↓", "Space", "Enter", "Esc", "Tab")
            ):
                key, rest = stripped.split(":", 1)
                out.append(indent, style="dim")
                out.append(key.strip(), style="bold yellow")
                out.append(":", style="dim")
                out.append(rest, style="white")
                out.append("\n")
                continue

            # Default
            out.append(raw, style="white")
            out.append("\n")

        return out

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

        # Dedicated DB initialization / setup section (separate from Examples)
        setup = """
Initialize & DB Setup:
  todo init                           # create config + DB (if missing)
  todo init --dir ~/Documents/todo-cli --force
  todo init --db-path ~/Documents/todo-cli/todos.json --force

Temporary override (no config change):
  todo --db ./todos.json ls
  TODO_DB=./todos.json todo ls

Verify which DB is in use:
  todo config
  todo path

Precedence:
  --db > TODO_DB env > config > default
        """.strip(
            "\n"
        )
        console.print(
            Panel(
                _style_epilog_block(setup),
                title="[bold]Initialize & DB Setup[/bold]",
                border_style="bright_blue",
            )
        )
        console.print()

    # Epilog/Examples
    if parser.epilog:
        console.print(
            Panel(
                _style_epilog_block(parser.epilog),
                title="[bold]Examples & Tips[/bold]",
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
    cfg_before = load_config()
    cfg_p, db_p = init_config(
        db=args.db_path or None, dir_=args.dir or None, force=args.force
    )
    note = ""
    if cfg_before.db_path and not args.force and not (args.db_path or args.dir):
        note = "\n[dim]Note: config already had a DB path; kept existing. Use --force to overwrite.[/dim]"
    elif cfg_before.db_path and not args.force and (args.db_path or args.dir):
        note = "\n[dim]Note: config already had a DB path; not overwriting without --force.[/dim]"
    console.print(
        Panel.fit(
            f"[bold green]✨ Initialized todo-cli[/bold green]\n\n"
            f"[cyan]Config:[/cyan] {cfg_p}\n"
            f"[cyan]DB:[/cyan]     {db_p}\n"
            f"{note}\n\n"
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


def cmd_doctor(args, db_path: Path) -> None:
    """Validate (and optionally repair) the DB JSON."""
    issues: List[str] = []
    fixed = False

    def add(msg: str) -> None:
        issues.append(msg)

    # Lock DB while inspecting/repairing to avoid concurrent writes
    with FileLock(db_path.with_suffix(".lock")):
        if not db_path.exists():
            console.print()
            console.print(
                Panel(
                    f"[bold red]❌ DB not found[/bold red]\n\n"
                    f"[white]Expected DB at: [bold]{db_path}[/bold]\n"
                    f"Run [bold cyan]todo init[/bold cyan] or set [bold cyan]--db[/bold cyan]/[bold cyan]TODO_DB[/bold cyan].[/white]",
                    border_style="red",
                )
            )
            console.print()
            raise SystemExit(1)

        raw = ""
        data = None
        try:
            raw = db_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            add(f"Invalid JSON: {e}")
            if args.fix and args.restore:
                ok = restore_latest_backup(db_path, keep=BACKUP_KEEP_DEFAULT)
                if ok:
                    fixed = True
                    add(
                        f"Restored from latest backup (looked in {db_path.name}.1..{db_path.name}.{BACKUP_KEEP_DEFAULT})"
                    )
                    raw = db_path.read_text(encoding="utf-8")
                    data = json.loads(raw)
                else:
                    add("No backup could be restored.")
            if data is None:
                console.print()
                console.print(
                    Panel(
                        "[bold red]❌ Doctor found invalid JSON[/bold red]\n\n"
                        + "\n".join(f"- {x}" for x in issues[:10])
                        + ("\n- ..." if len(issues) > 10 else "")
                        + "\n\n[white]Tip: run [bold cyan]todo doctor --fix --restore[/bold cyan] to restore from backup.[/white]",
                        border_style="red",
                    )
                )
                console.print()
                raise SystemExit(1)

        if not isinstance(data, dict):
            add("Root must be an object")
            if not args.fix:
                raise SystemExit(1)
            data = {}
            fixed = True

        version = data.get("version", 1)
        try:
            version = int(version)
        except Exception:
            add(f"version is not an int: {version!r}")
            version = 1
            fixed = True

        next_id = data.get("next_id", 1)
        try:
            next_id = int(next_id)
        except Exception:
            add(f"next_id is not an int: {next_id!r}")
            next_id = 1
            fixed = True

        tasks_raw = data.get("tasks", [])
        if not isinstance(tasks_raw, list):
            add("tasks must be a list")
            if args.fix:
                tasks_raw = []
                fixed = True
            else:
                raise SystemExit(1)

        repaired_tasks = []
        seen_ids = set()
        max_id = 0

        for i, t in enumerate(tasks_raw):
            if not isinstance(t, dict):
                add(f"task[{i}] is not an object")
                if args.fix:
                    fixed = True
                    continue
                raise SystemExit(1)

            # id
            tid = t.get("id", 0)
            try:
                tid = int(tid)
            except Exception:
                add(f"task[{i}].id invalid: {tid!r}")
                if args.fix:
                    fixed = True
                    tid = 0
                else:
                    raise SystemExit(1)

            if tid <= 0 or tid in seen_ids:
                add(f"task[{i}].id missing/duplicate: {tid!r}")
                if not args.fix:
                    raise SystemExit(1)
                fixed = True
                tid = 0

            # normalize fields
            text = str(t.get("text", "")).strip()
            done = bool(t.get("done", False))
            created_at = str(t.get("created_at", ""))
            done_at = str(t.get("done_at", ""))
            priority = str(t.get("priority", "")).lower().strip()
            if priority not in ("", "low", "med", "high"):
                add(f"task[{i}].priority invalid: {priority!r}")
                if args.fix:
                    priority = ""
                    fixed = True
                else:
                    raise SystemExit(1)
            due = str(t.get("due", "")).strip()
            if due:
                try:
                    dt.date.fromisoformat(due)
                except Exception:
                    add(f"task[{i}].due invalid: {due!r}")
                    if args.fix:
                        due = ""
                        fixed = True
                    else:
                        raise SystemExit(1)
            tags = t.get("tags", [])
            if tags is None:
                tags = []
                fixed = True
            if not isinstance(tags, list) or not all(isinstance(x, str) for x in tags):
                add(f"task[{i}].tags invalid (expected list[str])")
                if args.fix:
                    tags = (
                        [str(x) for x in (tags or [])] if isinstance(tags, list) else []
                    )
                    fixed = True
                else:
                    raise SystemExit(1)

            if tid == 0:
                # assign later
                repaired_tasks.append(
                    {
                        "id": 0,
                        "text": text,
                        "done": done,
                        "created_at": created_at,
                        "done_at": done_at,
                        "priority": priority,
                        "due": due,
                        "tags": tags,
                    }
                )
                continue

            seen_ids.add(tid)
            max_id = max(max_id, tid)
            repaired_tasks.append(
                {
                    "id": tid,
                    "text": text,
                    "done": done,
                    "created_at": created_at,
                    "done_at": done_at,
                    "priority": priority,
                    "due": due,
                    "tags": tags,
                }
            )

        # Assign ids to any tasks that couldn't keep theirs
        if any(t.get("id") == 0 for t in repaired_tasks):
            if not args.fix:
                raise SystemExit(1)
            nid = max_id + 1
            for t in repaired_tasks:
                if t.get("id") == 0:
                    t["id"] = nid
                    nid += 1
            max_id = nid - 1
            fixed = True

        # Ensure next_id is sane
        if max_id + 1 != next_id:
            add(f"next_id adjusted: {next_id} -> {max_id + 1}")
            next_id = max_id + 1
            fixed = True if args.fix else fixed

        ok = len(issues) == 0
        if args.fix:
            # write repaired db (save_db will also rotate backups)
            from .storage import save_db  # local import to avoid circular

            save_db(
                db_path,
                {"version": version, "next_id": next_id, "tasks": repaired_tasks},
            )
            fixed = True

    # Print report
    title = (
        "✅ Doctor OK"
        if ok
        else ("🛠️  Doctor repaired" if fixed and args.fix else "⚠️  Doctor found issues")
    )
    border = "green" if ok else ("yellow" if fixed and args.fix else "red")
    body = (
        "\n".join(f"- {x}" for x in issues[:15])
        if issues
        else "[dim]No issues found.[/dim]"
    )
    if len(issues) > 15:
        body += "\n- ..."
    console.print()
    console.print(Panel(body, title=title, border_style=border))
    console.print()

    if not ok and not args.fix:
        raise SystemExit(1)


def cmd_migrate(args, db_path: Path) -> None:
    """Migrate DB schema to the current version (best-effort)."""
    with FileLock(db_path.with_suffix(".lock")):
        if not db_path.exists():
            console.print()
            console.print(
                Panel(
                    f"[bold red]❌ DB not found[/bold red]\n\n"
                    f"[white]Expected DB at: [bold]{db_path}[/bold][/white]",
                    border_style="red",
                )
            )
            console.print()
            raise SystemExit(1)

        try:
            raw = db_path.read_text(encoding="utf-8")
            db = json.loads(raw)
        except json.JSONDecodeError as e:
            console.print()
            console.print(
                Panel(
                    f"[bold red]❌ Invalid JSON[/bold red]\n\n[white]{e}[/white]\n\n"
                    f"[white]Try: [bold cyan]todo doctor --fix --restore[/bold cyan][/white]",
                    border_style="red",
                )
            )
            console.print()
            raise SystemExit(1)

        if not isinstance(db, dict):
            raise SystemExit("DB root must be an object")

        try:
            migrated, from_v, to_v, notes = migrate_db_data(db)
        except ValueError as e:
            console.print()
            console.print(Panel(f"[bold red]❌ {e}[/bold red]", border_style="red"))
            console.print()
            raise SystemExit(1)

        save_db(db_path, migrated)

    body = f"[white]Migrated DB: [bold]{db_path}[/bold]\\nFrom: {from_v} → To: {to_v}[/white]"
    if notes:
        body += "\\n\\n[bold]Notes:[/bold]\\n" + "\\n".join(f"- {n}" for n in notes)
    console.print()
    console.print(Panel(body, title="todo migrate", border_style="green"))
    console.print()


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


def cmd_qa(args, db_path: Path) -> None:
    """Quick add: just text, no flags."""
    # Normalize to cmd_add signature
    args.p = "med"
    args.due = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    args.tag = []
    cmd_add(args, db_path)


def cmd_today(args, db_path: Path) -> None:
    """Quick add with due=today."""
    args.p = ""
    args.due = dt.date.today().isoformat()
    args.tag = []
    cmd_add(args, db_path)


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


def cmd_stats(args, db_path: Path) -> None:
    """Show task statistics as a dashboard (or JSON for scripts)."""
    _, tasks = load_tasks(db_path)
    stats = calculate_statistics(tasks)
    if args.json:
        payload = {
            "total": int(stats.get("total", 0)),
            "pending": int(stats.get("pending", 0)),
            "done": int(stats.get("done", 0)),
            "high_priority": int(stats.get("high_priority", 0)),
            "overdue": int(stats.get("overdue", 0)),
            "due_today": int(stats.get("due_today", 0)),
        }
        print(json.dumps(payload, ensure_ascii=False))
        return
    render_statistics_dashboard(stats, title="Todo Stats")


def cmd_completion(args, _db_path: Path) -> None:
    """Print shell completion scripts (bash/zsh/fish)."""
    cmds = [
        "init",
        "config",
        "doctor",
        "add",
        "qa",
        "today",
        "ls",
        "stats",
        "done",
        "pick",
        "rm",
        "edit",
        "pri",
        "due",
        "tag",
        "archive",
        "clear-done",
        "path",
        "completion",
        "bug",
    ]
    cmd_list = " ".join(cmds)

    shell = (args.shell or "").lower()
    if shell == "bash":
        print(
            f"""# todo-cli bash completion
_todo_complete() {{
  local cur="${{COMP_WORDS[COMP_CWORD]}}"
  if [[ $COMP_CWORD -le 1 ]]; then
    COMPREPLY=( $(compgen -W "{cmd_list}" -- "$cur") )
    return 0
  fi
}}
complete -F _todo_complete todo
"""
        )
        return

    if shell == "zsh":
        print(
            f"""#compdef todo
# todo-cli zsh completion
_todo() {{
  local -a commands
  commands=({cmd_list})
  _arguments '1:command:->cmds' '*::arg:->args'
  case $state in
    cmds)
      _values 'command' $commands
      ;;
  esac
}}
_todo "$@"
"""
        )
        return

    if shell == "fish":
        print(
            f"""# todo-cli fish completion
set -l cmds {cmd_list}
complete -c todo -f -n "not __fish_seen_subcommand_from $cmds" -a "$cmds"
"""
        )
        return

    raise SystemExit("Unsupported shell. Use one of: bash, zsh, fish")


def cmd_done(args, db_path: Path) -> None:
    with FileLock(db_path.with_suffix(".lock")):
        next_id, tasks = load_tasks(db_path)
        # Ergonomic default: if no ID provided, open interactive picker.
        if args.id is None and not getattr(args, "pick", False):
            args.pick = True
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
        removed = [t for t in tasks if t.id == args.id]
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
        # Archive removed task(s) so deletes are recoverable
        archive_path = archive_path_for_db(db_path)
        with FileLock(archive_path.with_suffix(".lock")):
            append_tasks_to_archive(archive_path, removed)
        save_tasks(db_path, next_id, tasks)
    msg = Text()
    msg.append("🗑️  Removed ", style="bold red")
    msg.append(f"#{args.id}", style="bold white")
    msg.append(" (archived) → ", style="dim")
    msg.append(str(archive_path_for_db(db_path)), style="bold white")
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


def _archive_done_tasks(db_path: Path) -> tuple[int, Path]:
    """Move done tasks out of main DB into todos-archieved.json (same folder)."""
    archive_path = archive_path_for_db(db_path)
    with FileLock(db_path.with_suffix(".lock")):
        next_id, tasks = load_tasks(db_path)
        done_tasks = [t for t in tasks if t.done]
        if not done_tasks:
            return (0, archive_path)
        # Lock archive after main DB (consistent order)
        with FileLock(archive_path.with_suffix(".lock")):
            appended = append_tasks_to_archive(archive_path, done_tasks)
        tasks = [t for t in tasks if not t.done]
        save_tasks(db_path, next_id, tasks)
    return (appended, archive_path)


def cmd_archive(args, db_path: Path) -> None:
    # currently only supports archiving done tasks
    count, ap = _archive_done_tasks(db_path)
    if count == 0:
        console.print("[dim]📭 No done tasks to archive[/dim]")
        return
    msg = Text()
    msg.append("📦 Archived ", style="bold cyan")
    msg.append(str(count), style="bold white")
    msg.append(" done task" + ("s" if count != 1 else ""), style="white")
    msg.append(" → ", style="dim")
    msg.append(str(ap), style="bold white")
    console.print(msg)


def cmd_clear_done(args, db_path: Path) -> None:
    if getattr(args, "force", False):
        # Dangerous: truly delete (no archive)
        with FileLock(db_path.with_suffix(".lock")):
            next_id, tasks = load_tasks(db_path)
            before = len(tasks)
            tasks = [t for t in tasks if not t.done]
            save_tasks(db_path, next_id, tasks)
        cleared_count = before - len(tasks)
        msg = Text()
        msg.append("🗑️  Deleted ", style="bold red")
        msg.append(str(cleared_count), style="bold white")
        msg.append(f" done task{'s' if cleared_count != 1 else ''}", style="white")
        console.print(msg)
        return

    # Default: archive instead of delete
    count, ap = _archive_done_tasks(db_path)
    if count == 0:
        console.print("[dim]📭 No done tasks to clear[/dim]")
        return
    msg = Text()
    msg.append("🧹 Cleared ", style="bold yellow")
    msg.append(str(count), style="bold white")
    msg.append(f" done task{'s' if count != 1 else ''}", style="white")
    msg.append(" (archived) → ", style="dim")
    msg.append(str(ap), style="bold white")
    console.print(msg)


def cmd_path(args, db_path: Path) -> None:
    msg = Text()
    msg.append("📁 Database path: ", style="bold cyan")
    msg.append(str(db_path), style="bold white")
    console.print(msg)


# ============================================================================
# Bug Tracking Commands
# ============================================================================


def cmd_bug_add(args, db_path: Path) -> None:
    """Add a new bug report."""
    with FileLock(db_path.with_suffix(".lock")):
        next_id, tasks = load_tasks(db_path)
        # Convert literal \n to actual newlines in steps
        steps = (args.steps or "").replace("\\n", "\n") if args.steps else ""
        t = Task(
            id=next_id,
            text=args.text.strip(),
            done=False,
            created_at=now_iso(),
            priority=(args.p or "").lower(),
            due=parse_date(args.due) if args.due else "",
            tags=(args.tag or []) + ["bug"],  # Auto-add #bug tag
            bug_status=args.status or "open",
            bug_assignee=args.assignee or "",
            bug_severity=(args.severity or "").lower(),
            bug_steps=steps,
            bug_environment=args.env or "",
        )
        tasks.append(t)
        save_tasks(db_path, next_id + 1, tasks)
    msg = Text()
    msg.append("🐛 Bug #", style="bold red")
    msg.append(f"{t.id}", style="bold white")
    msg.append(f": {t.text}", style="white")
    if t.bug_severity:
        msg.append(f" [{t.bug_severity.upper()}]", style="bold red")
    console.print(msg)


def cmd_bug_list(args, db_path: Path) -> None:
    """List all bugs."""
    _, tasks = load_tasks(db_path)
    bugs = [t for t in tasks if t.is_bug()]

    if args.status:
        bugs = [b for b in bugs if (b.bug_status or "").lower() == args.status.lower()]
    if args.severity:
        bugs = [
            b for b in bugs if (b.bug_severity or "").lower() == args.severity.lower()
        ]
    if args.assignee:
        bugs = [
            b for b in bugs if (b.bug_assignee or "").lower() == args.assignee.lower()
        ]
    if args.env:
        bugs = [
            b for b in bugs if (b.bug_environment or "").lower() == args.env.lower()
        ]

    if not bugs:
        console.print("[dim]🐛 No bugs found[/dim]")
        return

    # Render bugs in a table with bug-specific columns
    from .render import render_bugs_table

    render_bugs_table(bugs, title="Bugs")


def cmd_bug_show(args, db_path: Path) -> None:
    """Show detailed bug information."""
    _, tasks = load_tasks(db_path)
    t = find_task(tasks, args.id)

    if not t.is_bug():
        console.print()
        console.print(
            Panel(
                f"[bold yellow]⚠️  Task #{args.id} is not a bug[/bold yellow]\n\n"
                f"[white]Use [bold cyan]todo bug add[/bold cyan] to create bugs.[/white]",
                border_style="yellow",
            )
        )
        console.print()
        return

    # Render detailed bug panel
    from .render import render_bug_detail

    render_bug_detail(t)


def cmd_bug_status(args, db_path: Path) -> None:
    """Set bug status."""
    valid_statuses = ["open", "in-progress", "fixed", "closed"]
    status = args.status.lower()
    if status not in valid_statuses:
        console.print()
        console.print(
            Panel(
                f"[bold red]❌ Invalid bug status[/bold red]\n\n"
                f"[white]Status: [bold yellow]{args.status}[/bold yellow]\n"
                f"Must be one of: [bold cyan]{', '.join(valid_statuses)}[/bold cyan][/white]",
                border_style="red",
            )
        )
        console.print()
        raise SystemExit(1)

    with FileLock(db_path.with_suffix(".lock")):
        next_id, tasks = load_tasks(db_path)
        t = find_task(tasks, args.id)
        if not t.is_bug():
            # Convert to bug if not already
            if not t.tags:
                t.tags = []
            if "bug" not in [tag.lower() for tag in t.tags]:
                t.tags.append("bug")
        t.bug_status = status
        save_tasks(db_path, next_id, tasks)

    msg = Text()
    msg.append("🐛 Bug status set for #", style="bold cyan")
    msg.append(f"{args.id}", style="bold white")
    msg.append(f" -> ", style="dim")
    status_colors = {
        "open": "yellow",
        "in-progress": "blue",
        "fixed": "green",
        "closed": "dim",
    }
    msg.append(status.upper(), style=f"bold {status_colors.get(status, 'white')}")
    console.print(msg)


def cmd_bug_assign(args, db_path: Path) -> None:
    """Assign bug to someone."""
    with FileLock(db_path.with_suffix(".lock")):
        next_id, tasks = load_tasks(db_path)
        t = find_task(tasks, args.id)
        if not t.is_bug():
            # Convert to bug if not already
            if not t.tags:
                t.tags = []
            if "bug" not in [tag.lower() for tag in t.tags]:
                t.tags.append("bug")
        t.bug_assignee = args.assignee.strip()
        save_tasks(db_path, next_id, tasks)

    msg = Text()
    msg.append("👤 Assigned bug #", style="bold cyan")
    msg.append(f"{args.id}", style="bold white")
    msg.append(f" to ", style="dim")
    msg.append(args.assignee, style="bold white")
    console.print(msg)


def cmd_bug_severity(args, db_path: Path) -> None:
    """Set bug severity."""
    valid_severities = ["critical", "high", "medium", "low"]
    severity = args.severity.lower()
    if severity not in valid_severities:
        console.print()
        console.print(
            Panel(
                f"[bold red]❌ Invalid bug severity[/bold red]\n\n"
                f"[white]Severity: [bold yellow]{args.severity}[/bold yellow]\n"
                f"Must be one of: [bold cyan]{', '.join(valid_severities)}[/bold cyan][/white]",
                border_style="red",
            )
        )
        console.print()
        raise SystemExit(1)

    with FileLock(db_path.with_suffix(".lock")):
        next_id, tasks = load_tasks(db_path)
        t = find_task(tasks, args.id)
        if not t.is_bug():
            # Convert to bug if not already
            if not t.tags:
                t.tags = []
            if "bug" not in [tag.lower() for tag in t.tags]:
                t.tags.append("bug")
        t.bug_severity = severity
        save_tasks(db_path, next_id, tasks)

    msg = Text()
    msg.append("⚡ Severity set for bug #", style="bold cyan")
    msg.append(f"{args.id}", style="bold white")
    msg.append(f" -> ", style="dim")
    severity_colors = {
        "critical": "bold red",
        "high": "bold yellow",
        "medium": "bold blue",
        "low": "bold cyan",
    }
    msg.append(severity.upper(), style=severity_colors.get(severity, "white"))
    console.print(msg)


def cmd_bug_steps(args, db_path: Path) -> None:
    """Set steps to reproduce."""
    with FileLock(db_path.with_suffix(".lock")):
        next_id, tasks = load_tasks(db_path)
        t = find_task(tasks, args.id)
        if not t.is_bug():
            # Convert to bug if not already
            if not t.tags:
                t.tags = []
            if "bug" not in [tag.lower() for tag in t.tags]:
                t.tags.append("bug")
        # Convert literal \n to actual newlines
        steps = args.steps.strip().replace("\\n", "\n")
        t.bug_steps = steps
        save_tasks(db_path, next_id, tasks)

    msg = Text()
    msg.append("📝 Steps to reproduce set for bug #", style="bold cyan")
    msg.append(f"{args.id}", style="bold white")
    console.print(msg)


def cmd_bug_env(args, db_path: Path) -> None:
    """Set bug environment."""
    with FileLock(db_path.with_suffix(".lock")):
        next_id, tasks = load_tasks(db_path)
        t = find_task(tasks, args.id)
        if not t.is_bug():
            # Convert to bug if not already
            if not t.tags:
                t.tags = []
            if "bug" not in [tag.lower() for tag in t.tags]:
                t.tags.append("bug")
        t.bug_environment = args.env.strip()
        save_tasks(db_path, next_id, tasks)

    msg = Text()
    msg.append("🌍 Environment set for bug #", style="bold cyan")
    msg.append(f"{args.id}", style="bold white")
    msg.append(f" -> ", style="dim")
    msg.append(args.env, style="bold white")
    console.print(msg)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="todo",
        description="A local TODO CLI with rich tables, interactive picker, stats, backups, and safe archiving.",
        epilog="""
Examples:
  # Quick start
  todo add "Fix Celery retries" --p high --due 2025-12-20 --tag backend --tag infra
  todo add "Refactor auth middleware" --p med --tag security
  todo ls --pending --sort priority
  todo done              # no args opens picker (marks selected as done)
  todo ls --all

  # Fast capture
  todo qa "Review PR"
  todo today "Pay invoice"     # due=today

  # Stats (pretty + JSON)
  todo stats
  todo stats --json

  # Safe cleanup (archive-first)
  todo clear-done              # moves done tasks to todos-archieved.json
  todo clear-done --force      # permanent delete (dangerous)
  todo archive done

  # Health / recovery
  todo doctor
  todo doctor --fix --restore  # restore from rotating backups if JSON is invalid

  # Bug tracking (QA-friendly)
  todo bug add "Login button not working" --severity critical --env prod --assignee john
  todo bug list --status open
  todo bug status 1 in-progress
  todo bug assign 1 jane
  todo bug show 1

  # Storage override
  todo --db /path/to/todos.json ls
  TODO_DB=/path/to/todos.json todo ls

  # Shell completion
  todo completion zsh > _todo

Interactive Picker Keys:
  ↑ / ↓ : move
  Space : toggle selection
  Enter : confirm
  Esc   : cancel

For more information, see: README.md, PATH_RESOLUTION.md, and todo-cli/TROUBLESHOOTING.md
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
        "doctor",
        help="Validate/repair the DB JSON",
        description="Validate your todos DB and optionally repair common issues. Can restore from rotating backups.",
        epilog=f"""
Examples:
  todo doctor
  todo doctor --fix
  todo doctor --fix --restore

Backups:
  On every write, todo-cli keeps rotating backups next to your DB:
    {{"db"}}.1 .. {{"db"}}.{BACKUP_KEEP_DEFAULT}
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument(
        "--fix", action="store_true", help="Attempt to repair issues in-place"
    )
    sp.add_argument(
        "--restore",
        action="store_true",
        help=f"Restore from latest backup if JSON is invalid (checks .1..{BACKUP_KEEP_DEFAULT})",
    )
    sp.set_defaults(fn=cmd_doctor)

    sp = sub.add_parser(
        "migrate",
        help="Migrate DB schema to latest",
        description="Migrate your DB JSON schema to the latest supported version (with backups).",
        epilog="""
Examples:
  todo migrate
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.set_defaults(fn=cmd_migrate)

    sp = sub.add_parser(
        "completion",
        help="Generate shell completion",
        description="Print a shell completion script to stdout.",
        epilog="""
Examples:
  todo completion bash > todo.bash
  todo completion zsh  > _todo
  todo completion fish > todo.fish
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument("shell", type=str, choices=["bash", "zsh", "fish"])
    sp.set_defaults(fn=cmd_completion)

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
        "qa",
        help="Quick add (text only)",
        description="Quickly add a task with just text (no flags).",
        epilog="""
Examples:
  todo qa "Review PR"
  todo qa "Ship release notes"
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument("text", type=str, help="Task description")
    sp.set_defaults(fn=cmd_qa)

    sp = sub.add_parser(
        "today",
        help="Quick add due today",
        description="Quickly add a task with due date set to today.",
        epilog="""
Examples:
  todo today "Pay invoice"
  todo today "Follow up with recruiter"
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument("text", type=str, help="Task description")
    sp.set_defaults(fn=cmd_today)

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
  todo ls --sort due         # Sort by due date (overdue first)
  todo ls --sort created     # Sort by creation date (default)
  todo ls --plain            # Plain text output (no table)

Sort options: created, due, priority

Due badges:
  OVERDUE, TODAY, IN Nd (plus relative coloring in the table)
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
        "stats",
        help="Show stats dashboard",
        description="Show task statistics: total, pending, done, high priority, overdue, due today, due soon.",
        epilog="""
Examples:
  todo stats
  todo stats --json
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument(
        "--json", action="store_true", help="Print stats as JSON (for scripts)"
    )
    sp.set_defaults(fn=cmd_stats)

    sp = sub.add_parser(
        "done",
        help="Mark task(s) as done or undone",
        description="Mark a task as done by ID, or use interactive picker to select multiple tasks.",
        epilog="""
Examples:
  todo done                  # Interactive picker (marks selected as done)
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
        "archive",
        help="Archive tasks (move out of main DB)",
        description="Move tasks from the main DB into todos-archieved.json (same folder as your todos DB).",
        epilog="""
Examples:
  todo archive done          # Move all done tasks into todos-archieved.json
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument(
        "scope",
        type=str,
        nargs="?",
        default="done",
        choices=["done"],
        help="What to archive (currently only: done)",
    )
    sp.set_defaults(fn=cmd_archive)

    sp = sub.add_parser(
        "clear-done",
        help="Clear completed tasks (archives by default)",
        description="Remove done tasks from the active list. By default, tasks are moved to todos-archieved.json (safer).",
        epilog="""
Examples:
  todo clear-done            # Move all completed tasks to todos-archieved.json
  todo clear-done --force    # Permanently delete done tasks (dangerous)
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument(
        "--force",
        action="store_true",
        help="Permanently delete done tasks instead of archiving",
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

    # Bug tracking subcommands
    bug_sub = sub.add_parser(
        "bug",
        help="Bug tracking commands",
        description="Track bugs with status, severity, assignee, steps to reproduce, and environment.",
        epilog="""
Examples:
  # Create bugs
  todo bug add "Login button not working" --severity critical --env prod
  todo bug add "API returns 500" --severity high --assignee john --steps "1. Open app\\n2. Click login"

  # List and filter bugs
  todo bug list
  todo bug list --status open --severity critical
  todo bug list --assignee john --env prod

  # Manage bugs
  todo bug show 1                    # View detailed bug info
  todo bug status 1 in-progress      # Update status
  todo bug assign 1 jane             # Assign to someone
  todo bug severity 1 high           # Set severity
  todo bug steps 1 "1. Step\\n2. Step"  # Add reproduction steps
  todo bug env 1 staging             # Set environment

Bugs are regular tasks with additional fields and automatically tagged with #bug.
Use 'todo ls --tag bug' to see bugs in regular task lists.
        """,
        formatter_class=RichHelpFormatter,
    )
    bug_cmds = bug_sub.add_subparsers(
        dest="bug_cmd", required=True, title="bug commands", metavar="COMMAND"
    )

    sp = bug_cmds.add_parser(
        "add",
        help="Add a new bug report",
        description="Create a new bug report with optional fields.",
        epilog="""
Examples:
  # Basic bug
  todo bug add "Login button not working"

  # Bug with severity and environment
  todo bug add "API returns 500" --severity critical --env prod --assignee john

  # Complete bug with all fields
  todo bug add "UI glitch" --severity medium --status in-progress \\
    --steps "1. Open app\\n2. Click button\\n3. See error" \\
    --assignee jane --env staging --p high --due 2025-12-25

  # Quick bug for QA
  todo bug add "Payment fails on Safari" --severity high --env staging
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument("text", type=str, help="Bug description")
    sp.add_argument(
        "--severity",
        type=str,
        choices=["critical", "high", "medium", "low"],
        help="Bug severity",
    )
    sp.add_argument(
        "--status",
        type=str,
        choices=["open", "in-progress", "fixed", "closed"],
        default="open",
        help="Bug status (default: open)",
    )
    sp.add_argument("--assignee", type=str, default="", help="Assign bug to someone")
    sp.add_argument(
        "--env", type=str, default="", help="Environment (e.g., dev, staging, prod)"
    )
    sp.add_argument("--steps", type=str, default="", help="Steps to reproduce")
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
    sp.set_defaults(fn=cmd_bug_add)

    sp = bug_cmds.add_parser(
        "list",
        help="List all bugs",
        description="List all bugs with filtering options.",
        epilog="""
Examples:
  # List all bugs
  todo bug list

  # Filter by status
  todo bug list --status open
  todo bug list --status in-progress
  todo bug list --status fixed

  # Filter by severity
  todo bug list --severity critical
  todo bug list --severity high

  # Filter by assignee or environment
  todo bug list --assignee john
  todo bug list --env prod

  # Combine multiple filters (all must match)
  todo bug list --status open --severity critical --env prod
  todo bug list --status open --assignee john
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument(
        "--status",
        type=str,
        choices=["open", "in-progress", "fixed", "closed"],
        help="Filter by status",
    )
    sp.add_argument(
        "--severity",
        type=str,
        choices=["critical", "high", "medium", "low"],
        help="Filter by severity",
    )
    sp.add_argument("--assignee", type=str, help="Filter by assignee")
    sp.add_argument("--env", type=str, help="Filter by environment")
    sp.set_defaults(fn=cmd_bug_list)

    sp = bug_cmds.add_parser(
        "show",
        help="Show detailed bug information",
        description="Display detailed information about a specific bug.",
        epilog="""
Examples:
  # Show detailed bug information
  todo bug show 1

Displays all bug fields including status, severity, assignee, environment,
steps to reproduce, priority, due date, tags, and timestamps.
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument("id", type=int, metavar="ID", help="Bug ID")
    sp.set_defaults(fn=cmd_bug_show)

    sp = bug_cmds.add_parser(
        "status",
        help="Set bug status",
        description="Update the status of a bug.",
        epilog="""
Examples:
  todo bug status 1 open
  todo bug status 1 in-progress
  todo bug status 1 fixed
  todo bug status 1 closed
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument("id", type=int, metavar="ID", help="Bug ID")
    sp.add_argument(
        "status",
        type=str,
        choices=["open", "in-progress", "fixed", "closed"],
        help="New status",
    )
    sp.set_defaults(fn=cmd_bug_status)

    sp = bug_cmds.add_parser(
        "assign",
        help="Assign bug to someone",
        description="Assign a bug to a team member.",
        epilog="""
Examples:
  # Assign bug to someone
  todo bug assign 1 john
  todo bug assign 2 "Jane Doe"
  todo bug assign 3 backend-team

The assignee can be a name, username, or team identifier.
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument("id", type=int, metavar="ID", help="Bug ID")
    sp.add_argument("assignee", type=str, help="Assignee name")
    sp.set_defaults(fn=cmd_bug_assign)

    sp = bug_cmds.add_parser(
        "severity",
        help="Set bug severity",
        description="Set the severity level of a bug.",
        epilog="""
Examples:
  todo bug severity 1 critical
  todo bug severity 1 high
  todo bug severity 1 medium
  todo bug severity 1 low
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument("id", type=int, metavar="ID", help="Bug ID")
    sp.add_argument(
        "severity",
        type=str,
        choices=["critical", "high", "medium", "low"],
        help="Severity level",
    )
    sp.set_defaults(fn=cmd_bug_severity)

    sp = bug_cmds.add_parser(
        "steps",
        help="Set steps to reproduce",
        description="Add or update steps to reproduce a bug.",
        epilog="""
Examples:
  # Add steps to reproduce (use \\n for line breaks)
  todo bug steps 1 "1. Open the app\\n2. Click login\\n3. See error"

  # Multi-line steps example
  todo bug steps 1 "1. Navigate to checkout page\\n2. Select payment method\\n3. Enter card details\\n4. Click pay button\\n5. Observe: Payment fails with error message"

Use \\n to create line breaks in the steps. The steps will be displayed
formatted when viewing the bug with 'todo bug show'.
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument("id", type=int, metavar="ID", help="Bug ID")
    sp.add_argument("steps", type=str, help="Steps to reproduce")
    sp.set_defaults(fn=cmd_bug_steps)

    sp = bug_cmds.add_parser(
        "env",
        help="Set bug environment",
        description="Set the environment where the bug occurs.",
        epilog="""
Examples:
  todo bug env 1 prod
  todo bug env 1 staging
  todo bug env 1 dev
        """,
        formatter_class=RichHelpFormatter,
    )
    sp.add_argument("id", type=int, metavar="ID", help="Bug ID")
    sp.add_argument("env", type=str, help="Environment name")
    sp.set_defaults(fn=cmd_bug_env)

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
    if args.cmd == "done" and args.id is None and getattr(args, "undo", False):
        console.print()
        console.print(
            Panel(
                "[bold red]❌ Error[/bold red]\n\n"
                "[white]todo done --undo requires an ID[/white]",
                border_style="red",
            )
        )
        console.print()
        raise SystemExit(1)

    # Call the command function (works for both top-level and nested bug commands)
    if hasattr(args, "fn"):
        args.fn(args, db_path)
    else:
        console.print()
        console.print(
            Panel(
                "[bold red]❌ Command not found[/bold red]\n\n"
                "[white]Use [bold cyan]todo --help[/bold cyan] for available commands.[/white]",
                border_style="red",
            )
        )
        console.print()
        raise SystemExit(1)
    return 0
