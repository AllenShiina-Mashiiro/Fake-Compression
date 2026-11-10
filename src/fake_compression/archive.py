"""7-Zip archive creation and extraction."""
import base64
import os
import shutil
from pathlib import Path

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
        source, output_dir = source.resolve(), output_dir.resolve()
        if not source.exists() or source.is_symlink():
            raise FileNotFoundError(source)
        if source.is_dir() and output_dir.is_relative_to(source):
            raise ValueError("输出目录不能放在待压缩的输入文件夹内部。")
        if not master_password:
            raise ValueError("必须设置主密码。")
        if not name or Path(name).name != name or name in {".", ".."}:
            raise ValueError("包名称必须是简单文件名，不能包含路径。")
        if video and (not video.is_file() or video.resolve() == source):
            raise ValueError("请选择有效且独立的预览视频文件。")

        output_dir.mkdir(parents=True, exist_ok=True)
        fc_path = output_dir / f"{name}.fc"
        archive_base = output_dir / f"{name}.7z"
        if fc_path.exists() or archive_base.exists() or list(output_dir.glob(f"{name}.7z.*")):
            raise FileExistsError("同名输出已存在。请更换包名称或先移走旧文件，避免覆盖。")

        plan = inspect_source(source)
        salt = os.urandom(16)
        password = archive_password(derive_key(master_password, salt))
        command = [self.seven_zip, "a", "-t7z", "-mx=5", "-mhe=on", "-bsp1",
                   f"-p{password}", "-y"]
        if plan.volume_bytes:
            command.append(f"-v{plan.volume_bytes}b")
        command.extend([str(archive_base), str(source)])
        run_checked(command, on_output=on_output, cancel_event=cancel_event)

        parts = sorted(p for p in output_dir.glob(f"{name}.7z.*") if p.is_file())
        if not parts and archive_base.is_file():
            parts = [archive_base]
        if not parts:
            raise RuntimeError("7-Zip 已结束，但没有找到生成的压缩包分卷。")

        payload = {
            "format": "FAKE-COMPRESSION-PAYLOAD",
            "version": 1,
            "archive_base": archive_base.name,
            "salt": base64.b64encode(salt).decode("ascii"),
            "parts": [{"name": p.name, "size": p.stat().st_size, "sha256": sha256_file(p)}
                      for p in parts],
            "video": None,
        }
        if video:
            target = output_dir / video.name
            if target.exists() and target.resolve() != video.resolve():
                raise FileExistsError(f"预览视频目标文件已存在：{target}")
            if target.resolve() != video.resolve():
                shutil.copy2(video, target)
            payload["video"] = target.name
            payload["video_sha256"] = sha256_file(target)

        write_manifest(fc_path, payload, master_password)
        return fc_path

    def extract(self, fc_path: Path, output_dir: Path, master_password: str,
                on_output=None, cancel_event=None) -> Path:
        fc_path, output_dir = fc_path.resolve(), output_dir.resolve()
        payload = read_manifest(fc_path, master_password)
        salt = base64.b64decode(payload["salt"], validate=True)
        password = archive_password(derive_key(master_password, salt))
        verify_parts(fc_path.parent, payload["parts"])
        first_part = fc_path.parent / payload["parts"][0]["name"]
        output_dir.mkdir(parents=True, exist_ok=True)
        command = [self.seven_zip, "x", "-bsp1", str(first_part),
                   f"-o{output_dir}", f"-p{password}", "-y"]
        run_checked(command, on_output=on_output, cancel_event=cancel_event)
        return output_dir
