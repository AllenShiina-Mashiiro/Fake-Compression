import base64
import json

from fake_compression.fckey import encode_fckey, derive_archive_password
from fcreader_core import read_and_derive


def test_standalone_reader_derives_exact_archiver_passwords(tmp_path):
    salt = bytes(range(16))
    metadata = {
        "format": "FAKE-COMPRESSION-FCKEY-PAYLOAD",
        "version": 1,
        "source_root": "Example",
        "archive_salt": base64.b64encode(salt).decode("ascii"),
        "first_layer": {"format": "7z", "encryption": "AES-256", "volumes": [{"name": "a.7z.001"}]},
        "second_layer": {"format": "RAR5", "encryption": "AES-256", "split": False},
        "source_files": [],
    }
    raw = json.dumps(metadata).encode("utf-8")
    blob = encode_fckey(raw, "first-pass", "second-pass")
    path = tmp_path / "metadata.fckey"
    path.write_bytes(blob)

    parsed, first, second = read_and_derive(path, "first-pass", "second-pass")
    assert parsed["source_root"] == "Example"
    assert first == derive_archive_password("first-pass", salt, 1)
    assert second == derive_archive_password("second-pass", salt, 2)
