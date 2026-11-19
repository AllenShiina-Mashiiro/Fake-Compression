import pytest

from fake_compression.archive import parse_7z_slt_member_paths
from fake_compression.archive_paths import validate_archive_paths


def test_7z_slt_parser_excludes_archive_header_and_preserves_unicode_members():
    lines = [
        "Path = C:\\archives\\夏姐～我恋爱的30天 v1.1.7z",
        "Type = 7z",
        "Physical Size = 1234",
        "",
        "----------",
        "Path = 夏姐～我恋爱的30天 v1.1",
        "Folder = +",
        "",
        "Path = 夏姐～我恋爱的30天 v1.1\\なつねえ ～僕が恋した30日～",
        "Folder = +",
        "",
        "Path = 夏姐～我恋爱的30天 v1.1\\readme.txt",
        "Size = 12",
        "",
    ]

    members = parse_7z_slt_member_paths(lines)

    assert members == [
        "夏姐～我恋爱的30天 v1.1",
        "夏姐～我恋爱的30天 v1.1\\なつねえ ～僕が恋した30日～",
        "夏姐～我恋爱的30天 v1.1\\readme.txt",
    ]
    validate_archive_paths(members)


def test_7z_slt_parser_preserves_duplicates_for_security_validation():
    lines = [
        "Path = archive.7z",
        "Type = 7z",
        "",
        "----------",
        "Path = folder/file.txt",
        "",
        "Path = folder/FILE.TXT",
        "",
    ]
    with pytest.raises(ValueError, match="重复"):
        validate_archive_paths(parse_7z_slt_member_paths(lines))


def test_7z_slt_parser_rejects_missing_separator():
    with pytest.raises(ValueError, match="分隔标记"):
        parse_7z_slt_member_paths(["Path = archive.7z", "Type = 7z"])
