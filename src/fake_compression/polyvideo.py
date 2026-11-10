"""Video polyglot wrapper: preserves the source video and appends a ZIP payload.

The video stream is copied byte-for-byte. A fixed trailer lets Fake-Compression
locate and validate the appended package. Media-player compatibility depends
on the selected container/player; test the produced file with the target player.
"""
import hashlib
import os
import struct
from pathlib import Path

MAGIC = b"FC-POLYHEDRON-V1"
TRAILER_SIZE = len(MAGIC) + 8


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_polyhedron(video_path: Path, payload_path: Path, output_path: Path) -> Path:
    video_path, payload_path, output_path = map(Path, (video_path, payload_path, output_path))
    if not video_path.is_file() or not payload_path.is_file():
        raise FileNotFoundError("视频或加密载荷不存在。")
    if output_path.exists():
        raise FileExistsError(output_path)
    payload_size = payload_path.stat().st_size
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output_path.open("xb") as out:
            with video_path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    out.write(chunk)
            with payload_path.open("rb") as payload:
                for chunk in iter(lambda: payload.read(1024 * 1024), b""):
                    out.write(chunk)
            out.write(MAGIC)
            out.write(struct.pack(">Q", payload_size))
    except Exception:
        try:
            output_path.unlink()
        except OSError:
            pass
        raise
    return output_path


def extract_polyhedron_payload(polyhedron_path: Path, output_path: Path) -> tuple[Path, int]:
    source, target = Path(polyhedron_path), Path(output_path)
    size = source.stat().st_size
    if size < TRAILER_SIZE:
        raise ValueError("文件不包含 Fake-Compression 多面体数据。")
    with source.open("rb") as stream:
        stream.seek(-TRAILER_SIZE, os.SEEK_END)
        trailer = stream.read(TRAILER_SIZE)
        if trailer[:len(MAGIC)] != MAGIC:
            raise ValueError("未找到多面体文件标记。")
        payload_size = struct.unpack(">Q", trailer[len(MAGIC):])[0]
        payload_start = size - TRAILER_SIZE - payload_size
        if payload_size <= 0 or payload_start < 0:
            raise ValueError("多面体载荷长度无效。")
        stream.seek(payload_start)
        remaining = payload_size
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as out:
            while remaining:
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise ValueError("多面体载荷被截断。")
                out.write(chunk)
                remaining -= len(chunk)
    return target, payload_start
