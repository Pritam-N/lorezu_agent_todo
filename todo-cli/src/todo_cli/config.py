from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from .paths import config_path

@dataclass
class AppConfig:
    db_path: str = ""
    backups_dir: str = ""
    created_at: str = ""
    updated_at: str = ""

def _ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)

def load_config() -> AppConfig:
    p = config_path()
    if not p.exists():
        return AppConfig()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return AppConfig()
    return AppConfig(
        db_path=str(data.get("db_path", "")),
        backups_dir=str(data.get("backups_dir", "")),
        created_at=str(data.get("created_at", "")),
        updated_at=str(data.get("updated_at", "")),
    )

def save_config(cfg: AppConfig) -> None:
    p = config_path()
    _ensure_parent(p)
    p.write_text(json.dumps({
        "db_path": cfg.db_path,
        "backups_dir": cfg.backups_dir,
        "created_at": cfg.created_at,
        "updated_at": cfg.updated_at,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
