"""Opt-in real 7-Zip + WinRAR end-to-end regression test.

Run on Windows after installing both tools:
    py -m pytest tests/test_archive_e2e.py -q
"""
from pathlib import Path
import zipfile

import pytest

import fake_compression.archive as archive_module
from fake_compression.archive import ArchiveService
from fake_compression.sizing import SizePlan
from fake_compression.tools import find_7z, find_rar


pytestmark = pytest.mark.skipif(
    not find_7z() or not find_rar(),
    reason="Real 7-Zip and WinRAR executables are required for this end-to-end test.",
)


@pytest.mark.parametrize("repeat_password", [True, False])
def test_real_two_layer_round_trip_after_arbitrary_rename(tmp_path, monkeypatch, repeat_password):
    source = tmp_path / "Original-Project"
    (source / "nested").mkdir(parents=True)
    (source / "hello.txt").write_text("hello Fake-Compression", encoding="utf-8")
    (source / "nested" / "data.bin").write_bytes(bytes(range(256)) * 8192)
    output = tmp_path / "packages"
    restored = tmp_path / "restored"

    # Force small real split volumes so the test covers the multi-volume path
    # without requiring gigabytes of fixture data.
    monkeypatch.setattr(
        archive_module, "inspect_source",
        lambda _source: SizePlan(total_bytes=2 * 1024 * 1024, volume_bytes=512 * 1024),
    )
    service = ArchiveService()
    package = service.create(
        source, output, "First-Output-Name", "first raw password",
        second_password="second raw password",
        repeat_password=repeat_password,
    )
    assert package.name == "First-Output-Name.rar"
    assert zipfile.is_zipfile(package)
    key_file = package.with_suffix(".fckey")
    assert key_file.is_file()
    with zipfile.ZipFile(package) as outer:
        assert outer.namelist() == ["payload.rar"]
        assert "metadata.fckey" not in outer.namelist()

    renamed = output / "completely-unrelated-name.rar"
    package.rename(renamed)
    key_file.rename(renamed.with_suffix(".fckey"))
    result = service.extract(
        renamed, restored, "first raw password",
        second_password="second raw password",
        repeat_password=repeat_password,
    )
    assert result.name == source.name
    assert (result / "hello.txt").read_text(encoding="utf-8") == "hello Fake-Compression"
    assert (result / "nested" / "data.bin").read_bytes() == bytes(range(256)) * 8192
