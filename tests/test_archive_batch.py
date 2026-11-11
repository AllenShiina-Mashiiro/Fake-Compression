from pathlib import Path

from fake_compression.archive import ArchiveService


def test_batch_create_uses_each_child_folder_name_and_continues(tmp_path, monkeypatch):
    root = tmp_path / "input"
    (root / "Alpha").mkdir(parents=True)
    (root / "Beta").mkdir()
    output = tmp_path / "out"
    service = object.__new__(ArchiveService)
    calls = []

    def fake_create(source, output_dir, name, password, **kwargs):
        calls.append((Path(source).name, name))
        if name == "Beta":
            raise RuntimeError("deliberate test failure")
        return Path(output_dir) / f"{name}.fc"

    monkeypatch.setattr(service, "create", fake_create)
    results = service.create_batch(root, output, "password")
    assert calls == [("Alpha", "Alpha"), ("Beta", "Beta")]
    assert results[0]["success"] is True
    assert results[1]["success"] is False
    assert "deliberate test failure" in results[1]["error"]


def test_batch_extract_continues_after_one_failed_package(tmp_path, monkeypatch):
    packages = [tmp_path / "one.fc", tmp_path / "two.fc"]
    service = object.__new__(ArchiveService)

    def fake_extract(package, output_dir, password, **kwargs):
        if Path(package).name == "one.fc":
            raise ValueError("bad package")
        return Path(output_dir) / "Restored"

    monkeypatch.setattr(service, "extract", fake_extract)
    results = service.extract_batch(packages, tmp_path / "out", "password")
    assert [item["success"] for item in results] == [False, True]
