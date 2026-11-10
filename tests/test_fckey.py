import pytest

from fake_compression.fckey import decode_fckey, encode_fckey


def test_fckey_round_trip():
    payload = b'{"source_root":"Project-A","parts":[]}'
    encoded = encode_fckey(payload, "master password", "master password")
    assert encoded.startswith(b"FCKEY\x01\x00")
    assert decode_fckey(encoded, "master password", "master password") == payload


def test_fckey_rejects_wrong_password():
    encoded = encode_fckey(b"private metadata", "first", "second")
    with pytest.raises(ValueError, match="密码错误"):
        decode_fckey(encoded, "wrong", "second")


def test_fckey_rejects_corrupt_header():
    with pytest.raises(ValueError, match="不是有效的 FCKEY"):
        decode_fckey(b"not-an-fckey", "first", "second")


def test_external_layer_passwords_are_stable_and_separated():
    from fake_compression.fckey import derive_archive_password

    salt = bytes(range(16))
    first = derive_archive_password("same raw password", salt, 1)
    second = derive_archive_password("same raw password", salt, 2)
    assert first == derive_archive_password("same raw password", salt, 1)
    assert first != second
    assert first != derive_archive_password("different password", salt, 1)


def test_fckey_requires_both_original_passwords():
    with pytest.raises(ValueError, match="都不能为空"):
        encode_fckey(b"metadata", "first", "")
