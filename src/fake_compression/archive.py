"""7-Zip archive creation and safe, staged extraction."""
import base64
import os
import shutil
import tempfile
from pathlib import Path

from .archive_paths import validate_archive_paths
from .crypto import archive_password, derive_key
from .manifest import read_manifest, sha256_file, verify_parts, write_manifest
from .sizing import inspect_source
from .tools import find_7z, run_checked


class ArchiveService:
    def __init__(self, seven_zip: str | None = None):
        self.seven_zip = find_7z(seven_zip)
        if not self.seven_zip:
            raise RuntimeError("未找到 7-Zip。请在设置中指定 7z.exe 路径。")

    def create(self, source: Path, output_dir: Path, name: str, master_password: str,
               video: Path | None = None, on_output=None, cancel_event=None) -> Path:
        source_input = Path(source)
        if source_input.is_symlink():
            raise ValueError("不支持将符号链接作为压缩输入。")
        source, output_dir = source_input.resolve(), output_dir.resolve()
        if not source.exists():
            raise FileNotFoundError(source)
        if source.is_dir() and output_dir.is_relative_to(source):
            raise ValueError("输出目录不能放在待压缩的输入文件夹内部。")
        if not master_password:
            raise ValueError("必须设置主密码。")
        if not name or Path(name).name != name or name in {".", ".."}:
            raise ValueError("包名称必须是简单文件名，不能包含路径。")
        if video and (video.is_symlink() or not video.is_file() or video.resolve() == source):
            raise ValueError("请选择有效、非符号链接且独立的预览视频文件。")

        output_dir.mkdir(parents=True, exist_ok=True)
        fc_path = output_dir / f"{name}.fc"
        archive_base = output_dir / f"{name}.7z"
        if fc_path.exists() or archive_base.exists() or list(output_dir.glob(f"{name}.7z.*")):
            raise FileExistsError("同名输出已存在。请更换包名称或先移走旧文件，避免覆盖。")

        video_target = output_dir / video.name if video else None
        if video_target:
            if video_target.name == fc_path.name or video_target.name == archive_base.name:
                raise ValueError("预览视频文件名与压缩包文件名冲突，请先重命名视频。")
            if video_target.name.startswith(archive_base.name + "."):
                raise ValueError("预览视频文件名与分卷文件名冲突，请先重命名视频。")
            if video_target.exists() and video_target.resolve() != video.resolve():
                raise FileExistsError(f"预览视频目标文件已存在：{video_target}")

        plan = inspect_source(source)
        salt = os.urandom(16)
        password = archive_password(derive_key(master_password, salt))
        command = [self.seven_zip, "a", "-t7z", "-mx=5", "-mhe=on", "-bsp1",
                   f"-p{password}", "-y"]
        if plan.volume_bytes:
            command.append(f"-v{plan.volume_bytes}b")
        command.extend([str(archive_base), str(source)])
        try:
            run_checked(command, on_output=on_output, cancel_event=cancel_event)
        except Exception:
            for partial in [archive_base, *output_dir.glob(f"{name}.7z.*")]:
                try:
                    if partial.is_file():
                        partial.unlink()
                except OSError:
                    pass
            raise

        parts = sorted(p for p in output_dir.glob(f"{name}.7z.*") if p.is_file())
        if not parts and archive_base.is_file():
            parts = [archive_base]
        if not parts:
            raise RuntimeError("7-Zip 已结束，但没有找到生成的压缩包分卷。")

        copied_video = False
        try:
            payload = {
                "format": "FAKE-COMPRESSION-PAYLOAD",
                "version": 1,
                "archive_base": archive_base.name,
                "salt": base64.b64encode(salt).decode("ascii"),
                "parts": [{"name": p.name, "size": p.stat().st_size, "sha256": sha256_file(p, cancel_event)}
                          for p in parts],
                "video": None,
            }
            if video_target:
                if video_target.resolve() != video.resolve():
                    shutil.copy2(video, video_target)
                    copied_video = True
                payload["video"] = video_target.name
                payload["video_sha256"] = sha256_file(video_target, cancel_event)
            write_manifest(fc_path, payload, master_password)
        except Exception:
            for partial in [fc_path, archive_base, *output_dir.glob(f"{name}.7z.*")]:
                try:
                    if partial.is_file():
                        partial.unlink()
                except OSError:
                    pass
            if copied_video and video_target:
                try:
                    video_target.unlink()
                except OSError:
                    pass
            raise
        return fc_path

    def extract(self, fc_path: Path, output_dir: Path, master_password: str,
                on_output=None, cancel_event=None) -> Path:
        fc_path, output_dir = fc_path.resolve(), output_dir.resolve()
        payload = read_manifest(fc_path, master_password)
        salt = base64.b64decode(payload["salt"], validate=True)
        password = archive_password(derive_key(master_password, salt))
        verify_parts(fc_path.parent, payload["parts"], cancel_event)
        first_part = fc_path.parent / payload["parts"][0]["name"]

        # Inspect the member list before extraction. Links and paths that can
        # escape the staging directory are rejected rather than trusted.
        listing = []
        run_checked(
            [self.seven_zip, "l", "-slt", str(first_part), f"-p{password}"],
            on_output=listing.append,
            cancel_event=cancel_event,
        )
        member_paths = [line[7:] for line in listing if line.startswith("Path = ")]
        if member_paths:
            member_paths = member_paths[1:]  # First Path entry describes the archive itself.
        if any(line.startswith(("Symbolic Link = ", "Hard Link = ")) for line in listing):
            raise ValueError("压缩包包含链接条目，出于安全考虑已拒绝恢复。")
        validate_archive_paths(member_paths)

        output_dir.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".fc-staging-", dir=output_dir))
        try:
            command = [self.seven_zip, "x", "-bsp1", str(first_part),
                       f"-o{staging}", f"-p{password}", "-y"]
            run_checked(command, on_output=on_output, cancel_event=cancel_event)

            staged_items = list(staging.iterdir())
            collisions = [item.name for item in staged_items if (output_dir / item.name).exists()]
            if collisions:
                joined = "、".join(collisions[:5])
                raise FileExistsError(f"恢复目录中已有同名文件或文件夹：{joined}")
            for item in staged_items:
                shutil.move(str(item), str(output_dir / item.name))
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        return output_dir
