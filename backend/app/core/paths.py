from pathlib import Path


# `backend/app/core/paths.py` 位于 `backend/app/core` 下，
# 因此项目根目录需要从当前文件回退 3 层。
BACKEND_APP_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BACKEND_APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent


def get_project_root() -> str:
    return str(PROJECT_ROOT)


def get_abs_path(relative_path: str) -> str:
    return str(PROJECT_ROOT / relative_path)
