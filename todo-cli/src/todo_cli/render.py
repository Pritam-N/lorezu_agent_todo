from __future__ import annotations
from typing import Iterable
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns
from rich import box
from rich.align import Align
from datetime import datetime, date, timedelta
from .model import Task


def calculate_statistics(tasks: Iterable[Task]) -> dict:
    """Public wrapper to compute task statistics for commands like `todo stats`."""
    return _calculate_statistics(list(tasks))


def render_statistics_dashboard(stats: dict, title: str = "Stats") -> None:
    """Render a production-style stats dashboard (panels)."""
    console = Console()
    console.print(
        Panel.fit(
            f"[bold bright_magenta]📊 {title}[/bold bright_magenta]",
            border_style="bright_blue",
        )
    )
    console.print()
    _render_statistics(stats, console)


def _format_status(done: bool) -> Text:
    """Format status with modern indicators"""
    if done:
        return Text("✓", style="bold green")
    return Text("○", style="bright_black")


def _format_priority(priority: str) -> Text:
    """Format priority with modern badges"""
    pri = (priority or "").lower()
    if pri == "high":
        return Text("🔴 HIGH", style="bold white on red")
    elif pri == "med":
        return Text("🟡 MED", style="bold black on yellow")
    elif pri == "low":
        return Text("🔵 LOW", style="bold white on blue")
    return Text("—", style="dim")


def _format_due(due_str: str) -> Text:
    """Format due date with badge-style UX (OVERDUE / TODAY / IN Nd)."""
    if not due_str:
        return Text("—", style="dim")
    try:
        due_date = date.fromisoformat(due_str)
        today = date.today()
        days_until = (due_date - today).days

        out = Text()
        if days_until < 0:
            overdue_days = abs(days_until)
            out.append("OVERDUE", style="bold white on red")
            out.append(" ")
            out.append(due_str, style="dim")
            out.append(f" ({overdue_days}d)", style="red")
            return out
        if days_until == 0:
            out.append("TODAY", style="bold black on yellow")
            out.append(" ")
            out.append(due_str, style="dim")
            return out

        out.append(
            f"IN {days_until}d",
            style=(
                "bold black on cyan" if days_until <= 7 else "bold black on bright_cyan"
            ),
        )
        out.append(" ")
        out.append(due_str, style="dim")
        return out
    except (ValueError, TypeError):
        return Text(due_str, style="dim")


def _format_tags(tags: list) -> Text:
    """Format tags with modern badge styling"""
    if not tags:
        return Text("—", style="dim")
    tag_text = Text()
    for i, tag in enumerate(tags):
        if i > 0:
            tag_text.append(" ", style="dim")
        tag_text.append(f"#{tag}", style="bold cyan")
    return tag_text


def _format_task_id(task_id: int, done: bool) -> Text:
    """Format task ID with styling"""
    style = "dim" if done else "bold bright_white"
    return Text(f"#{task_id}", style=style)


def _format_task_text(text: str, done: bool, priority: str) -> Text:
    """Format task text with appropriate styling"""
    task_text = Text(text or "")
    if done:
        task_text.stylize("dim strikethrough")
    else:
        # Highlight high priority tasks
        pri = (priority or "").lower()
        if pri == "high":
            task_text.stylize("bold white")
        else:
            task_text.stylize("white")
    return task_text


def _calculate_statistics(tasks: list[Task]) -> dict:
    """Calculate task statistics"""
    total = len(tasks)
    done = sum(1 for t in tasks if t.done)
    pending = total - done
    high_priority = sum(
        1 for t in tasks if not t.done and (t.priority or "").lower() == "high"
    )

    overdue = 0
    due_today = 0
    due_soon = 0

    today = date.today()
    for t in tasks:
        if t.done or not t.due:
            continue
        try:
            due_date = date.fromisoformat(t.due)
            days_until = (due_date - today).days
            if days_until < 0:
                overdue += 1
            elif days_until == 0:
                due_today += 1
            elif days_until <= 3:
                due_soon += 1
        except (ValueError, TypeError):
            pass

    return {
        "total": total,
        "done": done,
        "pending": pending,
        "high_priority": high_priority,
        "overdue": overdue,
        "due_today": due_today,
        "due_soon": due_soon,
    }


