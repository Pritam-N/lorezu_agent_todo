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


def _format_status(done: bool) -> Text:
    """Format status with modern indicators"""
    if done:
        return Text("✓", style="bold green")
    return Text("○", style="bright_black")


def _format_priority(priority: str) -> Text:
    """Format priority with modern badges"""
    pri = (priority or "").lower()
    if pri == "high":
        return Text("HIGH", style="bold white on red")
    elif pri == "med":
        return Text("MED", style="bold black on yellow")
    elif pri == "low":
        return Text("LOW", style="bold white on blue")
    return Text("—", style="dim")


def _format_due(due_str: str) -> Text:
    """Format due date with relative time and urgency indicators"""
    if not due_str:
        return Text("—", style="dim")
    try:
        due_date = date.fromisoformat(due_str)
        today = date.today()
        days_until = (due_date - today).days

        if days_until < 0:
            overdue_days = abs(days_until)
            return Text(f"⚠️  {due_str} ({overdue_days}d overdue)", style="bold red")
        elif days_until == 0:
            return Text(f"🔥 Today", style="bold yellow")
        elif days_until == 1:
            return Text(f"⏰ Tomorrow", style="yellow")
        elif days_until <= 3:
            return Text(f"⏰ {due_str} ({days_until}d)", style="yellow")
        elif days_until <= 7:
            return Text(f"📅 {due_str} ({days_until}d)", style="cyan")
        else:
            return Text(f"📅 {due_str}", style="bright_cyan")
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
