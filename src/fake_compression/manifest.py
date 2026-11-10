"""Versioned encrypted .fc sidecar manifest."""
import hashlib
import json
from pathlib import Path
from .crypto import decrypt_json, encrypt_json

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def write_manifest(path: Path, payload: dict, password: str) -> None:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    envelope = {"format":"FAKE-COMPRESSION", "version":1, "encrypted":encrypt_json(raw, password)}
    path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")

def read_manifest(path: Path, password: str) -> dict:
    envelope = json.loads(path.read_text(encoding="utf-8"))
    if envelope.get("format") != "FAKE-COMPRESSION" or envelope.get("version") != 1:
        raise ValueError("Unsupported or invalid FC manifest.")
    payload = json.loads(decrypt_json(envelope["encrypted"], password).decode("utf-8"))
    if payload.get("format") != "FAKE-COMPRESSION-PAYLOAD":
        raise ValueError("Invalid FC payload.")
    return payload

def verify_parts(directory: Path, parts: list[dict]) -> None:
    root = directory.resolve()
    for item in parts:
        candidate = (root / item["name"]).resolve()
        if candidate.parent != root:
            raise ValueError("Manifest contains an unsafe path.")
        if not candidate.is_file():
            raise FileNotFoundError(candidate.name)
        if candidate.stat().st_size != item["size"] or sha256_file(candidate) != item["sha256"]:
            raise ValueError(f"Integrity check failed: {candidate.name}")
