"""External archiver discovery and subprocess helpers."""
import shutil
import subprocess
from pathlib import Path

def find_7z(configured: str | None = None) -> str | None:
    candidates = [configured, shutil.which("7z"), shutil.which("7z.exe"),
        r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate))
    return None

def run_checked(command: list[str], on_output=None) -> None:
    """Run without a shell. Never log the command: it may contain a password."""
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", shell=False)
    assert process.stdout is not None
    for line in process.stdout:
        if on_output:
            on_output(line.rstrip())
    code = process.wait()
    if code:
        raise RuntimeError(f"External archiver failed (exit code {code}).")
