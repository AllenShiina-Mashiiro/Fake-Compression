import base64
import hashlib
import json

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from fcreader_core import AAD, MAGIC, NONCE_SIZE, SALT_SIZE, read_and_derive


def make_fckey(payload, password1, password2):
    salt = bytes(range(SALT_SIZE))
    nonce = bytes(range(NONCE_SIZE))
    material = password1.encode() + b"\x00FC-LAYER-SEPARATOR\x00" + password2.encode()
    key = hashlib.scrypt(material, salt=salt, n=2**15, r=8, p=1,
                         maxmem=128 * 1024 * 1024, dklen=32)
    return MAGIC + salt + nonce + AESGCM(key).encrypt(nonce, payload, AAD)


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
    path = tmp_path / "metadata.fckey"
    path.write_bytes(make_fckey(raw, "first-pass", "second-pass"))

    parsed, first, second = read_and_derive(path, "first-pass", "second-pass")
    assert parsed["source_root"] == "Example"
    # Independent expected derivation, intentionally not importing FC code.
    def expected(password, layer):
        key = hashlib.scrypt(password.encode(), salt=salt, n=2**15, r=8, p=1,
                             maxmem=128 * 1024 * 1024, dklen=32)
        import hmac
        digest = hmac.new(key, f"fake-compression/archive/layer-{layer}/v1".encode(),
                          hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    assert first == expected("first-pass", 1)
    assert second == expected("second-pass", 2)
