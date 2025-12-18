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
