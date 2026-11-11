"""Input sizing and volume policy."""
from dataclasses import dataclass
from pathlib import Path

GIB = 1024 ** 3


@dataclass(frozen=True)
class SizePlan:
    total_bytes: int
    volume_bytes: int | None

    @property
    def split(self) -> bool:
        return self.volume_bytes is not None


def calculate_size(source: str | Path) -> int:
    path = Path(source)
    if path.is_symlink():
        raise ValueError("Symbolic links are not accepted as input roots.")
    if path.is_file():
        return path.stat().st_size
    if not path.is_dir():
        raise FileNotFoundError(path)

    total = 0
    for item in path.rglob("*"):
        if item.is_symlink():
            raise ValueError(f"Input folder contains a symbolic link: {item}")
        if item.is_file():
            total += item.stat().st_size
    return total


def plan_volumes(total_bytes: int) -> SizePlan:
    if total_bytes < 0:
        raise ValueError("total_bytes cannot be negative")
    if total_bytes <= GIB:
        volume = None
    elif total_bytes <= 5 * GIB:
        volume = 2 * GIB
    else:
        volume = 4 * GIB
    return SizePlan(total_bytes, volume)


def inspect_source(source: str | Path) -> SizePlan:
    return plan_volumes(calculate_size(source))
