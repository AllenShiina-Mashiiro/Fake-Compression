import sys
import threading
import time

import pytest

from fake_compression.tools import OperationCancelled, run_checked


def test_run_checked_streams_carriage_return_progress():
    output = []
    run_checked(
        [sys.executable, "-c", "import sys; sys.stdout.write(' 7%\\r 42%\\n')"],
        on_output=output.append,
    )
    assert output == ["7%", "42%"]


def test_run_checked_reports_nonzero_exit():
    with pytest.raises(RuntimeError, match="退出代码"):
        run_checked([sys.executable, "-c", "raise SystemExit(9)"])


def test_run_checked_can_be_cancelled():
    cancelled = threading.Event()
    timer = threading.Timer(0.35, cancelled.set)
    timer.start()
    started = time.monotonic()
    try:
        with pytest.raises(OperationCancelled):
            run_checked(
                [sys.executable, "-c", "import time; print('starting', flush=True); time.sleep(20)"],
                cancel_event=cancelled,
            )
    finally:
        timer.cancel()
    assert time.monotonic() - started < 5
