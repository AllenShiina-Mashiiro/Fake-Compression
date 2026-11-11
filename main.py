"""Run Fake-Compression from a source checkout."""
import sys
from pathlib import Path

# 获取项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent

# 添加 src 到 Python 模块搜索路径
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