def _render_statistics(stats: dict, console: Console) -> None:
    """Render statistics panel"""
    if stats["total"] == 0:
        return

    stats_items = []

    # Total tasks
    total_text = Text()
    total_text.append(f"{stats['total']}", style="bold white")
    total_text.append("\n")
    total_text.append("Total", style="dim")
    stats_items.append(
        Panel(
            Align.center(total_text),
            border_style="blue",
            padding=(0, 1),
        )
    )

    # Pending tasks
    if stats["pending"] > 0:
        pending_text = Text()
        pending_text.append(f"{stats['pending']}", style="bold yellow")
        pending_text.append("\n")
        pending_text.append("Pending", style="dim")
        stats_items.append(
            Panel(
                Align.center(pending_text),
                border_style="yellow",
                padding=(0, 1),
            )
        )

    # Done tasks
    if stats["done"] > 0:
        done_text = Text()
        done_text.append(f"{stats['done']}", style="bold green")
        done_text.append("\n")
        done_text.append("Done", style="dim")
        stats_items.append(
            Panel(
                Align.center(done_text),
                border_style="green",
                padding=(0, 1),
            )
        )

    # High priority
    if stats["high_priority"] > 0:
        high_text = Text()
        high_text.append(f"{stats['high_priority']}", style="bold red")
        high_text.append("\n")
        high_text.append("High Priority", style="dim")
        stats_items.append(
            Panel(
                Align.center(high_text),
                border_style="red",
                padding=(0, 1),
            )
        )

    # Overdue
    if stats["overdue"] > 0:
        overdue_text = Text()
        overdue_text.append(f"{stats['overdue']}", style="bold red")
        overdue_text.append("\n")
        overdue_text.append("Overdue", style="dim")
        stats_items.append(
            Panel(
                Align.center(overdue_text),
                border_style="red",
                padding=(0, 1),
            )
        )

    # Due today
    if stats["due_today"] > 0:
        today_text = Text()
        today_text.append(f"{stats['due_today']}", style="bold yellow")
        today_text.append("\n")
        today_text.append("Due Today", style="dim")
        stats_items.append(
            Panel(
                Align.center(today_text),
                border_style="yellow",
                padding=(0, 1),
            )
        )

    if stats_items:
        console.print(Columns(stats_items, equal=True, expand=True))
        console.print()


