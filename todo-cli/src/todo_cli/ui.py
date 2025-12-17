from __future__ import annotations
from typing import List, Sequence, Tuple
from prompt_toolkit.shortcuts import checkboxlist_dialog
from datetime import date
from .model import Task


def _format_task_for_picker(t: Task) -> str:
    """Format a task for the picker dialog with colors and emojis"""
    status = "✓" if t.done else "○"

    # Priority indicator
    pri_str = ""
    if t.priority:
        pri = t.priority.lower()
        if pri == "high":
            pri_str = " 🔴 HIGH"
        elif pri == "med":
            pri_str = " 🟡 MED"
        elif pri == "low":
            pri_str = " 🔵 LOW"

    # Due date indicator
    due_str = ""
    if t.due:
        try:
            due_date = date.fromisoformat(t.due)
            today = date.today()
            days_until = (due_date - today).days
            if days_until < 0:
                due_str = f" ⚠️  {t.due} (overdue)"
            elif days_until == 0:
                due_str = f" 🔥 {t.due} (today)"
            elif days_until <= 3:
                due_str = f" ⏰ {t.due} (soon)"
            else:
                due_str = f" 📅 {t.due}"
        except (ValueError, TypeError):
            due_str = f" 📅 {t.due}"

    # Tags
    tags_str = ""
    if t.tags:
        tags_str = "  #" + " #".join(t.tags)

    # Combine parts
    parts = [f"[{status}]", f"#{t.id:>3}", t.text]
    if pri_str:
        parts.append(pri_str)
    if due_str:
        parts.append(due_str)
    if tags_str:
        parts.append(tags_str)

    return "  ".join(parts)


def pick_tasks_to_done(tasks: Sequence[Task]) -> List[int]:
    values: List[Tuple[int, str]] = []
    for t in tasks:
        formatted = _format_task_for_picker(t)
        values.append((t.id, formatted))
    if not values:
        return []
    result = checkboxlist_dialog(
        title="✨ Mark Tasks as Done",
        text="Use ↑/↓ to navigate, Space to toggle, Enter to confirm, Esc to cancel.",
        values=values,
        ok_text="✅ Done",
        cancel_text="❌ Cancel",
    ).run()
    return list(result or [])
