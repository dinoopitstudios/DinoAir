# Root-level pytest configuration helpers applied to all tests
# - Ensure 'DinoAir3.0' is importable so tests can `from models...` and `from database...`
# - Keep deterministic defaults (can add seeds here if randomness is used)

from pathlib import Path
import sys


def _add_repo_src_to_sys_path() -> None:
    repo_root = Path(__file__).resolve().parent
    project_src = repo_root / "DinoAir3.0"
    if str(project_src) not in sys.path:
        sys.path.insert(0, str(project_src))


_add_repo_src_to_sys_path()