def render_tasks_table(tasks: Iterable[Task], title: str = "TODOs") -> None:
    console = Console()
    task_list = list(tasks)

    # Calculate statistics
    stats = _calculate_statistics(task_list)

    # Render statistics if there are tasks
    if task_list:
        _render_statistics(stats, console)

    # Handle empty state
    if not task_list:
        empty_panel = Panel(
            Align.center(Text("📭 No tasks found", style="dim")),
            border_style="dim",
            padding=(1, 2),
        )
        console.print()
        console.print(empty_panel)
        console.print()
        return

    # Create modern table with production-grade styling
    table = Table(
        show_header=True,
        header_style="bold bright_white",
        border_style="bright_blue",
        box=box.ROUNDED,
        show_lines=True,
        padding=(0, 1),
        title=f"📋 {title}",
        title_style="bold bright_magenta",
        caption=f"Total: {stats['total']} | Pending: {stats['pending']} | Done: {stats['done']}",
        caption_style="dim",
    )

    # Define columns with optimal widths
    table.add_column(
        "ID",
        justify="right",
        no_wrap=True,
        style="bright_white",
        width=5,
        header_style="bold bright_white",
    )
    table.add_column(
        "Status",
        justify="center",
        no_wrap=True,
        width=6,
        header_style="bold bright_white",
    )
    table.add_column(
        "Priority",
        justify="center",
        no_wrap=True,
        width=8,
        header_style="bold bright_white",
    )
    table.add_column(
        "Due Date",
        justify="left",
        no_wrap=False,
        width=22,
        header_style="bold bright_white",
    )
    table.add_column(
        "Tags",
        justify="left",
        no_wrap=False,
        width=18,
        header_style="bold bright_white",
    )
    table.add_column(
        "Task",
        overflow="fold",
        ratio=2,
        header_style="bold bright_white",
    )

    # Add rows with enhanced styling
    for i, t in enumerate(task_list):
        task_id = _format_task_id(t.id, t.done)
        status = _format_status(t.done)
        priority = _format_priority(t.priority)
        due = _format_due(t.due)
        tags = _format_tags(t.tags or [])
        task_text = _format_task_text(t.text or "", t.done, t.priority)

        # Determine row style based on urgency
        row_style = None
        if not t.done:
            pri = (t.priority or "").lower()
            if pri == "high":
                row_style = "bold"
            elif t.due:
                try:
                    due_date = date.fromisoformat(t.due)
                    days_until = (due_date - date.today()).days
                    if days_until < 0:
                        row_style = "bold red"
                    elif days_until == 0:
                        row_style = "bold yellow"
                except (ValueError, TypeError):
                    pass

        table.add_row(
            task_id,
            status,
            priority,
            due,
            tags,
            task_text,
            style=row_style,
        )

    # Render table
    console.print()
    console.print(table)
    console.print()


def render_tasks_plain(tasks: Iterable[Task]) -> None:
    """Render tasks in plain text format with modern styling"""
    console = Console()
    task_list = list(tasks)

    if not task_list:
        console.print("[dim]📭 No tasks found[/dim]")
        return

    # Use the same formatting functions for consistency
    for t in task_list:
        task_id = _format_task_id(t.id, t.done)
        status = _format_status(t.done)
        priority = _format_priority(t.priority)
        due = _format_due(t.due)
        tags = _format_tags(t.tags or [])
        task_text = _format_task_text(t.text or "", t.done, t.priority)

        # Build the line with consistent spacing
        line = Text()
        line.append(status)
        line.append("  ")
        line.append(task_id)
        line.append("  ")
        line.append(priority)
        line.append("  ")
        line.append(due)
        if t.tags:  # Only add tags if they exist
            line.append("  ")
            line.append(tags)
        line.append("  ")
        line.append(task_text)

        console.print(line)


def _format_bug_status(status: str) -> Text:
    """Format bug status with color coding."""
    status_lower = (status or "open").lower()
    status_colors = {
        "open": "bold yellow",
        "in-progress": "bold blue",
        "fixed": "bold green",
        "closed": "dim",
    }
    style = status_colors.get(status_lower, "white")
    return Text(status_lower.upper(), style=style)


def _format_bug_severity(severity: str) -> Text:
    """Format bug severity with color coding."""
    if not severity:
        return Text("—", style="dim")
    severity_lower = severity.lower()
    severity_styles = {
        "critical": "bold white on red",
        "high": "bold white on yellow",
        "medium": "bold black on blue",
        "low": "bold white on cyan",
    }
    style = severity_styles.get(severity_lower, "white")
    return Text(severity_lower.upper(), style=style)


