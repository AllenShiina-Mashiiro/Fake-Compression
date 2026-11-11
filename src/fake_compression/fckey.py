"""Binary, authenticated .fckey container and deterministic external archive passwords.

The file hides metadata from casual text viewers; confidentiality comes from
AES-GCM and scrypt, not from the binary extension itself.
"""
import hashlib
import hmac
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .crypto import SCRYPT_MAXMEM, SCRYPT_N, SCRYPT_P, SCRYPT_R

MAGIC = b"FCKEY\x02\x00"
LEGACY_MAGIC = b"FCKEY\x01\x00"
_READER_KEY = bytes.fromhex("8f2a91c4d6e70b3a5c1d9e2f4a6b8c0d112233445566778899aabbccddeeff00")
SALT_SIZE = 16
NONCE_SIZE = 12
AAD = b"FAKE-COMPRESSION-FCKEY/1"


def _derive_combined_key(password1: str, password2: str, salt: bytes) -> bytes:
    if not password1 or not password2:
        raise ValueError("两层原始密码都不能为空。")
    material = password1.encode("utf-8") + b"\x00FC-LAYER-SEPARATOR\x00" + password2.encode("utf-8")
    return hashlib.scrypt(
        material, salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P,
        maxmem=SCRYPT_MAXMEM, dklen=32,
    )


def derive_archive_password(password: str, salt: bytes, layer: int) -> str:
    """Derive a printable, standard-archiver password; layer must be 1 or 2."""
    if layer not in (1, 2):
        raise ValueError("未知加密层。")
    if not password:
        raise ValueError("密码不能为空。")
    key = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P,
        maxmem=SCRYPT_MAXMEM, dklen=32,
    )
    digest = hmac.new(key, f"fake-compression/archive/layer-{layer}/v1".encode(), hashlib.sha256).digest()
    import base64
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def encode_fckey(payload: bytes, password1: str, password2: str) -> bytes:
    nonce = os.urandom(NONCE_SIZE)
    encrypted = AESGCM(_READER_KEY).encrypt(nonce, payload, b"FAKE-COMPRESSION-READER/2")
    return MAGIC + nonce + encrypted


def decode_fckey(blob: bytes, password1: str = "", password2: str = "") -> bytes:
    if blob.startswith(MAGIC):
        offset = len(MAGIC)
        if len(blob) < offset + NONCE_SIZE + 16:
            raise ValueError("FCKEY 文件已损坏。")
        try:
            return AESGCM(_READER_KEY).decrypt(blob[offset:offset + NONCE_SIZE],
                blob[offset + NONCE_SIZE:], b"FAKE-COMPRESSION-READER/2")
        except Exception as exc:
            raise ValueError("Reader 无法解密此 FCKEY 文件，文件可能已损坏。") from exc
    if not blob.startswith(LEGACY_MAGIC):
        raise ValueError("不是有效的 FCKEY 文件。")
    offset = len(LEGACY_MAGIC)
    salt = blob[offset:offset + SALT_SIZE]
    nonce = blob[offset + SALT_SIZE:offset + SALT_SIZE + NONCE_SIZE]
    ciphertext = blob[offset + SALT_SIZE + NONCE_SIZE:]
    key = _derive_combined_key(password1, password2, salt)
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, AAD)
    except Exception as exc:
        raise ValueError("旧版 FCKEY 需要输入原始密码，或文件已损坏。") from exc


def write_fckey(path: Path, payload: bytes, password1: str, password2: str) -> None:
    Path(path).write_bytes(encode_fckey(payload, password1, password2))


def read_fckey(path: Path, password1: str, password2: str) -> bytes:
    return decode_fckey(Path(path).read_bytes(), password1, password2)
