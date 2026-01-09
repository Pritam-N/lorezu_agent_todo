import json
import os
from pathlib import Path
import tempfile


def test_resolve_db_path_precedence_cli_env_config_default():
    # Ensure we don't depend on the real user's home dir
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        old_home = os.environ.get("HOME", "")
        old_todo_db = os.environ.get("TODO_DB", "")
        try:
            os.environ["HOME"] = td

            from todo_cli.paths import config_path, default_db_path
            from todo_cli.housekeeping import resolve_db_path

            # Config file with relative db_path should resolve relative to config dir
            cfg_p = config_path()
            cfg_p.parent.mkdir(parents=True, exist_ok=True)
            cfg_p.write_text(
                json.dumps({"db_path": "todos.json"}, indent=2),
                encoding="utf-8",
            )

            resolved_from_config = resolve_db_path("")
            assert resolved_from_config == cfg_p.parent / "todos.json"

            # Env var overrides config
            os.environ["TODO_DB"] = str(td_path / "env.json")
            assert resolve_db_path("") == td_path / "env.json"

            # CLI arg overrides env
            assert resolve_db_path(str(td_path / "cli.json")) == td_path / "cli.json"

            # If both env and config absent, fallback to default
            os.environ["TODO_DB"] = ""
            cfg_p.unlink()
            assert resolve_db_path("") == default_db_path()
        finally:
            if old_home:
                os.environ["HOME"] = old_home
            else:
                os.environ.pop("HOME", None)
            if old_todo_db:
                os.environ["TODO_DB"] = old_todo_db
            else:
                os.environ.pop("TODO_DB", None)


def test_save_config_uses_per_install_mapping():
    with tempfile.TemporaryDirectory() as td:
        old_home = os.environ.get("HOME", "")
        try:
            os.environ["HOME"] = td

            from todo_cli.config import load_config, save_config
            from todo_cli.paths import config_path

            cfg = load_config()
            cfg.db_path = "todos.json"
            save_config(cfg)

            raw = json.loads(config_path().read_text(encoding="utf-8"))
            assert raw.get("schema_version") == 2
            assert isinstance(raw.get("installs"), dict)
            assert len(raw["installs"].keys()) >= 1
        finally:
            if old_home:
                os.environ["HOME"] = old_home
            else:
                os.environ.pop("HOME", None)


def test_install_config_has_priority_over_global_config():
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        old_home = os.environ.get("HOME", "")
        old_install_cfg = os.environ.get("TODO_CLI_INSTALL_CONFIG", "")
        try:
            os.environ["HOME"] = td
            os.environ["TODO_CLI_INSTALL_CONFIG"] = str(td_path / "install-config.json")

            from todo_cli.paths import config_path
            from todo_cli.housekeeping import resolve_db_path

            # Global config points to global.json
            cfg_p = config_path()
            cfg_p.parent.mkdir(parents=True, exist_ok=True)
            cfg_p.write_text(
                json.dumps({"db_path": str(td_path / "global.json")}, indent=2),
                encoding="utf-8",
            )

            # Install config points to install.json (should win)
            Path(os.environ["TODO_CLI_INSTALL_CONFIG"]).write_text(
                json.dumps({"db_path": str(td_path / "install.json")}, indent=2),
                encoding="utf-8",
            )

            assert resolve_db_path("") == td_path / "install.json"
        finally:
            if old_home:
                os.environ["HOME"] = old_home
            else:
                os.environ.pop("HOME", None)
            if old_install_cfg:
                os.environ["TODO_CLI_INSTALL_CONFIG"] = old_install_cfg
            else:
                os.environ.pop("TODO_CLI_INSTALL_CONFIG", None)
