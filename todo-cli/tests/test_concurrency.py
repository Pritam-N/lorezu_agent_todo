import multiprocessing as mp
from pathlib import Path
import tempfile


def _worker(db_path_str: str, n: int) -> None:
    # Import inside worker for multiprocessing pickling friendliness
    from todo_cli.storage import FileLock, load_tasks, save_tasks
    from todo_cli.model import Task
    from todo_cli.housekeeping import now_iso

    db_path = Path(db_path_str)
    for _ in range(n):
        with FileLock(db_path.with_suffix(".lock")):
            next_id, tasks = load_tasks(db_path)
            tasks.append(
                Task(
                    id=next_id,
                    text="concurrency test",
                    done=False,
                    created_at=now_iso(),
                    priority="",
                    due="",
                    tags=[],
                )
            )
            save_tasks(db_path, next_id + 1, tasks)


def test_concurrent_writes_do_not_corrupt_db():
    # This is a smoke test to ensure FileLock + atomic writes keep JSON valid
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "todos.json"

        procs = [
            mp.Process(target=_worker, args=(str(db_path), 25)),
            mp.Process(target=_worker, args=(str(db_path), 25)),
        ]
        for p in procs:
            p.start()
        for p in procs:
            p.join(timeout=30)

        for p in procs:
            assert p.exitcode == 0

        from todo_cli.storage import load_db

        db = load_db(db_path)
        tasks = db.get("tasks") or []
        ids = [int(t.get("id")) for t in tasks]
        assert len(ids) == 50
        assert len(set(ids)) == 50
