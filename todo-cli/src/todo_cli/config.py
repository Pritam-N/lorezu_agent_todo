from __future__ import annotations
import os
import json
from dataclasses import dataclass
from pathlib import Path
from .paths import config_path, install_config_path

# Config schema:
# - Legacy (v1): { "db_path": "...", "backups_dir": "...", ... }
# - Multi-install (v2):
#   {
#     "schema_version": 2,
#     "installs": {
#        "<install_id>": { "db_path": "...", "backups_dir": "...", ... }
#     }
#   }
SCHEMA_VERSION = 2


@dataclass
class AppConfig:
    db_path: str = ""
    backups_dir: str = ""
    created_at: str = ""
    updated_at: str = ""


def install_id() -> str:
    """
    Identifier for "where todo is installed" so separate installs don't stomp each
    other's config.

    We use the resolved package directory path, which is unique per editable
    install / venv / site-packages location.
    """
    p = Path(__file__).resolve().parent  # .../todo_cli
    s = str(p)
    # On Windows, normalize casing so the same directory maps consistently.
    if os.name == "nt":
        s = os.path.normcase(s)
    return s


def _ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def _coerce_cfg(data: dict) -> AppConfig:
    return AppConfig(
        db_path=str(data.get("db_path", "")),
        backups_dir=str(data.get("backups_dir", "")),
        created_at=str(data.get("created_at", "")),
        updated_at=str(data.get("updated_at", "")),
    )


def _read_json(p: Path) -> dict | None:
    try:
        if not p.exists():
            return None
        raw = json.loads(p.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None
    except Exception:
        return None


def load_config_with_base_dir() -> tuple[AppConfig, Path]:
    """
    Load config with knowledge of the directory to resolve relative db_path.

    Priority:
    1) install_config_path() (per-install, local)
    2) config_path() (global per-user file, v2 installs map or legacy v1)
    """
    install_p = install_config_path()
    install_data = _read_json(install_p)
    if install_data is not None:
        # install-config can be either:
        # - v1: { db_path: ... }
        # - v2: { schema_version: 2, installs: { <install_id>: { db_path: ... } } }
        try:
            if int(
                install_data.get("schema_version", 0)
            ) >= SCHEMA_VERSION and isinstance(install_data.get("installs"), dict):
                entry = (install_data.get("installs") or {}).get(install_id()) or {}
                if isinstance(entry, dict):
                    return _coerce_cfg(entry), install_p.parent
        except Exception:
            pass
        return _coerce_cfg(install_data), install_p.parent

    global_p = config_path()
    data = _read_json(global_p)
    if data is None:
        return AppConfig(), global_p.parent

    # v2: per-install mapping
    try:
        if int(data.get("schema_version", 0)) >= SCHEMA_VERSION and isinstance(
            data.get("installs"), dict
        ):
            entry = (data.get("installs") or {}).get(install_id()) or {}
            if isinstance(entry, dict):
                return _coerce_cfg(entry), global_p.parent
            return AppConfig(), global_p.parent
    except Exception:
        pass

    # v1 (legacy): single shared config
    return _coerce_cfg(data), global_p.parent


def load_config() -> AppConfig:
    cfg, _base = load_config_with_base_dir()
    return cfg


def save_install_config(cfg: AppConfig) -> bool:
    """
    Best-effort write of per-install config at install_config_path().
    Returns True if write succeeds.
    """
    p = install_config_path()
    try:
        _ensure_parent(p)
        p.write_text(
            json.dumps(
                {
                    "db_path": cfg.db_path,
                    "backups_dir": cfg.backups_dir,
                    "created_at": cfg.created_at,
                    "updated_at": cfg.updated_at,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return True
    except Exception:
        return False


def save_config(cfg: AppConfig) -> None:
    p = config_path()
    _ensure_parent(p)

    # Merge with existing file (preserve other installs)
    base: dict = {}
    if p.exists():
        try:
            base = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            base = {}
    if not isinstance(base, dict):
        base = {}

    installs = base.get("installs")
    if not isinstance(installs, dict):
        installs = {}

    installs[install_id()] = {
        "db_path": cfg.db_path,
        "backups_dir": cfg.backups_dir,
        "created_at": cfg.created_at,
        "updated_at": cfg.updated_at,
    }

    out = {
        "schema_version": SCHEMA_VERSION,
        "installs": installs,
    }

    p.write_text(
        json.dumps(out, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
