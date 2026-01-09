from __future__ import annotations
import os, datetime as dt
from pathlib import Path
from typing import Optional, Tuple
from .config import AppConfig, load_config_with_base_dir, save_config, save_install_config
from .paths import default_db_path
from .storage import FileLock, load_db, save_db, archive_path_for_db


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def resolve_db_path(cli_db: str = "") -> Path:
    if cli_db:
        return Path(cli_db).expanduser()
    env = os.environ.get("TODO_DB", "").strip()
    if env:
        return Path(env).expanduser()
    cfg, base_dir = load_config_with_base_dir()
    if cfg.db_path:
        p = Path(cfg.db_path).expanduser()
        # If config stores a relative path, resolve it relative to config directory
        if not p.is_absolute():
            p = (base_dir / p).expanduser()
        return p
    return default_db_path()


def init_config(
    db: Optional[str], dir_: Optional[str], force: bool = False
) -> Tuple[Path, Path]:
    # Historical return value: config_path() used to be returned here.
    # With install-config support, the actual config file could be either local or global.
    # Callers only use this for display, so we keep returning the global config_path().
    from .paths import config_path

    cfg_p = config_path()
    cfg, base_dir = load_config_with_base_dir()

    # Save config (only overwrite if empty or force)
    if (cfg.db_path and not force) and not (db or dir_):
        # Nothing specified and already set; keep existing configured path.
        p = Path(cfg.db_path).expanduser()
        if not p.is_absolute():
            p = (base_dir / p).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(p.with_suffix(".lock")):
            if not p.exists():
                save_db(p, {"version": 1, "next_id": 1, "tasks": []})
            else:
                # Load validates the file; load_db handles corrupted files gracefully
                _ = load_db(p)
        ap = archive_path_for_db(p)
        with FileLock(ap.with_suffix(".lock")):
            if not ap.exists():
                save_db(ap, {"version": 1, "next_id": 1, "tasks": []})
            else:
                _ = load_db(ap)
        return cfg_p, p

    if cfg.db_path and not force and (db or dir_):
        # User is trying to change without force: keep existing configured path, ensure it exists.
        p = Path(cfg.db_path).expanduser()
        if not p.is_absolute():
            p = (base_dir / p).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(p.with_suffix(".lock")):
            if not p.exists():
                save_db(p, {"version": 1, "next_id": 1, "tasks": []})
            else:
                # Load validates the file; load_db handles corrupted files gracefully
                _ = load_db(p)
        ap = archive_path_for_db(p)
        with FileLock(ap.with_suffix(".lock")):
            if not ap.exists():
                save_db(ap, {"version": 1, "next_id": 1, "tasks": []})
            else:
                _ = load_db(ap)
        return cfg_p, p

    # Determine db path (new/overwrite)
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
            # Load validates the file; load_db handles corrupted files gracefully
            _ = load_db(db_path)

    # Ensure archive file exists next to the DB (so deletes/archives are recoverable)
    archive_path = archive_path_for_db(db_path)
    with FileLock(archive_path.with_suffix(".lock")):
        if not archive_path.exists():
            save_db(archive_path, {"version": 1, "next_id": 1, "tasks": []})
        else:
            _ = load_db(archive_path)

    now = now_iso()
    if not cfg.created_at:
        cfg.created_at = now
    cfg.updated_at = now
    cfg.db_path = str(db_path)
    # Prefer per-install config (best-effort), and always keep global config updated too.
    _ = save_install_config(cfg)
    save_config(cfg)
    return cfg_p, db_path
