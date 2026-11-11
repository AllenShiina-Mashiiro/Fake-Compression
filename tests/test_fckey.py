import pytest

from fake_compression.fckey import MAGIC, decode_fckey, encode_fckey


def test_fckey_v2_round_trip_without_password_entry():
    payload = b'{"source_root":"Project-A","parts":[]}'
    encoded = encode_fckey(payload, "master password", "second password")
    assert encoded.startswith(MAGIC)
    assert encoded.startswith(b"FCKEY\x02\x00")
    assert decode_fckey(encoded) == payload
    # Reader-mode decode remains independent from the original passwords.
    assert decode_fckey(encoded, "wrong", "wrong") == payload


def test_fckey_rejects_corrupt_header():
    with pytest.raises(ValueError, match="不是有效的 FCKEY"):
        decode_fckey(b"not-an-fckey")


def test_fckey_rejects_corrupt_ciphertext():
    encoded = bytearray(encode_fckey(b"private metadata", "first", "second"))
    encoded[-1] ^= 0x01
    with pytest.raises(ValueError, match="无法解密"):
        decode_fckey(bytes(encoded))


def test_external_layer_passwords_are_stable_and_separated():
    from fake_compression.fckey import derive_archive_password

    salt = bytes(range(16))
    first = derive_archive_password("same raw password", salt, 1)
    second = derive_archive_password("same raw password", salt, 2)
    assert first == derive_archive_password("same raw password", salt, 1)
    assert first != second
    assert first != derive_archive_password("different password", salt, 1)
