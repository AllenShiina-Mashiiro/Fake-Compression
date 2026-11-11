"""Three-stage package: encrypted 7z volumes -> encrypted RAR -> plain ZIP renamed to .rar."""
import base64
import json
import os
import re
import shutil
import tempfile
import time
import zipfile
from pathlib import Path

from .archive_paths import validate_archive_paths, validate_package_name
from .fckey import decode_fckey, derive_archive_password, encode_fckey
from .manifest import build_file_manifest, sha256_file, verify_extracted_files
from .polyvideo import create_polyhedron, extract_polyhedron_payload
from .sizing import inspect_source
from .tools import find_7z, find_rar, normalize_dictionary_size, performance_settings, run_checked


# Kept only for backward compatibility when reading packages made by older builds.
OUTER_METADATA = "metadata.fckey"
OUTER_ARCHIVE = "payload.rar"


def validate_fckey_metadata(metadata: object) -> dict:
    """Validate authenticated metadata structure before using any value as a path."""
    if not isinstance(metadata, dict):
        raise ValueError("FCKEY 元数据必须是对象。")
    if metadata.get("format") != "FAKE-COMPRESSION-FCKEY-PAYLOAD" or metadata.get("version") != 1:
        raise ValueError("不支持的 FCKEY 元数据版本。")
    root_name = metadata.get("source_root")
    if not isinstance(root_name, str):
        raise ValueError("FCKEY 原始目录名称无效。")
    validate_archive_paths([root_name])
    if len(root_name.replace("\\", "/").split("/")) != 1:
        raise ValueError("FCKEY 原始目录名称必须是单一目录名。")
    first_layer, second_layer = metadata.get("first_layer"), metadata.get("second_layer")
    if not isinstance(first_layer, dict) or first_layer.get("format") != "7z" or first_layer.get("encryption") != "AES-256":
        raise ValueError("FCKEY 第一层归档信息无效。")
    if (not isinstance(second_layer, dict) or second_layer.get("format") != "RAR5"
            or second_layer.get("encryption") != "AES-256" or second_layer.get("split") is not False):
        raise ValueError("FCKEY 第二层归档信息无效。")
    volumes = first_layer.get("volumes")
    if not isinstance(volumes, list) or not volumes:
        raise ValueError("FCKEY 中缺少第一层分卷清单。")
    volume_names = []
    for item in volumes:
        if not isinstance(item, dict):
            raise ValueError("FCKEY 分卷清单格式无效。")
        name, size, digest = item.get("name"), item.get("size"), item.get("sha256")
        if not isinstance(name, str) or not name or "/" in name or "\\" in name:
            raise ValueError("FCKEY 分卷文件名无效。")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ValueError("FCKEY 分卷大小无效。")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            raise ValueError("FCKEY 分卷 SHA-256 无效。")
        volume_names.append(name)
    validate_archive_paths(volume_names)
    source_files = metadata.get("source_files")
    if not isinstance(source_files, list):
        raise ValueError("FCKEY 原始文件清单无效。")
    for record in source_files:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise ValueError("FCKEY 原始文件记录无效。")
        size, digest = record.get("size"), record.get("sha256")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ValueError("FCKEY 原始文件大小无效。")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            raise ValueError("FCKEY 原始文件 SHA-256 无效。")
    validate_archive_paths([record["path"] for record in source_files])
    salt_text = metadata.get("archive_salt")
    if not isinstance(salt_text, str):
        raise ValueError("FCKEY 归档盐无效。")
    salt = base64.b64decode(salt_text, validate=True)
    if len(salt) != 16:
        raise ValueError("FCKEY 归档盐长度无效。")
    return metadata


