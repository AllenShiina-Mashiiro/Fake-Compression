"""External archiver discovery and cancellable subprocess helpers."""
import queue
import shutil
import subprocess
import threading
from pathlib import Path


class OperationCancelled(RuntimeError):
    """Raised when the user cancels an active archive operation."""


def find_7z(configured: str | None = None) -> str | None:
    candidates = [
        configured,
        shutil.which("7z"),
        shutil.which("7z.exe"),
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate))
    return None


def run_checked(command: list[str], on_output=None, cancel_event=None) -> None:
    """Run without a shell, stream console output and support responsive cancellation.

    The command is intentionally never logged: 7-Zip's -p argument contains a
    derived archive password and may be visible to local process inspection.
    """
    if cancel_event and cancel_event.is_set():
        raise OperationCancelled("任务已取消。")

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        bufsize=1,
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
                process.terminate()
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
        if process.stdout:
            process.stdout.close()