def render_bugs_table(bugs: Iterable[Task], title: str = "Bugs") -> None:
    """Render bugs in a table with bug-specific columns."""
    console = Console()
    bug_list = list(bugs)

    if not bug_list:
        console.print("[dim]🐛 No bugs found[/dim]")
        return

    table = Table(
        show_header=True,
        header_style="bold bright_white",
        border_style="bright_red",
        box=box.ROUNDED,
        show_lines=True,
        padding=(0, 1),
        title=f"🐛 {title}",
        title_style="bold bright_red",
        caption=f"Total: {len(bug_list)}",
        caption_style="dim",
    )

    table.add_column("ID", justify="right", no_wrap=True, style="bright_white", width=5)
    table.add_column(
        "Status",
        justify="center",
        no_wrap=True,
        width=12,
        header_style="bold bright_white",
    )
    table.add_column(
        "Severity",
        justify="center",
        no_wrap=True,
        width=10,
        header_style="bold bright_white",
    )
    table.add_column(
        "Assignee",
        justify="left",
        no_wrap=True,
        width=15,
        header_style="bold bright_white",
    )
    table.add_column(
        "Env", justify="left", no_wrap=True, width=10, header_style="bold bright_white"
    )
    table.add_column(
        "Priority",
        justify="center",
        no_wrap=True,
        width=8,
        header_style="bold bright_white",
    )
    table.add_column(
        "Steps",
        justify="left",
        no_wrap=False,
        width=25,
        header_style="bold bright_white",
    )
    table.add_column(
        "Bug Description", overflow="fold", ratio=2, header_style="bold bright_white"
    )

    for b in bug_list:
        bug_id = _format_task_id(b.id, b.done)
        bug_status = _format_bug_status(b.bug_status)
        bug_severity = _format_bug_severity(b.bug_severity)
        assignee = Text(
            b.bug_assignee or "—", style="white" if b.bug_assignee else "dim"
        )
        env = Text(
            b.bug_environment or "—", style="white" if b.bug_environment else "dim"
        )
        priority = _format_priority(b.priority)

        # Format steps: show first line or truncated preview
        if b.bug_steps:
            steps_lines = b.bug_steps.split("\n")
            first_line = steps_lines[0].strip()
            # Truncate if too long
            if len(first_line) > 40:
                steps_preview = first_line[:37] + "..."
            else:
                steps_preview = first_line
            # Add indicator if there are more lines
            if len(steps_lines) > 1:
                steps_preview += f" (+{len(steps_lines) - 1} more)"
            steps_text = Text(steps_preview, style="cyan")
        else:
            steps_text = Text("—", style="dim")

        bug_text = _format_task_text(b.text or "", b.done, b.priority)

        table.add_row(
            bug_id,
            bug_status,
            bug_severity,
            assignee,
            env,
            priority,
            steps_text,
            bug_text,
        )

    console.print()
    console.print(table)
    console.print()


def render_bug_detail(bug: Task) -> None:
    """Render detailed bug information in a panel."""
    console = Console()

    # Build detailed bug info
    info_lines = []

    info_lines.append(("ID", f"#{bug.id}"))
    info_lines.append(("Description", bug.text or ""))
    info_lines.append(("Status", bug.bug_status or "open"))
    info_lines.append(("Severity", bug.bug_severity or "—"))
    info_lines.append(("Assignee", bug.bug_assignee or "—"))
    info_lines.append(("Environment", bug.bug_environment or "—"))
    info_lines.append(("Priority", bug.priority or "—"))
    info_lines.append(("Due Date", bug.due or "—"))
    info_lines.append(("Tags", ", ".join(bug.tags or []) if bug.tags else "—"))
    if bug.bug_steps:
        info_lines.append(("Steps to Reproduce", bug.bug_steps))
    info_lines.append(("Created", bug.created_at or "—"))
    if bug.done:
        info_lines.append(("Done", bug.done_at or "—"))

    # Create formatted text
    content = Text()
    for label, value in info_lines:
        if not value or value == "—":
            continue
        content.append(f"{label}: ", style="bold cyan")
        if label == "Severity":
            content.append(_format_bug_severity(value))
        elif label == "Status":
            content.append(_format_bug_status(value))
        elif label == "Priority":
            content.append(_format_priority(value))
        elif label == "Due Date":
            content.append(_format_due(value))
        elif label == "Tags":
            content.append(_format_tags(bug.tags or []))
        else:
            content.append(str(value), style="white")
        content.append("\n")

    console.print()
    console.print(
        Panel(
            content,
            title=f"[bold red]🐛 Bug #{bug.id}[/bold red]",
            border_style="red",
            padding=(1, 2),
        )
    )
    console.print()
