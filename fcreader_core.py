"""Protocol-compatible FCKEY decoder for the standalone Reader."""
import base64
import hashlib
import hmac
import json
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"FCKEY\x01\x00"
SALT_SIZE = 16
NONCE_SIZE = 12
AAD = b"FAKE-COMPRESSION-FCKEY/1"
SCRYPT_N = 2 ** 15
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MAXMEM = 128 * 1024 * 1024


def _derive_combined_key(password1: str, password2: str, salt: bytes) -> bytes:
    if not password1 or not password2:
        raise ValueError("请输入第一层和第二层原始密码。")
    material = password1.encode("utf-8") + b"\x00FC-LAYER-SEPARATOR\x00" + password2.encode("utf-8")
    return hashlib.scrypt(material, salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P,
                          maxmem=SCRYPT_MAXMEM, dklen=32)


def derive_archive_password(password: str, salt: bytes, layer: int) -> str:
    if layer not in (1, 2):
        raise ValueError("未知加密层。")
    key = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R,
                         p=SCRYPT_P, maxmem=SCRYPT_MAXMEM, dklen=32)
    digest = hmac.new(key, f"fake-compression/archive/layer-{layer}/v1".encode(),
                      hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def read_and_derive(path: Path, password1: str, password2: str):
    blob = Path(path).read_bytes()
    minimum = len(MAGIC) + SALT_SIZE + NONCE_SIZE + 16
    if len(blob) < minimum or not blob.startswith(MAGIC):
        raise ValueError("不是有效的 FCKEY 文件，或文件已损坏。")
    offset = len(MAGIC)
    salt = blob[offset:offset + SALT_SIZE]
    nonce = blob[offset + SALT_SIZE:offset + SALT_SIZE + NONCE_SIZE]
    ciphertext = blob[offset + SALT_SIZE + NONCE_SIZE:]
    key = _derive_combined_key(password1, password2, salt)
    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, AAD)
    except Exception as exc:
        raise ValueError("密码错误，或 FCKEY 文件已损坏。") from exc
    metadata = json.loads(plaintext.decode("utf-8"))
    if metadata.get("format") != "FAKE-COMPRESSION-FCKEY-PAYLOAD" or metadata.get("version") != 1:
        raise ValueError("不支持此 FCKEY 元数据版本。")
    archive_salt = base64.b64decode(metadata["archive_salt"], validate=True)
    return metadata, derive_archive_password(password1, archive_salt, 1), derive_archive_password(password2, archive_salt, 2)
