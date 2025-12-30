from __future__ import annotations
import json, os, tempfile
import datetime as dt
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple
from .model import Task

VERSION = 1
PRIORITY_ORDER = {"high": 0, "med": 1, "low": 2, "": 3, None: 3}
BACKUP_KEEP_DEFAULT = 5


def migrate_db_data(db: Dict[str, Any]) -> Tuple[Dict[str, Any], int, int, List[str]]:
    """
    Migrate an in-memory DB dict to the current schema version.

    Returns: (migrated_db, from_version, to_version, notes)
    """
    notes: List[str] = []
    raw_v = db.get("version", VERSION)
    try:
        from_v = int(raw_v)
    except Exception:
        from_v = VERSION
        notes.append(f"Coerced invalid version {raw_v!r} -> {from_v}")

    if from_v > VERSION:
        raise ValueError(
            f"DB version {from_v} is newer than supported version {VERSION}"
        )

    # Current schema (v1) normalization
    db.setdefault("tasks", [])
    db.setdefault("next_id", 1)
    if not isinstance(db.get("tasks"), list):
        db["tasks"] = []
        notes.append("Reset tasks to empty list (invalid type)")
    try:
        db["next_id"] = int(db.get("next_id", 1))
    except Exception:
        db["next_id"] = 1
        notes.append("Reset next_id to 1 (invalid type)")

    if db.get("version") != VERSION:
        db["version"] = VERSION
        notes.append(f"Set version to {VERSION}")

    return db, from_v, VERSION, notes


def ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def atomic_write_json(path: Path, obj: Any) -> None:
    ensure_parent(path)
    data = json.dumps(obj, indent=2, ensure_ascii=False)
    with tempfile.NamedTemporaryFile(
        "w", delete=False, dir=str(path.parent), encoding="utf-8"
    ) as tf:
        tf.write(data)
        tf.flush()
        os.fsync(tf.fileno())
        tmp = tf.name
    os.replace(tmp, path)


def backup_paths(db_path: Path, keep: int = BACKUP_KEEP_DEFAULT) -> List[Path]:
    """Return backup paths in order [1..keep]."""
    keep = max(0, int(keep))
    return [db_path.with_name(f"{db_path.name}.{i}") for i in range(1, keep + 1)]


def rotate_backups(db_path: Path, keep: int = BACKUP_KEEP_DEFAULT) -> None:
    """Rotate backups like todos.json.1, todos.json.2 ... (best-effort)."""
    keep = max(0, int(keep))
    if keep <= 0:
        return
    if not db_path.exists():
        return

    # Shift older backups up
    for i in range(keep, 1, -1):
        src = db_path.with_name(f"{db_path.name}.{i - 1}")
        dst = db_path.with_name(f"{db_path.name}.{i}")
        if src.exists():
            try:
                os.replace(src, dst)
            except Exception:
                pass

    # Copy current to .1
    dst1 = db_path.with_name(f"{db_path.name}.1")
    try:
        shutil.copy2(db_path, dst1)
    except Exception:
        pass


def restore_latest_backup(db_path: Path, keep: int = BACKUP_KEEP_DEFAULT) -> bool:
    """Restore the newest available backup into db_path. Returns True if restored."""
    for p in backup_paths(db_path, keep=keep):
        if p.exists():
            try:
                shutil.copy2(p, db_path)
                return True
            except Exception:
                return False
    return False


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
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                # Empty file - return default
                return {"version": VERSION, "next_id": 1, "tasks": []}
            data = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        # Corrupted JSON - return default
        return {"version": VERSION, "next_id": 1, "tasks": []}
    data.setdefault("version", VERSION)
    data.setdefault("next_id", 1)
    data.setdefault("tasks", [])
    return data


def save_db(db_path: Path, data: Dict[str, Any]) -> None:
    # Backup current DB before write
    rotate_backups(db_path, keep=BACKUP_KEEP_DEFAULT)
    atomic_write_json(db_path, data)


def archive_path_for_db(db_path: Path) -> Path:
    """Default archive path lives next to the main DB."""
    # Keep archive adjacent to the active DB file, so switching DB path also switches archive location.
    # NOTE: filename uses user's requested spelling.
    return db_path.with_name("todos-archieved.json")


def append_tasks_to_archive(archive_path: Path, tasks: List[Task]) -> int:
    """Append tasks to archive DB (creates archive if missing). Returns count appended."""
    if not tasks:
        return 0
    adb = load_db(archive_path)
    existing = list(adb.get("tasks") or [])
    existing.extend([t.to_dict() for t in tasks])
    adb["tasks"] = existing
    # Keep next_id reasonable for potential future use
    try:
        max_id = max(int(t.get("id", 0)) for t in existing) if existing else 0
    except Exception:
        max_id = 0
    adb["next_id"] = max(int(adb.get("next_id", 1)), max_id + 1)
    save_db(archive_path, adb)
    return len(tasks)


def load_tasks(db_path: Path) -> Tuple[int, List[Task]]:
    db = load_db(db_path)
    next_id = int(db.get("next_id", 1))
    tasks = [Task.from_dict(t) for t in (db.get("tasks") or [])]
    return next_id, tasks


def save_tasks(db_path: Path, next_id: int, tasks: List[Task]) -> None:
    save_db(
        db_path,
        {
            "version": VERSION,
            "next_id": int(next_id),
            "tasks": [t.to_dict() for t in tasks],
        },
    )


def sort_tasks(tasks: List[Task], sort: str) -> List[Task]:
    sort = (sort or "created").lower()
    if sort == "due":

        def due_key(t: Task):
            # Bucket: 0 = overdue, 1 = has due date (today/future), 2 = no/invalid due date
            due_s = (t.due or "").strip()
            if not due_s:
                return (2, 10**9, PRIORITY_ORDER.get(t.priority, 3), t.id)
            try:
                days_until = (dt.date.fromisoformat(due_s) - dt.date.today()).days
            except ValueError:
                return (2, 10**9, PRIORITY_ORDER.get(t.priority, 3), t.id)
            bucket = 0 if days_until < 0 else 1
            return (bucket, days_until, PRIORITY_ORDER.get(t.priority, 3), t.id)

        return sorted(tasks, key=due_key)
    if sort == "priority":
        return sorted(
            tasks,
            key=lambda t: (
                PRIORITY_ORDER.get(t.priority, 3),
                t.due or "9999-12-31",
                t.id,
            ),
        )
    return sorted(tasks, key=lambda t: (t.created_at or "", t.id))
