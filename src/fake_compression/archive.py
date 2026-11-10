"""Two-layer archive pipeline: 7z volumes -> encrypted RAR -> rename-safe ZIP/video payload."""
import base64
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from .archive_paths import validate_archive_paths, validate_package_name
from .crypto import archive_password, derive_key
from .fckey import decode_fckey, derive_archive_password, encode_fckey
from .manifest import build_file_manifest, sha256_file, verify_extracted_files
from .polyvideo import create_polyhedron, extract_polyhedron_payload
from .sizing import inspect_source
from .tools import find_7z, find_rar, run_checked


OUTER_METADATA = "metadata.fckey"
OUTER_ARCHIVE = "payload.rar"


class ArchiveService:
    """Create and restore the agreed two-layer package format."""

    def __init__(self, seven_zip: str | None = None, winrar: str | None = None):
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
        if video and (video.is_symlink() or not video.is_file()):
            raise ValueError("请选择有效且非符号链接的预览视频。")

        output_dir.mkdir(parents=True, exist_ok=True)
        final_path = output_dir / (f"{name}{video.suffix}" if video else f"{name}.fc")
        if final_path.exists():
            raise FileExistsError(f"输出文件已存在：{final_path}")
        if video and video.resolve() == final_path.resolve():
            raise ValueError("输出文件不能覆盖预览视频。")

        plan = inspect_source(source)
        source_files = build_file_manifest(source, cancel_event)
        salt = os.urandom(16)
        password1 = derive_archive_password(master_password, salt, 1)
        rar_password = derive_archive_password(password2, salt, 2)

        with tempfile.TemporaryDirectory(prefix="fc-create-") as temp_name:
            work = Path(temp_name)
            volume_base = work / f"{source.name}.7z"
            command = [self.seven_zip, "a", "-t7z", "-mx=5", "-mhe=on", "-bsp1",
                       f"-p{password1}", "-y"]
            if plan.volume_bytes:
                command.append(f"-v{plan.volume_bytes}b")
            command.append(str(volume_base))
            command.append(source.name)
            run_checked(command, on_output=on_output, cancel_event=cancel_event, cwd=source.parent)

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

            rar_path = work / OUTER_ARCHIVE
            rar_command = [self.winrar, "a", "-ma5", "-r", "-hp" + rar_password,
                           "-y", str(rar_path), volume_folder.name]
            run_checked(rar_command, on_output=on_output, cancel_event=cancel_event, cwd=work)
            if not rar_path.is_file():
                raise RuntimeError("WinRAR 未生成第二层 RAR 文件。")

            metadata = {
                "format": "FAKE-COMPRESSION-FCKEY-PAYLOAD",
                "version": 1,
                "source_root": source.name,
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
            with zipfile.ZipFile(outer_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as package:
                package.write(rar_path, OUTER_ARCHIVE)
                package.writestr(OUTER_METADATA, metadata_blob)

            if video:
                create_polyhedron(video, outer_zip, final_path)
            else:
                shutil.copy2(outer_zip, final_path)
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
            try:
                extract_polyhedron_payload(package_path, zip_path)
            except ValueError:
                # Ordinary ZIP packages are also supported. The extension is never trusted.
                if not zipfile.is_zipfile(package_path):
                    raise ValueError("文件既不是有效的多面体载荷，也不是外层 ZIP 包。")
                shutil.copy2(package_path, zip_path)

            if not zipfile.is_zipfile(zip_path):
                raise ValueError("外层打包文件已损坏。")
            with zipfile.ZipFile(zip_path, "r") as package:
                names = package.namelist()
                if sorted(names) != sorted([OUTER_METADATA, OUTER_ARCHIVE]):
                    raise ValueError("外层包内容不符合 Fake-Compression 固定布局。")
                validate_archive_paths(names)
                metadata_blob = package.read(OUTER_METADATA)
                rar_path = work / OUTER_ARCHIVE
                rar_path.write_bytes(package.read(OUTER_ARCHIVE))

            raw = decode_fckey(metadata_blob, master_password, password2)
            metadata = json.loads(raw.decode("utf-8"))
            if metadata.get("format") != "FAKE-COMPRESSION-FCKEY-PAYLOAD" or metadata.get("version") != 1:
                raise ValueError("不支持的 FCKEY 元数据版本。")
            salt = base64.b64decode(metadata["archive_salt"], validate=True)
            rar_password = derive_archive_password(password2, salt, 2)
            first_password = derive_archive_password(master_password, salt, 1)

            listing = []
            run_checked([self.winrar, "lb", "-hp" + rar_password, str(rar_path)],
                        on_output=listing.append, cancel_event=cancel_event)
            validate_archive_paths(listing)
            rar_stage = work / "rar-stage"
            rar_stage.mkdir()
            run_checked([self.winrar, "x", "-ibck", "-y", "-hp" + rar_password,
                         str(rar_path), str(rar_stage) + os.sep],
                        on_output=on_output, cancel_event=cancel_event)
            root_name = metadata["source_root"]
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
            run_checked([self.seven_zip, "x", "-bsp1", str(first_volume),
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
                     repeat_password: bool = True) -> list[dict]:
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
                    on_output=on_output, cancel_event=cancel_event,
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
        results = []
        for package in package_paths:
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
