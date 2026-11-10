import pytest

from fake_compression.archive_paths import validate_archive_paths


@pytest.mark.parametrize(
    "path",
    [
        "../outside.txt",
        "folder/../../outside.txt",
        "/rooted/file.txt",
        r"\rooted\file.txt",
        r"C:\Windows\system.ini",
        r"\\server\share\file.txt",
        "folder/CON.txt",
        "folder/report.txt:secret",
        "folder/trailing-dot.",
        "folder/trailing-space ",
    ],
)
def test_rejects_unsafe_archive_paths(path):
    with pytest.raises(ValueError):
        validate_archive_paths([path])


@pytest.mark.parametrize(
    "path",
    [
        "readme.txt",
        "photos/2026/image.jpg",
        "folder with spaces/document.pdf",
        "nested/deeper/data.bin",
    ],
)
def test_accepts_normal_relative_paths(path):
    validate_archive_paths([path])
