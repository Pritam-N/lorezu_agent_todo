from __future__ import annotations
import os, sys
from pathlib import Path

APP_NAME = "todo-cli"

def home() -> Path:
    return Path.home()

def config_dir() -> Path:
    if os.name == "nt":
        appdata = os.environ.get("APPDATA") or str(home() / "AppData" / "Roaming")
        return Path(appdata) / APP_NAME
    if sys.platform == "darwin":
        return home() / "Library" / "Application Support" / APP_NAME
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / APP_NAME
    return home() / ".config" / APP_NAME

def config_path() -> Path:
    return config_dir() / "config.json"

def default_db_path() -> Path:
    docs = home() / "Documents"
    if docs.exists():
        return docs / "todo-cli" / "todos.json"
    return home() / ".todo-cli" / "todos.json"
