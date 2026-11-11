from pathlib import Path
import zipfile

import pytest

from fake_compression.polyvideo import create_polyhedron, extract_polyhedron_payload


def make_zip(path: Path):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("metadata.fckey", b"encrypted metadata")
        archive.writestr("payload.rar", b"encrypted archive")


def test_mp4_zip_polyglot_is_renamable_and_extractable(tmp_path: Path):
    video = tmp_path / "preview.mp4"
    payload = tmp_path / "outer-package.zip"
    output = tmp_path / "disguised.mp4"
    extracted = tmp_path / "recovered-package.zip"
    video_bytes = b"\x00\x00\x00\x18ftypisom" + b"synthetic-mp4-fixture"
    video.write_bytes(video_bytes)
    make_zip(payload)

    create_polyhedron(video, payload, output)
    assert output.read_bytes().startswith(video_bytes)
    assert zipfile.is_zipfile(output)

    renamed = tmp_path / "renamed.zip"
    output.rename(renamed)
    assert zipfile.is_zipfile(renamed)
    extract_polyhedron_payload(renamed, extracted)
    with zipfile.ZipFile(extracted) as archive:
        assert sorted(archive.namelist()) == ["metadata.fckey", "payload.rar"]
        assert archive.read("payload.rar") == b"encrypted archive"


def test_polyvideo_rejects_invalid_zip_payload(tmp_path: Path):
    video = tmp_path / "preview.mp4"
    payload = tmp_path / "bad.zip"
    output = tmp_path / "disguised.mp4"
    video.write_bytes(b"\x00\x00\x00\x18ftypisom")
    payload.write_bytes(b"not a zip")
    with pytest.raises(ValueError, match="有效的 ZIP"):
        create_polyhedron(video, payload, output)
    assert not output.exists()


def test_polyvideo_creation_cancellation_removes_partial_output(tmp_path: Path):
    from threading import Event
    from fake_compression.tools import OperationCancelled

    video = tmp_path / "preview.mp4"
    payload = tmp_path / "payload.zip"
    output = tmp_path / "cancelled.mp4"
    video.write_bytes(b"v" * 4096)
    make_zip(payload)
    cancelled = Event()
    cancelled.set()
    with pytest.raises(OperationCancelled):
        create_polyhedron(video, payload, output, cancelled)
    assert not output.exists()
    assert not output.with_name(output.name + ".partial").exists()


def test_polyvideo_extraction_cancellation_removes_partial_output(tmp_path: Path):
    from threading import Event
    from fake_compression.tools import OperationCancelled

    video = tmp_path / "preview.mp4"
    payload = tmp_path / "payload.zip"
    output = tmp_path / "partial.zip"
    video.write_bytes(b"\x00\x00\x00\x18ftypisom")
    make_zip(payload)
    wrapped = tmp_path / "wrapped.mp4"
    create_polyhedron(video, payload, wrapped)
    cancelled = Event()
    cancelled.set()
    with pytest.raises(OperationCancelled):
        extract_polyhedron_payload(wrapped, output, cancelled)
    assert not output.exists()


def test_polyvideo_extraction_does_not_overwrite_existing_target(tmp_path: Path):
    video = tmp_path / "preview.mp4"
    payload = tmp_path / "payload.zip"
    wrapped = tmp_path / "wrapped.mp4"
    target = tmp_path / "existing.zip"
    video.write_bytes(b"\x00\x00\x00\x18ftypisom")
    make_zip(payload)
    create_polyhedron(video, payload, wrapped)
    target.write_bytes(b"keep this file")
    with pytest.raises(FileExistsError):
        extract_polyhedron_payload(wrapped, target)
    assert target.read_bytes() == b"keep this file"


def test_ffmpeg_can_probe_real_mp4_polyglot_when_available(tmp_path: Path):
    import shutil
    import subprocess

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg/ffprobe are not installed.")
    video = tmp_path / "real-preview.mp4"
    payload = tmp_path / "real-payload.zip"
    output = tmp_path / "real-disguised.mp4"
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi",
         "-i", "color=c=black:s=160x90:d=0.5", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", "-y", str(video)],
        check=True, capture_output=True,
    )
    make_zip(payload)
    create_polyhedron(video, payload, output)
    probe = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=format_name",
         "-of", "default=noprint_wrappers=1:nokey=1", str(output)],
        check=True, capture_output=True, text=True,
    )
    assert "mov" in probe.stdout or "mp4" in probe.stdout
    assert zipfile.is_zipfile(output)
