"""External archiver discovery, performance profiles and cancellable subprocess helpers."""
import ctypes
import queue
import shutil
import subprocess
import threading
from pathlib import Path


class OperationCancelled(RuntimeError):
    """Raised when the user cancels an active archive operation."""


SUPPORTED_DICTIONARY_SIZES = (
    "64k", "1m", "2m", "4m", "8m", "16m", "32m",
    "64m", "128m", "256m", "512m",
)


def normalize_dictionary_size(value: str | None) -> str:
    """Validate and normalize an LZMA2 dictionary size for the 7-Zip CLI."""
    normalized = str(value or "64k").strip().lower().replace(" ", "")
    if normalized not in SUPPORTED_DICTIONARY_SIZES:
        raise ValueError(f"不支持的 LZMA2 字典大小：{value}")
    return normalized


def available_memory_gib() -> float:
    """Return approximate physical memory in GiB without an optional dependency."""
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return status.ullAvailPhys / (1024 ** 3)
    except (AttributeError, OSError):
        pass
    return 4.0


def performance_settings(profile: str = "balanced", max_threads: int | None = None) -> dict:
    """Resolve a user-facing profile into real 7-Zip/WinRAR thread and dictionary settings."""
    cpu = max(1, __import__("os").cpu_count() or 1)
    memory = available_memory_gib()
    thread_ceiling = max(1, min(cpu, int(max_threads))) if max_threads else cpu
    profiles = {
        # compression_level is the real 7-Zip -mx level (1 = fastest, 9 = smallest).
        "eco": (1, 32, 5),
        "balanced": (thread_ceiling, 64, 3),
        "fast": (thread_ceiling, 128, 1),
        "max": (thread_ceiling, 256, 1),
    }
    if profile == "auto":
        # Reserve most memory for the OS and other applications. Scale worker
        # threads with currently available RAM as well as logical CPU count.
        memory_limited_threads = max(1, int(memory / 1.5))
        threads = max(1, min(thread_ceiling, memory_limited_threads))
        requested_mb = 128 if threads >= 4 else 64 if threads >= 2 else 32
        compression_level = 1 if threads >= 4 else 3
    else:
        threads, requested_mb, compression_level = profiles.get(profile, profiles["balanced"])
    # Keep the dictionary conservative relative to currently available RAM.
    memory_cap_mb = max(16, int(memory * 1024 * 0.20 / threads))
    dictionary_mb = min(requested_mb, memory_cap_mb)
    return {
        "threads": threads,
        "dictionary_mb": dictionary_mb,
        "compression_level": compression_level,
        "available_memory_gib": memory,
    }


def find_7z(configured: str | None = None) -> str | None:
    candidates = [
        configured, shutil.which("7z"), shutil.which("7z.exe"),
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate))
    return None


def find_rar(configured: str | None = None) -> str | None:
    """Find the WinRAR console executable (rar.exe)."""
    candidates = [
        configured, shutil.which("rar"), shutil.which("rar.exe"),
        r"C:\Program Files\WinRAR\rar.exe",
        r"C:\Program Files (x86)\WinRAR\rar.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate))
    return None


def run_checked(command: list[str], on_output=None, cancel_event=None, cwd=None) -> None:
    """Run without a shell, stream console output and support responsive cancellation.

    The command is intentionally never logged: 7-Zip's -p argument contains a
    derived archive password and may be visible to local process inspection.
    """
    if cancel_event and cancel_event.is_set():
        raise OperationCancelled("任务已取消。")
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace", shell=False,
        cwd=str(cwd) if cwd else None, bufsize=1,
    )
    output_queue = queue.Queue()

    def read_output():
        assert process.stdout is not None
        try:
            while True:
                char = process.stdout.read(1)
                if not char:
                    break
                output_queue.put(char)
        finally:
            output_queue.put(None)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    pending = ""
    eof = False
    try:
        while not eof or process.poll() is None:
            if cancel_event and cancel_event.is_set():
                try:
                    process.terminate()
                except OSError:
                    pass
                try:
                    process.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise OperationCancelled("任务已取消。")
            try:
                char = output_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if char is None:
                eof = True
                if pending and on_output:
                    on_output(pending.strip())
                pending = ""
            elif char in ("\r", "\n"):
                if pending and on_output:
                    on_output(pending.strip())
                pending = ""
            else:
                pending += char
        code = process.wait()
        if cancel_event and cancel_event.is_set():
            raise OperationCancelled("任务已取消。")
        if code:
            raise RuntimeError(f"外部压缩程序执行失败（退出代码 {code}）。")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        reader.join(timeout=1)
        if process.stdout:
            process.stdout.close()
