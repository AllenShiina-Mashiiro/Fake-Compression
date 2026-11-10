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
            raise RuntimeError("7-Zip was not found. Set its path in Settings.")

    def create(self, source: Path, output_dir: Path, name: str, master_password: str,
               video: Path | None = None, on_output=None) -> Path:
        source, output_dir = source.resolve(), output_dir.resolve()
        if not source.exists() or source.is_symlink():
            raise FileNotFoundError(source)
        if source.is_dir() and output_dir.is_relative_to(source):
            raise ValueError("Output directory cannot be inside the input folder.")
        if not master_password:
            raise ValueError("A master password is required.")
        if not name or Path(name).name != name or name in {".", ".."}:
            raise ValueError("Package name must be a simple file name.")
        if video and (not video.is_file() or video.resolve() == source):
            raise ValueError("Choose a valid, separate preview video.")
        output_dir.mkdir(parents=True, exist_ok=True)
        plan = inspect_source(source)
        salt = os.urandom(16)
        password = archive_password(derive_key(master_password, salt))
        archive_base = output_dir / f"{name}.7z"
        command = [self.seven_zip, "a", "-t7z", "-mx=5", "-mhe=on", f"-p{password}", "-y"]
        if plan.volume_bytes:
            command.append(f"-v{plan.volume_bytes}b")
        command.extend([str(archive_base), str(source)])
        run_checked(command, on_output)
        parts = sorted(p for p in output_dir.glob(f"{name}.7z.*") if p.is_file())
        if not parts:
            # Non-split 7z archives use the exact base filename.
            if archive_base.is_file():
                parts = [archive_base]
            else:
                raise RuntimeError("7-Zip completed but no archive parts were found.")
        payload = {"format":"FAKE-COMPRESSION-PAYLOAD", "version":1,
            "archive_base":archive_base.name, "salt":base64.b64encode(salt).decode("ascii"),
            "parts":[{"name":p.name,"size":p.stat().st_size,"sha256":sha256_file(p)} for p in parts],
            "video":None}
        if video:
            target = output_dir / video.name
            if target.exists() and target.resolve() != video.resolve():
                raise FileExistsError(f"Preview destination already exists: {target}")
            if target.resolve() != video.resolve():
                shutil.copy2(video, target)
            payload["video"] = target.name
            payload["video_sha256"] = sha256_file(target)
        fc_path = output_dir / f"{name}.fc"
        write_manifest(fc_path, payload, master_password)
        return fc_path

    def extract(self, fc_path: Path, output_dir: Path, master_password: str, on_output=None) -> Path:
        fc_path, output_dir = fc_path.resolve(), output_dir.resolve()
        payload = read_manifest(fc_path, master_password)
        salt = base64.b64decode(payload["salt"], validate=True)
        password = archive_password(derive_key(master_password, salt))
        verify_parts(fc_path.parent, payload["parts"])
        first_part = fc_path.parent / payload["parts"][0]["name"]
        output_dir.mkdir(parents=True, exist_ok=True)
        command = [self.seven_zip, "x", str(first_part), f"-o{output_dir}", f"-p{password}", "-y"]
        run_checked(command, on_output)
        return output_dir
