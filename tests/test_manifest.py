import threading

import pytest

from fake_compression.manifest import read_manifest, sha256_file, write_manifest
from fake_compression.tools import OperationCancelled


def test_manifest_round_trip(tmp_path):
    path = tmp_path / "sample.fc"
    payload = {"format": "FAKE-COMPRESSION-PAYLOAD", "parts": []}
    write_manifest(path, payload, "correct horse battery staple")
    assert read_manifest(path, "correct horse battery staple") == payload
    with pytest.raises(ValueError):
        read_manifest(path, "wrong password")


def test_sha256_file_can_be_cancelled(tmp_path):
    path = tmp_path / "large.bin"
    path.write_bytes(b"sample data")
    cancelled = threading.Event()
    cancelled.set()
    with pytest.raises(OperationCancelled):
        sha256_file(path, cancelled)
