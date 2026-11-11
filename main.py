"""Run Fake-Compression from a source checkout."""
import sys
from pathlib import Path

# 判断当前是否运行在 PyInstaller 环境
if getattr(sys, "frozen", False):
    # 打包后的程序
    PROJECT_ROOT = Path(sys.executable).resolve().parent
else:
    # 源码运行
    PROJECT_ROOT = Path(__file__).resolve().parent
    SRC_DIR = PROJECT_ROOT / "src"

    if SRC_DIR.is_dir():
        sys.path.insert(0, str(SRC_DIR))
    else:
        raise FileNotFoundError(
            f"找不到项目源码目录：{SRC_DIR}"
        )

from fake_compression.app import main


if __name__ == "__main__":
    main()