"""Standalone FCKEY v2 decoder. The embedded key is an obfuscation boundary, not unbreakable DRM."""
import base64, hashlib, hmac, json
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"FCKEY\x02\x00"
NONCE_SIZE = 12
READER_KEY = bytes.fromhex("8f2a91c4d6e70b3a5c1d9e2f4a6b8c0d112233445566778899aabbccddeeff00")

def derive_archive_password(password, salt, layer):
    key = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**15, r=8, p=1,
                         maxmem=128*1024*1024, dklen=32)
    digest = hmac.new(key, f"fake-compression/archive/layer-{layer}/v1".encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

def read_and_derive(path: Path):
    blob = Path(path).read_bytes()
    if not blob.startswith(MAGIC) or len(blob) < len(MAGIC)+NONCE_SIZE+16:
        raise ValueError("不是新版 Reader FCKEY；旧版文件无法免密码读取，请用新版 FC 重新生成。")
    off=len(MAGIC)
    raw=AESGCM(READER_KEY).decrypt(blob[off:off+NONCE_SIZE], blob[off+NONCE_SIZE:], b"FAKE-COMPRESSION-READER/2")
    meta=json.loads(raw.decode("utf-8"))
    if meta.get("format")!="FAKE-COMPRESSION-FCKEY-PAYLOAD" or meta.get("version")!=1:
        raise ValueError("不支持此 FCKEY 元数据版本。")
    p1,p2=meta["original_password1"],meta["original_password2"]
    salt=base64.b64decode(meta["archive_salt"],validate=True)
    return meta,p1,p2,derive_archive_password(p1,salt,1),derive_archive_password(p2,salt,2)
