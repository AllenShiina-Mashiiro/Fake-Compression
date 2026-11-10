"""QThread wrapper for long-running archive operations."""
from PySide6.QtCore import QThread, Signal

class TaskWorker(QThread):
    message = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, operation, *args, **kwargs):
        super().__init__()
        self.operation, self.args, self.kwargs = operation, args, kwargs

    def run(self):
        try:
            result = self.operation(*self.args, on_output=self.message.emit, **self.kwargs)
            self.succeeded.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
