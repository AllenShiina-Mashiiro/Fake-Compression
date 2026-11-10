"""Path validation for archive members before extraction."""
from pathlib import PurePosixPath, PureWindowsPath


_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def validate_archive_paths(paths: list[str]) -> None:
    """Reject traversal and names that cannot be represented safely on Windows."""
    seen = set()
    for raw in paths:
        if not raw or "\x00" in raw:
            raise ValueError("压缩包包含空文件名或无效字符。")

        normalized = raw.replace("\\", "/")
        posix = PurePosixPath(normalized)
        windows = PureWindowsPath(raw)
        if posix.is_absolute() or windows.is_absolute() or windows.drive or windows.root:
            raise ValueError(f"压缩包包含绝对路径：{raw}")
        parts = [part for part in posix.parts if part not in ("", ".")]
        if not parts or any(part == ".." for part in parts):
            raise ValueError(f"压缩包包含目录穿越路径：{raw}")

        key = "/".join(parts).casefold()
        if key in seen:
            raise ValueError(f"压缩包包含重复或大小写冲突的路径：{raw}")
        seen.add(key)

        for part in parts:
            if ":" in part or part.endswith((".", " ")):
                raise ValueError(f"压缩包包含不安全的 Windows 文件名：{raw}")
            device_name = part.split(".", 1)[0].upper()
            if device_name in _WINDOWS_RESERVED:
                raise ValueError(f"压缩包包含 Windows 保留设备名：{raw}")


def validate_package_name(name: str) -> None:
    """Validate a package stem as a portable Windows file name."""
    if not name or name in (".", "..") or len(name) > 180:
        raise ValueError("包名称不能为空，且长度不能超过 180 个字符。")
    if any(char in '<>:"/\\|?*' for char in name) or name.endswith((".", " ")):
        raise ValueError("包名称包含 Windows 不允许的字符。")
    if name.split(".", 1)[0].upper() in _WINDOWS_RESERVED:
        raise ValueError("包名称不能使用 Windows 保留设备名。")
