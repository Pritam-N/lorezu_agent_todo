from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple
from .model import Task

VERSION = 1
PRIORITY_ORDER = {"high": 0, "med": 1, "low": 2, "": 3, None: 3}

def ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)

def atomic_write_json(path: Path, obj: Any) -> None:
    ensure_parent(path)
    data = json.dumps(obj, indent=2, ensure_ascii=False)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent), encoding="utf-8") as tf:
        tf.write(data)
        tf.flush()
        os.fsync(tf.fileno())
        tmp = tf.name
    os.replace(tmp, path)

class FileLock:
    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self.fp = None
    def __enter__(self):
        ensure_parent(self.lock_path)
        self.fp = open(self.lock_path, "a+", encoding="utf-8")
        try:
            if os.name == "nt":
                import msvcrt  # type: ignore
                msvcrt.locking(self.fp.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl  # type: ignore
                fcntl.flock(self.fp.fileno(), fcntl.LOCK_EX)
        except Exception:
            pass
        return self
    def __exit__(self, exc_type, exc, tb):
        try:
            if self.fp:
                if os.name == "nt":
                    import msvcrt  # type: ignore
                    msvcrt.locking(self.fp.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl  # type: ignore
                    fcntl.flock(self.fp.fileno(), fcntl.LOCK_UN)
                self.fp.close()
        except Exception:
            pass

def load_db(db_path: Path) -> Dict[str, Any]:
    if not db_path.exists():
        return {"version": VERSION, "next_id": 1, "tasks": []}
    with open(db_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("version", VERSION)
    data.setdefault("next_id", 1)
    data.setdefault("tasks", [])
    return data

def save_db(db_path: Path, data: Dict[str, Any]) -> None:
    atomic_write_json(db_path, data)

def load_tasks(db_path: Path) -> Tuple[int, List[Task]]:
    db = load_db(db_path)
    next_id = int(db.get("next_id", 1))
    tasks = [Task.from_dict(t) for t in (db.get("tasks") or [])]
    return next_id, tasks

def save_tasks(db_path: Path, next_id: int, tasks: List[Task]) -> None:
    save_db(db_path, {"version": VERSION, "next_id": int(next_id), "tasks": [t.to_dict() for t in tasks]})

def sort_tasks(tasks: List[Task], sort: str) -> List[Task]:
    sort = (sort or "created").lower()
    if sort == "due":
        return sorted(tasks, key=lambda t: (t.due or "9999-12-31", PRIORITY_ORDER.get(t.priority, 3), t.id))
    if sort == "priority":
        return sorted(tasks, key=lambda t: (PRIORITY_ORDER.get(t.priority, 3), t.due or "9999-12-31", t.id))
    return sorted(tasks, key=lambda t: (t.created_at or "", t.id))
