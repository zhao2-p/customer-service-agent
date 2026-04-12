from pathlib import Path


# 集中维护项目里的几个关键目录，避免到处手写相对路径。
BACKEND_APP_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BACKEND_APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent


def get_project_root() -> str:
    return str(PROJECT_ROOT)


def get_abs_path(relative_path: str) -> str:
    # 配置文件里一般保存相对项目根目录的路径，这里负责转成绝对路径。
    return str(PROJECT_ROOT / relative_path)
