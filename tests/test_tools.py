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


def test_performance_profiles_respect_cpu_and_memory(monkeypatch):
    import os
    import fake_compression.tools as tools

    monkeypatch.setattr(os, "cpu_count", lambda: 12)
    monkeypatch.setattr(tools, "available_memory_gib", lambda: 4.0)

    eco = tools.performance_settings("eco")
    balanced = tools.performance_settings("balanced")
    fast = tools.performance_settings("fast")
    maximum = tools.performance_settings("max")

    assert eco["threads"] == 1
    assert balanced["threads"] == 12
    assert fast["threads"] == 12
    assert maximum["threads"] == 12
    assert eco["compression_level"] == 5
    assert balanced["compression_level"] == 3
    assert fast["compression_level"] == 1
    assert maximum["compression_level"] == 1
    for profile in (eco, balanced, fast, maximum):
        assert profile["dictionary_mb"] >= 16
        assert profile["dictionary_mb"] * profile["threads"] <= 4.0 * 1024 * 0.20


def test_auto_performance_profile_adapts_to_cpu_and_memory(monkeypatch):
    import os
    import fake_compression.tools as tools

    monkeypatch.setattr(os, "cpu_count", lambda: 16)
    monkeypatch.setattr(tools, "available_memory_gib", lambda: 3.0)
    settings = tools.performance_settings("auto")
    assert settings["threads"] == 2
    assert settings["compression_level"] == 3
    assert settings["dictionary_mb"] * settings["threads"] <= 3.0 * 1024 * 0.20

    monkeypatch.setattr(tools, "available_memory_gib", lambda: 24.0)
    settings = tools.performance_settings("auto")
    assert settings["threads"] == 8
    assert settings["compression_level"] == 1



def test_configurable_thread_ceiling_respects_cpu_detection(monkeypatch):
    import os
    import fake_compression.tools as tools

    monkeypatch.setattr(os, "cpu_count", lambda: 64)
    monkeypatch.setattr(tools, "available_memory_gib", lambda: 128.0)

    assert tools.performance_settings("balanced", max_threads=20)["threads"] == 20
    assert tools.performance_settings("max", max_threads=32)["threads"] == 32
    assert tools.performance_settings("max", max_threads=64)["threads"] == 64

    monkeypatch.setattr(os, "cpu_count", lambda: 18)
    assert tools.performance_settings("max", max_threads=64)["threads"] == 18
    assert tools.performance_settings("max", max_threads=None)["threads"] == 18



def test_normalize_dictionary_size_accepts_7zip_lzma2_sizes():
    from fake_compression.tools import normalize_dictionary_size

    assert normalize_dictionary_size("64k") == "64k"
    assert normalize_dictionary_size("8M") == "8m"
    assert normalize_dictionary_size("512m") == "512m"


def test_normalize_dictionary_size_rejects_unsupported_values():
    from fake_compression.tools import normalize_dictionary_size

    with pytest.raises(ValueError, match="不支持"):
        normalize_dictionary_size("1024m")
