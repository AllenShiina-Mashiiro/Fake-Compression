from pathlib import Path

from fake_compression.polyvideo import create_polyhedron, extract_polyhedron_payload


def test_polyvideo_payload_survives_arbitrary_rename(tmp_path: Path):
    video = tmp_path / "preview.mp4"
    payload = tmp_path / "outer-package.zip"
    output = tmp_path / "disguised.mp4"
    extracted = tmp_path / "recovered-package.bin"
    video.write_bytes(b"video-container-prefix")
    payload.write_bytes(b"PK\\x03\\x04encrypted-package-data")

    create_polyhedron(video, payload, output)
    renamed = tmp_path / "renamed-to-anything.dat"
    output.rename(renamed)
    extract_polyhedron_payload(renamed, extracted)

    assert extracted.read_bytes() == payload.read_bytes()
    assert renamed.read_bytes().startswith(video.read_bytes())
