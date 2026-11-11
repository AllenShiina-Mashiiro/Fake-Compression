
"""Run Fake-Compression from a source checkout or PyInstaller bundle."""

import sys
from pathlib import Path


# 源码运行时，将 src 加入 Python 搜索路径
if not getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(__file__).resolve().parent
    SRC_DIR = PROJECT_ROOT / "src"

    if not SRC_DIR.is_dir():
        raise FileNotFoundError(f"找不到项目源码目录：{SRC_DIR}")

    sys.path.insert(0, str(SRC_DIR))

from fake_compression.app import main


if __name__ == "__main__":
    main()
