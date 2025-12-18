from pathlib import Path
import tempfile


def test_save_creates_backup_on_second_write():
    from todo_cli.storage import save_db

    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "todos.json"
        save_db(db_path, {"version": 1, "next_id": 1, "tasks": []})
        save_db(db_path, {"version": 1, "next_id": 2, "tasks": []})

        assert (db_path.with_name(db_path.name + ".1")).exists()


def test_sort_due_overdue_first_then_upcoming_then_none():
    from todo_cli.model import Task
    from todo_cli.storage import sort_tasks

    tasks = [
        Task(id=1, text="no due", due="", done=False),
        Task(id=2, text="tomorrow", due="2099-01-02", done=False),
        Task(id=3, text="overdue", due="2000-01-01", done=False),
    ]

    out = sort_tasks(tasks, "due")
    assert out[0].id == 3  # overdue first
    assert out[1].id == 2  # upcoming next
    assert out[2].id == 1  # no due last
