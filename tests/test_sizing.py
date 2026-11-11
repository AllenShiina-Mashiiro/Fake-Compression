import pytest

from fake_compression.sizing import GIB, calculate_size, plan_volumes


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        (0, None),
        (GIB, None),
        (GIB + 1, 2 * GIB),
        (5 * GIB, 2 * GIB),
        (5 * GIB + 1, 4 * GIB),
        (9 * GIB, 4 * GIB),
        (9 * GIB + 1, 4 * GIB),
    ],
)
def test_volume_policy(size, expected):
    assert plan_volumes(size).volume_bytes == expected


def test_negative_size_rejected():
    with pytest.raises(ValueError):
        plan_volumes(-1)


def test_calculate_size_counts_regular_files(tmp_path):
    (tmp_path / "one.bin").write_bytes(b"123")
    child = tmp_path / "nested"
    child.mkdir()
    (child / "two.bin").write_bytes(b"45678")
    assert calculate_size(tmp_path) == 8


def test_calculate_size_rejects_symbolic_links(tmp_path):
    target = tmp_path / "target.bin"
    target.write_bytes(b"payload")
    link = tmp_path / "link.bin"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("Symbolic links are unavailable in this environment.")
    with pytest.raises(ValueError, match="symbolic link"):
        calculate_size(tmp_path)
