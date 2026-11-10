"""QThread wrapper for long-running, cancellable archive operations."""
import re
from threading import Event

from PySide6.QtCore import QThread, Signal

from .tools import OperationCancelled


class TaskWorker(QThread):
    message = Signal(str)
    progress = Signal(int)
    succeeded = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, operation, *args, **kwargs):
        super().__init__()
        self.operation, self.args, self.kwargs = operation, args, kwargs
        self.cancel_event = Event()

    def cancel(self):
        self.cancel_event.set()

    def _handle_output(self, line: str):
        self.message.emit(line)
        match = re.search(r"(?:^|\s)(\d{1,3})%", line)
        if match:
            self.progress.emit(max(0, min(100, int(match.group(1)))))

    def run(self):
        try:
            result = self.operation(
                *self.args,
                on_output=self._handle_output,
                cancel_event=self.cancel_event,
                **self.kwargs,
            )
            self.progress.emit(100)
            self.succeeded.emit(result)
        except OperationCancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(str(exc))
