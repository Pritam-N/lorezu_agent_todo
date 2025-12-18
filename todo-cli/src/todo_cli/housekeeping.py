from __future__ import annotations
import os, datetime as dt
from pathlib import Path
from typing import Optional, Tuple
from .config import AppConfig, load_config, save_config
from .paths import config_path, default_db_path
from .storage import FileLock, load_db, save_db


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def resolve_db_path(cli_db: str = "") -> Path:
    if cli_db:
        return Path(cli_db).expanduser()
    env = os.environ.get("TODO_DB", "").strip()
    if env:
        return Path(env).expanduser()
    cfg = load_config()
    if cfg.db_path:
        p = Path(cfg.db_path).expanduser()
        # If config stores a relative path, resolve it relative to config directory
        if not p.is_absolute():
            p = (config_path().parent / p).expanduser()
        return p
    return default_db_path()


def init_config(
    db: Optional[str], dir_: Optional[str], force: bool = False
) -> Tuple[Path, Path]:
    cfg_p = config_path()
    cfg = load_config()

    # Determine db path
    if dir_ and not db:
        db_path = Path(dir_).expanduser() / "todos.json"
    elif db:
        db_path = Path(db).expanduser()
    else:
        db_path = default_db_path()

    db_path.parent.mkdir(parents=True, exist_ok=True)

    with FileLock(db_path.with_suffix(".lock")):
        if not db_path.exists():
            save_db(db_path, {"version": 1, "next_id": 1, "tasks": []})
        else:
            _ = load_db(db_path)

    # Save config (only overwrite if empty or force)
    if (cfg.db_path and not force) and not (db or dir_):
        # nothing specified and already set; keep
        return cfg_p, Path(cfg.db_path).expanduser()

    if cfg.db_path and not force and (db or dir_):
        # user is trying to change without force: keep existing but still ensure target exists
        return cfg_p, Path(cfg.db_path).expanduser()

    now = now_iso()
    if not cfg.created_at:
        cfg.created_at = now
    cfg.updated_at = now
    cfg.db_path = str(db_path)
    save_config(cfg)
    return cfg_p, db_path
