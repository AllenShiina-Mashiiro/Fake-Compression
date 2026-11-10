import base64
import hashlib
import hmac
import json

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from fcreader_core import MAGIC, NONCE_SIZE, READER_KEY, read_and_derive


def make_fckey(payload):
    nonce = bytes(range(NONCE_SIZE))
    return MAGIC + nonce + AESGCM(READER_KEY).encrypt(
        nonce, payload, b"FAKE-COMPRESSION-READER/2"
    )


def expected(password, salt, layer):
    key = hashlib.scrypt(password.encode(), salt=salt, n=2**15, r=8, p=1,
                         maxmem=128 * 1024 * 1024, dklen=32)
    digest = hmac.new(key, f"fake-compression/archive/layer-{layer}/v1".encode(),
                      hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def test_standalone_reader_derives_passwords_without_user_input(tmp_path):
    salt = bytes(range(16))
    metadata = {
        "format": "FAKE-COMPRESSION-FCKEY-PAYLOAD",
        "version": 1,
        "source_root": "Example",
        "original_password1": "first-pass",
        "original_password2": "second-pass",
        "archive_salt": base64.b64encode(salt).decode("ascii"),
        "first_layer": {"format": "7z", "encryption": "AES-256",
                        "volumes": [{"name": "a.7z.001", "size": 1, "sha256": "0" * 64}]},
        "second_layer": {"format": "RAR5", "encryption": "AES-256", "split": False},
        "source_files": [],
    }
    path = tmp_path / "metadata.fckey"
    path.write_bytes(make_fckey(json.dumps(metadata).encode("utf-8")))

    parsed, first_original, second_original, first_special, second_special = read_and_derive(path)
    assert parsed["source_root"] == "Example"
    assert first_original == "first-pass"
    assert second_original == "second-pass"
    assert first_special == expected("first-pass", salt, 1)
    assert second_special == expected("second-pass", salt, 2)


def test_reader_rejects_corrupted_key_file(tmp_path):
    path = tmp_path / "broken.fckey"
    path.write_bytes(b"not a key file")
    import pytest
    with pytest.raises(ValueError, match="不是新版 Reader FCKEY"):
        read_and_derive(path)