class ArchiveService:
    """Create and restore the agreed two-layer package format."""

    def __init__(self, seven_zip: str | None = None, winrar: str | None = None,
                 performance_profile: str = "balanced", max_threads: int | None = None,
                 dictionary_size: str = "64k"):
        self.performance = performance_settings(performance_profile, max_threads=max_threads)
        self.dictionary_size = normalize_dictionary_size(dictionary_size)
        self.seven_zip = find_7z(seven_zip)
        self.winrar = find_rar(winrar)
        if not self.seven_zip:
            raise RuntimeError("未找到 7-Zip。请在设置中指定 7z.exe 路径。")
        if not self.winrar:
            raise RuntimeError("未找到 WinRAR 命令行工具 rar.exe，请安装 WinRAR 或在设置中指定路径。")

    def create(self, source: Path, output_dir: Path, name: str, master_password: str,
               video: Path | None = None, on_output=None, cancel_event=None,
               second_password: str | None = None, repeat_password: bool = True) -> Path:
        source_input = Path(source)
        if source_input.is_symlink() or not source_input.is_dir():
            raise ValueError("双层归档要求选择一个原始文件夹作为输入。")
        source, output_dir = source_input.resolve(), Path(output_dir).resolve()
        if output_dir.is_relative_to(source):
            raise ValueError("输出目录不能放在待压缩的输入文件夹内部。")
        if not master_password:
            raise ValueError("必须设置第一层密码。")
        password2 = master_password if repeat_password else (second_password or "")
        if not password2:
            raise ValueError("请设置第二层密码。")
        validate_package_name(name)
        if video is not None and (Path(video).is_symlink() or not Path(video).is_file()):
            raise ValueError("请选择有效且非符号链接的预览视频。")

        output_dir.mkdir(parents=True, exist_ok=True)
        final_suffix = Path(video).suffix.lower() if video is not None else ".rar"
        final_path = output_dir / f"{name}{final_suffix}"
        key_path = output_dir / f"{name}.fckey"
        if final_path.exists():
            raise FileExistsError(f"输出文件已存在：{final_path}")
        if key_path.exists():
            raise FileExistsError(f"Reader 密钥文件已存在：{key_path}")

        stage_started = time.monotonic()
        plan = inspect_source(source)
        source_files = build_file_manifest(source, cancel_event)
        if on_output:
            on_output(f"[性能] 文件扫描与清单：{time.monotonic() - stage_started:.1f} 秒")
        salt = os.urandom(16)
        password1 = derive_archive_password(master_password, salt, 1)
        rar_password = derive_archive_password(password2, salt, 2)

        with tempfile.TemporaryDirectory(prefix="fc-create-") as temp_name:
            work = Path(temp_name)
            volume_base = work / f"{source.name}.7z"
            command = [self.seven_zip, "a", "-t7z",
                       f"-mx={self.performance['compression_level']}", "-mhe=on", "-bsp1",
                       f"-mmt={self.performance['threads']}",
                       # The dictionary is a persistent user setting and is passed
                       # directly to LZMA2; fb and solid block follow the 7-Zip profile.
                       f"-m0=lzma2:d={self.dictionary_size}:fb=32", "-ms=16m",
                       f"-p{password1}", "-y"]
            if plan.volume_bytes:
                command.append(f"-v{plan.volume_bytes}b")
            command.append(str(volume_base))
            command.append(source.name)
            if on_output:
                on_output(
                    f"[参数] LZMA2 · 字典 {self.dictionary_size.upper()} · "
                    f"固实块 16 MB · {self.performance['threads']} 线程 · "
                    f"压缩等级 {self.performance['compression_level']}"
                )
            stage_started = time.monotonic()
            run_checked(command, on_output=on_output, cancel_event=cancel_event, cwd=source.parent)
            if on_output:
                on_output(f"[性能] 第一层 7-Zip：{time.monotonic() - stage_started:.1f} 秒")

            stage_started = time.monotonic()
            volumes = sorted(work.glob(volume_base.name + ".*"))
            if not volumes and volume_base.is_file():
                volumes = [volume_base]
            if not volumes:
                raise RuntimeError("7-Zip 未生成任何分卷文件。")

            volume_folder = work / source.name
            volume_folder.mkdir()
            volume_records = []
            for volume in volumes:
                target = volume_folder / volume.name
                shutil.move(str(volume), str(target))
                volume_records.append({
                    "name": target.name,
                    "size": target.stat().st_size,
                    "sha256": sha256_file(target, cancel_event),
                })
            if on_output:
                on_output(f"[性能] 分卷整理与 SHA-256：{time.monotonic() - stage_started:.1f} 秒")

            rar_path = work / OUTER_ARCHIVE
            # The RAR layer contains already-compressed 7z volumes. Store them
            # without recompression: this preserves RAR5 encryption while avoiding
            # wasted CPU time and the RAR dictionary-size incompatibility.
            rar_command = [self.winrar, "a", "-ma5", "-m0", "-r",
                           f"-mt{self.performance['threads']}",
                           "-hp" + rar_password, "-y", str(rar_path), volume_folder.name]
            stage_started = time.monotonic()
            run_checked(rar_command, on_output=on_output, cancel_event=cancel_event, cwd=work)
            if on_output:
                on_output(f"[性能] 第二层 WinRAR：{time.monotonic() - stage_started:.1f} 秒")
            if not rar_path.is_file():
                raise RuntimeError("WinRAR 未生成第二层 RAR 文件。")

            # The RAR now contains every first-layer volume. Remove the staged
            # volume copies immediately to reduce peak temporary-disk usage.
            shutil.rmtree(volume_folder)

            metadata = {
                "format": "FAKE-COMPRESSION-FCKEY-PAYLOAD",
                "version": 1,
                "source_root": source.name,
                "original_password1": master_password,
                "original_password2": password2,
                "archive_salt": base64.b64encode(salt).decode("ascii"),
                "first_layer": {"format": "7z", "encryption": "AES-256", "split": bool(plan.volume_bytes),
                                "volumes": volume_records},
                "second_layer": {"format": "RAR5", "encryption": "AES-256", "split": False},
                "source_files": source_files,
            }
            metadata_blob = encode_fckey(
                json.dumps(metadata, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                master_password, password2,
            )
            outer_zip = work / "outer-package.zip"
            # The third-layer ZIP contains only the encrypted RAR payload.
            # Its authenticated metadata lives in one sidecar .fckey file.
            # RAR is already encrypted and effectively incompressible. Store it as-is;
            # DEFLATE would spend CPU trying to recompress ciphertext for no gain.
            with zipfile.ZipFile(outer_zip, "w", compression=zipfile.ZIP_STORED) as package:
                package.write(rar_path, OUTER_ARCHIVE)
            # The third-layer ZIP is complete; the intermediate RAR is no
            # longer needed. Keep only one copy of the encrypted payload.
            rar_path.unlink()

            staged_key = key_path.with_name(key_path.name + ".partial")
            stage_started = time.monotonic()
            try:
                if video is not None:
                    # Preserve the MP4 polyhedron: video bytes stay at the front,
                    # followed by the complete ZIP payload.
                    create_polyhedron(Path(video), outer_zip, final_path, cancel_event)
                else:
                    staged_output = output_dir / (final_path.name + ".partial")
                    try:
                        shutil.copy2(outer_zip, staged_output)
                        os.replace(staged_output, final_path)
                    finally:
                        if staged_output.exists():
                            staged_output.unlink()

                staged_key.write_bytes(metadata_blob)
                if cancel_event and cancel_event.is_set():
                    raise RuntimeError("任务已取消。")
                os.replace(staged_key, key_path)
                if on_output:
                    on_output(f"[性能] 第三层封装与输出：{time.monotonic() - stage_started:.1f} 秒")
            except Exception:
                staged_key.unlink(missing_ok=True)
                final_path.unlink(missing_ok=True)
                raise
        return final_path

    def extract(self, package_path: Path, output_dir: Path, master_password: str,
                on_output=None, cancel_event=None, second_password: str | None = None,
                repeat_password: bool = True) -> Path:
        package_path, output_dir = Path(package_path).resolve(), Path(output_dir).resolve()
        if not package_path.is_file():
            raise FileNotFoundError(package_path)
        password2 = master_password if repeat_password else (second_password or "")
        if not master_password or not password2:
            raise ValueError("请输入两层密码。")
        output_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="fc-extract-") as temp_name:
            work = Path(temp_name)
            zip_path = work / "outer-package.zip"
            # New packages are plain ZIP files named .rar. Keep legacy video
            # wrapper reading for packages made by earlier Beta builds.
            if zipfile.is_zipfile(package_path):
                shutil.copy2(package_path, zip_path)
            else:
                try:
                    extract_polyhedron_payload(package_path, zip_path, cancel_event)
                except ValueError as exc:
                    raise ValueError("文件既不是有效的第三层 ZIP 封装，也不是旧版视频伪装包。") from exc

            if not zipfile.is_zipfile(zip_path):
                raise ValueError("外层打包文件已损坏。")
            with zipfile.ZipFile(zip_path, "r") as package:
                names = package.namelist()
                validate_archive_paths(names)
                if names == [OUTER_ARCHIVE]:
                    # New layout: metadata is stored once, beside the package.
                    key_path = package_path.with_suffix(".fckey")
                    if not key_path.is_file():
                        raise FileNotFoundError(
                            f"缺少配套 Reader 密钥文件：{key_path.name}"
                        )
                    metadata_blob = key_path.read_bytes()
                elif sorted(names) == sorted([OUTER_METADATA, OUTER_ARCHIVE]):
                    # Backward compatibility for older packages.
                    metadata_blob = package.read(OUTER_METADATA)
                else:
                    raise ValueError("外层包内容不符合 Fake-Compression 固定布局。")
                rar_path = work / OUTER_ARCHIVE
                rar_path.write_bytes(package.read(OUTER_ARCHIVE))

            raw = decode_fckey(metadata_blob, master_password, password2)
            try:
                metadata = validate_fckey_metadata(json.loads(raw.decode("utf-8")))
            except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
                raise ValueError(f"FCKEY 元数据无效：{exc}") from exc
            root_name = metadata["source_root"]
            salt = base64.b64decode(metadata["archive_salt"], validate=True)

            rar_password = derive_archive_password(password2, salt, 2)
            first_password = derive_archive_password(master_password, salt, 1)

            listing = []
            run_checked([self.winrar, "lb", "-hp" + rar_password, str(rar_path)],
                        on_output=listing.append, cancel_event=cancel_event)
            validate_archive_paths(listing)
            rar_stage = work / "rar-stage"
            rar_stage.mkdir()
            run_checked([self.winrar, "x", "-ibck", "-y",
                         f"-mt{self.performance['threads']}", "-hp" + rar_password,
                         str(rar_path), str(rar_stage) + os.sep],
                        on_output=on_output, cancel_event=cancel_event)
            volume_dir = rar_stage / root_name
            if not volume_dir.is_dir():
                raise ValueError("第二层 RAR 中缺少预期的分卷目录。")

            for record in metadata["first_layer"]["volumes"]:
                candidate = volume_dir / record["name"]
                if not candidate.is_file() or candidate.stat().st_size != record["size"]:
                    raise ValueError(f"第一层分卷缺失或大小不匹配：{record['name']}")
                if sha256_file(candidate, cancel_event) != record["sha256"]:
                    raise ValueError(f"第一层分卷完整性校验失败：{record['name']}")

            first_volume = volume_dir / metadata["first_layer"]["volumes"][0]["name"]
            seven_listing = []
            run_checked([self.seven_zip, "l", "-slt", str(first_volume), f"-p{first_password}"],
                        on_output=seven_listing.append, cancel_event=cancel_event)
            member_paths = [line[7:] for line in seven_listing if line.startswith("Path = ")]
            if member_paths:
                member_paths = member_paths[1:]
            validate_archive_paths(member_paths)
            if any(line.startswith(("Symbolic Link = ", "Hard Link = ")) for line in seven_listing):
                raise ValueError("第一层压缩包包含链接条目，已拒绝恢复。")

            restored_stage = work / "restored"
            restored_stage.mkdir()
            run_checked([self.seven_zip, "x", "-bsp1",
                         f"-mmt={self.performance['threads']}", str(first_volume),
                         f"-o{restored_stage}", f"-p{first_password}", "-y"],
                        on_output=on_output, cancel_event=cancel_event)
            verify_extracted_files(restored_stage, metadata["source_files"], cancel_event)
            restored_root = restored_stage / root_name
            if not restored_root.is_dir():
                raise ValueError("恢复内容中缺少原始文件夹。")
            destination = output_dir / root_name
            if destination.exists():
                raise FileExistsError(f"恢复目标已存在：{destination}")
            shutil.move(str(restored_root), str(destination))
            return destination

    def create_batch(self, source_root: Path, output_dir: Path, master_password: str,
                     on_output=None, cancel_event=None, second_password: str | None = None,
                     repeat_password: bool = True, video: Path | None = None) -> list[dict]:
        """Create one independent package for each immediate child directory."""
        root = Path(source_root).resolve()
        if not root.is_dir():
            raise NotADirectoryError(root)
        folders = sorted((item for item in root.iterdir() if item.is_dir() and not item.is_symlink()),
                         key=lambda item: item.name.casefold())
        if not folders:
            raise ValueError("批量压缩目录中没有可处理的子文件夹。")
        results = []
        for folder in folders:
            if cancel_event and cancel_event.is_set():
                from .tools import OperationCancelled
                raise OperationCancelled("批量任务已取消。")
            try:
                result = self.create(
                    folder, output_dir, folder.name, master_password,
                    video=video, on_output=on_output, cancel_event=cancel_event,
                    second_password=second_password, repeat_password=repeat_password,
                )
                results.append({"source": folder.name, "success": True, "output": str(result)})
            except Exception as exc:
                results.append({"source": folder.name, "success": False, "error": str(exc)})
        return results

    def extract_batch(self, package_paths: list[Path], output_dir: Path, master_password: str,
                      on_output=None, cancel_event=None, second_password: str | None = None,
                      repeat_password: bool = True) -> list[dict]:
        """Restore multiple packages independently; report failures without stopping the batch."""
        # Sidecar .fckey files are metadata, not standalone packages.
        packages = [Path(item) for item in package_paths if Path(item).suffix.lower() != ".fckey"]
        skipped = len(package_paths) - len(packages)
        if skipped and on_output:
            on_output(f"[提示] 已自动忽略 {skipped} 个 .fckey 配套文件；请选择对应的 .rar / .mp4 成品恢复。")
        if not packages:
            raise ValueError("没有可恢复的压缩成品。请只选择 .rar 或 .mp4 文件，不要单独选择 .fckey。")
        results = []
        for package in packages:
            if cancel_event and cancel_event.is_set():
                from .tools import OperationCancelled
                raise OperationCancelled("批量任务已取消。")
            package = Path(package)
            try:
                result = self.extract(
                    package, output_dir, master_password,
                    on_output=on_output, cancel_event=cancel_event,
                    second_password=second_password, repeat_password=repeat_password,
                )
                results.append({"package": str(package), "success": True, "output": str(result)})
            except Exception as exc:
                results.append({"package": str(package), "success": False, "error": str(exc)})
        return results
