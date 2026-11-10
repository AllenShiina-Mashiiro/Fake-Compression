import pytest
from fake_compression.manifest import read_manifest, write_manifest

def test_manifest_round_trip(tmp_path):
    path = tmp_path / "sample.fc"
    payload = {"format": "FAKE-COMPRESSION-PAYLOAD", "parts": []}
    write_manifest(path, payload, "correct horse battery staple")
    assert read_manifest(path, "correct horse battery staple") == payload
    with pytest.raises(ValueError):
        read_manifest(path, "wrong password")
