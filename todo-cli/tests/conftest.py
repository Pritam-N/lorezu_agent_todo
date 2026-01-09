import os
import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    """
    Tests in this repo are often run from the repo root without installing the
    package. Since `todo-cli` uses a `src/` layout, we bootstrap the module path
    here so `import todo_cli` works.

    We also set PYTHONPATH so multiprocessing spawn children can import too.
    """
    tests_dir = Path(__file__).resolve().parent
    pkg_src = (tests_dir.parent / "src").resolve()
    pkg_src_s = str(pkg_src)

    # For the current Python process
    if pkg_src_s not in sys.path:
        sys.path.insert(0, pkg_src_s)

    # For spawned subprocesses (macOS default start method is spawn)
    existing = os.environ.get("PYTHONPATH", "")
    parts = [p for p in existing.split(os.pathsep) if p]
    if pkg_src_s not in parts:
        os.environ["PYTHONPATH"] = os.pathsep.join([pkg_src_s, *parts]) if parts else pkg_src_s


_ensure_src_on_path()

