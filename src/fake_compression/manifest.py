"""Versioned encrypted .fc sidecar manifest."""
import hashlib
import json
from pathlib import Path, PurePosixPath

from .crypto import decrypt_json, encrypt_json
from .tools import OperationCancelled


def sha256_file(path: Path, cancel_event=None) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            if cancel_event and cancel_event.is_set():
                raise OperationCancelled("任务已取消。")
            digest.update(chunk)
    return digest.hexdigest()


def build_file_manifest(source: Path, cancel_event=None) -> list[dict]:
    """Hash every regular input file using paths relative to the archive root."""
    source = Path(source)
    if source.is_symlink():
        raise ValueError("不支持对符号链接计算文件清单。")
    if source.is_file():
        files = [source]
        prefix = ""
    elif source.is_dir():
        files = sorted(source.rglob("*"))
        prefix = source.name
    else:
        raise FileNotFoundError(source)

    records = []
    for item in files:
        if cancel_event and cancel_event.is_set():
            raise OperationCancelled("任务已取消。")
        if item.is_symlink():
            raise ValueError(f"输入目录包含符号链接：{item}")
        if not item.is_file():
            continue
        relative = item.name if not prefix else f"{prefix}/{item.relative_to(source).as_posix()}"
        records.append({
            "path": relative,
            "size": item.stat().st_size,
            "sha256": sha256_file(item, cancel_event),
        })
    return records


def verify_extracted_files(staging: Path, records: list[dict], cancel_event=None) -> None:
    """Require exact file-set, size and SHA-256 agreement before publishing output."""
    root = Path(staging).resolve()
    expected = {}
    for record in records:
        relative = PurePosixPath(record["path"])
        if relative.is_absolute() or not relative.parts or any(part in ("", ".", "..") for part in relative.parts):
            raise ValueError("文件校验清单包含不安全路径。")
        key = relative.as_posix().casefold()
        if key in expected:
            raise ValueError("文件校验清单包含重复路径。")
        expected[key] = (relative, record)

    actual = {}
    for item in root.rglob("*"):
        if cancel_event and cancel_event.is_set():
            raise OperationCancelled("任务已取消。")
        if item.is_symlink():
            raise ValueError("恢复内容包含符号链接，已拒绝发布文件。")
        if item.is_file():
            key = item.relative_to(root).as_posix().casefold()
            actual[key] = item

    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise ValueError(f"恢复文件列表与原始清单不一致。缺少：{missing[:3]}；多出：{extra[:3]}")

    for key, (relative, record) in expected.items():
        item = actual[key]
        if item.stat().st_size != record["size"] or sha256_file(item, cancel_event) != record["sha256"]:
            raise ValueError(f"恢复文件完整性校验失败：{relative.as_posix()}")


def write_manifest(path: Path, payload: dict, password: str) -> None:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    envelope = {"format": "FAKE-COMPRESSION", "version": 1, "encrypted": encrypt_json(raw, password)}
    path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")


def read_manifest(path: Path, password: str) -> dict:
    envelope = json.loads(path.read_text(encoding="utf-8"))
    if envelope.get("format") != "FAKE-COMPRESSION" or envelope.get("version") != 1:
        raise ValueError("Unsupported or invalid FC manifest.")
    payload = json.loads(decrypt_json(envelope["encrypted"], password).decode("utf-8"))
    if payload.get("format") != "FAKE-COMPRESSION-PAYLOAD":
        raise ValueError("Invalid FC payload.")
    return payload


def verify_parts(directory: Path, parts: list[dict], cancel_event=None) -> None:
    root = directory.resolve()
    for item in parts:
        if cancel_event and cancel_event.is_set():
            raise OperationCancelled("任务已取消。")
        candidate = (root / item["name"]).resolve()
        if candidate.parent != root:
            raise ValueError("Manifest contains an unsafe path.")
        if not candidate.is_file():
            raise FileNotFoundError(candidate.name)
        if candidate.stat().st_size != item["size"] or sha256_file(candidate, cancel_event) != item["sha256"]:
            raise ValueError(f"Integrity check failed: {candidate.name}")
