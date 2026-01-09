from __future__ import annotations
import os, sys
from pathlib import Path

APP_NAME = "todo-cli"
INSTALL_CONFIG_ENV = "TODO_CLI_INSTALL_CONFIG"

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

def install_dir() -> Path:
    """
    Directory where the Python package is installed from.

    This is used for an optional per-install local config file, so multiple
    installs (editable installs, different venvs, etc.) can keep separate config.
    """
    return Path(__file__).resolve().parent

def install_config_path() -> Path:
    """
    Per-install config path (higher priority than user config_dir()).

    Can be overridden for testing via TODO_CLI_INSTALL_CONFIG.
    """
    override = os.environ.get(INSTALL_CONFIG_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    return install_dir() / "install-config.json"

def default_db_path() -> Path:
    docs = home() / "Documents"
    if docs.exists():
        return docs / "todo-cli" / "todos.json"
    return home() / ".todo-cli" / "todos.json"
