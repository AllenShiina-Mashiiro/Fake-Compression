"""MP4 + ZIP polyglot helpers.

The original MP4 bytes are kept unchanged at the beginning of the file and a
complete ZIP archive is appended. ZIP readers locate the end-of-central-
directory record, so prepended MP4 data is tolerated by standard ZIP readers.
"""
import hashlib
import os
import tempfile
import zipfile
from pathlib import Path

from .tools import OperationCancelled


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_stream(source: Path, destination, cancel_event=None) -> None:
    with Path(source).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            if cancel_event and cancel_event.is_set():
                raise OperationCancelled("视频载荷封装已取消。")
            destination.write(chunk)


def create_polyhedron(video_path: Path, payload_path: Path, output_path: Path, cancel_event=None) -> Path:
    video_path, payload_path, output_path = map(Path, (video_path, payload_path, output_path))
    if not video_path.is_file() or not payload_path.is_file():
        raise FileNotFoundError("视频或 ZIP 载荷不存在。")
    if video_path.suffix.lower() != ".mp4":
        raise ValueError("视频伪装目前只接受 MP4 文件。")
    if not zipfile.is_zipfile(payload_path):
        raise ValueError("第三层载荷不是有效的 ZIP 文件。")
    if output_path.exists():
        raise FileExistsError(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(output_path.name + ".partial")
    try:
        with temporary.open("xb") as out:
            _copy_stream(video_path, out, cancel_event)
            _copy_stream(payload_path, out, cancel_event)
        if cancel_event and cancel_event.is_set():
            raise OperationCancelled("视频载荷封装已取消。")
        os.replace(temporary, output_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
        raise
    return output_path


def extract_polyhedron_payload(polyhedron_path: Path, output_path: Path, cancel_event=None) -> tuple[Path, int]:
    """Extract the appended ZIP payload without overwriting an existing file."""
    source, target = Path(polyhedron_path), Path(output_path)
    if not source.is_file():
        raise FileNotFoundError(source)
    if target.exists():
        raise FileExistsError(target)
    if not zipfile.is_zipfile(source):
        raise ValueError("未找到可识别的 ZIP 载荷。")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".partial", dir=target.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(source, "r") as archive:
            bad = archive.testzip()
            if bad is not None:
                raise ValueError(f"ZIP 载荷校验失败：{bad}")
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as clean:
                for info in archive.infolist():
                    if cancel_event and cancel_event.is_set():
                        raise OperationCancelled("视频载荷提取已取消。")
                    clean.writestr(info, archive.read(info.filename))
        if cancel_event and cancel_event.is_set():
            raise OperationCancelled("视频载荷提取已取消。")
        if target.exists():
            raise FileExistsError(target)
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return target, 0
