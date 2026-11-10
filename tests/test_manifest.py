import threading

import pytest

from fake_compression.crypto import derive_key
from fake_compression.manifest import (
    build_file_manifest, read_manifest, sha256_file,
    verify_extracted_files, write_manifest,
)
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


def test_file_manifest_verifies_restored_content(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "hello.txt").write_text("original", encoding="utf-8")
    records = build_file_manifest(source)

    staging = tmp_path / "staging"
    (staging / "source").mkdir(parents=True)
    (staging / "source" / "hello.txt").write_text("original", encoding="utf-8")
    verify_extracted_files(staging, records)

    (staging / "source" / "hello.txt").write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="完整性校验失败"):
        verify_extracted_files(staging, records)


def test_file_manifest_rejects_missing_and_extra_files(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "expected.txt").write_text("expected", encoding="utf-8")
    records = build_file_manifest(source)
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(ValueError, match="文件列表"):
        verify_extracted_files(staging, records)


def test_scrypt_derives_32_byte_key_without_default_openssl_cap():
    key = derive_key("simple-password", b"0123456789abcdef")
    assert len(key) == 32
    assert key == derive_key("simple-password", b"0123456789abcdef")


def test_scrypt_uses_password_as_given():
    assert derive_key("123", b"0123456789abcdef") != derive_key("1234", b"0123456789abcdef")
