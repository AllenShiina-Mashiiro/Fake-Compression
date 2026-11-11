"""QThread wrapper with live progress and remaining-time estimates."""
import re
import time
from threading import Event

from PySide6.QtCore import QThread, Signal

from .tools import OperationCancelled


class TaskWorker(QThread):
    message = Signal(str)
    progress = Signal(int)
    estimate = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, operation, *args, **kwargs):
        super().__init__()
        self.operation, self.args, self.kwargs = operation, args, kwargs
        self.cancel_event = Event()
        self._phase_started = None
        self._last_percent = None

    def cancel(self):
        self.cancel_event.set()

    def _handle_output(self, line: str):
        self.message.emit(line)
        match = re.search(r"(?:^|\s)(\d{1,3})%", line)
        if not match:
            return
        percent = max(0, min(100, int(match.group(1))))
        now = time.monotonic()
        if self._phase_started is None or (
            self._last_percent is not None and percent < self._last_percent
        ):
            self._phase_started = now
        self._last_percent = percent
        self.progress.emit(min(percent, 99))
        elapsed = max(0.0, now - self._phase_started)
        if percent >= 2 and percent < 100:
            remaining = elapsed * (100 - percent) / percent
            self.estimate.emit(
                f"当前阶段剩余约 {self._format_time(remaining)} · 已用 {self._format_time(elapsed)}"
            )
        elif percent >= 100:
            self.estimate.emit("当前阶段即将完成，正在校验/封装…")

    @staticmethod
    def _format_time(seconds):
        seconds = max(0, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"

    def run(self):
        try:
            result = self.operation(
                *self.args, on_output=self._handle_output,
                cancel_event=self.cancel_event, **self.kwargs,
            )
            self.progress.emit(100)
            self.estimate.emit("任务完成")
            self.succeeded.emit(result)
        except OperationCancelled:
            self.estimate.emit("任务已取消")
            self.cancelled.emit()
        except Exception as exc:
            self.estimate.emit("任务失败")
            self.failed.emit(str(exc))
