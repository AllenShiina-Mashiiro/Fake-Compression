import base64
import copy
import pytest

from fake_compression.archive import validate_fckey_metadata


@pytest.fixture
def valid_metadata():
    return {
        "format": "FAKE-COMPRESSION-FCKEY-PAYLOAD",
        "version": 1,
        "source_root": "Project-A",
        "archive_salt": base64.b64encode(b"0123456789abcdef").decode("ascii"),
        "first_layer": {"format": "7z", "encryption": "AES-256", "split": True,
                        "volumes": [{"name": "Project-A.7z.001", "size": 128, "sha256": "a" * 64}]},
        "second_layer": {"format": "RAR5", "encryption": "AES-256", "split": False},
        "source_files": [{"path": "Project-A/readme.txt", "size": 12, "sha256": "b" * 64}],
    }


def test_accepts_valid_authenticated_metadata(valid_metadata):
    assert validate_fckey_metadata(valid_metadata) is valid_metadata


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(source_root="../escape"),
        lambda value: value.update(source_root="folder/nested"),
        lambda value: value["first_layer"].update(volumes=[{"name": None, "size": 1, "sha256": "a" * 64}]),
        lambda value: value["first_layer"].update(volumes=[{"name": "vol.001", "size": True, "sha256": "a" * 64}]),
        lambda value: value["first_layer"].update(volumes=[{"name": "vol.001", "size": 1, "sha256": "bad"}]),
        lambda value: value.update(source_files=[{"path": "../escape", "size": 1, "sha256": "b" * 64}]),
        lambda value: value.update(source_files=[{"path": "safe.txt", "size": -1, "sha256": "b" * 64}]),
        lambda value: value.update(archive_salt="not-base64!"),
    ],
)
def test_rejects_malformed_metadata(valid_metadata, mutate):
    malformed = copy.deepcopy(valid_metadata)
    mutate(malformed)
    with pytest.raises(ValueError):
        validate_fckey_metadata(malformed)


def test_rejects_non_object_metadata():
    with pytest.raises(ValueError):
        validate_fckey_metadata([])