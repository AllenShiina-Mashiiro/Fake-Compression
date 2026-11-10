"""Password-based key derivation and authenticated metadata encryption."""
import base64
import hashlib
import hmac
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SCRYPT_N = 2 ** 15
SCRYPT_R = 8
SCRYPT_P = 1

def derive_key(password: str, salt: bytes) -> bytes:
    if not password:
        raise ValueError("A master password is required.")
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)

def archive_password(key: bytes) -> str:
    digest = hmac.new(key, b"fake-compression/archive/v1", hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

def encrypt_json(payload: bytes, password: str) -> dict:
    salt, nonce = os.urandom(16), os.urandom(12)
    key = derive_key(password, salt)
    ciphertext = AESGCM(key).encrypt(nonce, payload, b"FAKE-COMPRESSION/1")
    return {"kdf":"scrypt", "n":SCRYPT_N, "r":SCRYPT_R, "p":SCRYPT_P,
            "salt":base64.b64encode(salt).decode("ascii"),
            "nonce":base64.b64encode(nonce).decode("ascii"),
            "ciphertext":base64.b64encode(ciphertext).decode("ascii")}

def decrypt_json(envelope: dict, password: str) -> bytes:
    if envelope.get("kdf") != "scrypt":
        raise ValueError("Unsupported key derivation scheme.")
    salt = base64.b64decode(envelope["salt"], validate=True)
    nonce = base64.b64decode(envelope["nonce"], validate=True)
    ciphertext = base64.b64decode(envelope["ciphertext"], validate=True)
    key = derive_key(password, salt)
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, b"FAKE-COMPRESSION/1")
    except Exception as exc:
        raise ValueError("Incorrect password or damaged FC manifest.") from exc
