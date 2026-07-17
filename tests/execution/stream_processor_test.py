"""Tests for runtime stream processing helpers."""

from __future__ import annotations

import threading
import time

from slop_code.execution import stream_processor
from slop_code.execution.stream_processor import ensure_string, process_stream


def test_ensure_string_preserves_text_around_invalid_utf8_bytes() -> None:
    decoded = ensure_string(b'{"type":"message_update","data":"ok"}\xff\n')

    assert '{"type":"message_update","data":"ok"}' in decoded
    assert decoded.endswith("\n")


def _drain(gen):
    events = []
    try:
        while True:
            events.append(next(gen))
    except StopIteration as exc:
        return events, exc.value


def test_inactivity_watchdog_reaps_a_stalled_stream(monkeypatch) -> None:
    """A stream that goes silent with the process still 'alive' must be reaped
    on the inactivity deadline, not left to hang. Regression for the tail-stall
    that used to deadlock the whole run on an unbounded pump join."""
    monkeypatch.setattr(stream_processor, "STREAM_JOIN_GRACE", 0.2)

    stall = threading.Event()

    def stalling_stream():
        yield (b'{"type":"message_end"}\n', b"")
        stall.wait()  # blocks like a pump stuck on a half-dead pipe read
        yield (b"", b"")

    start = time.monotonic()
    gen = process_stream(stalling_stream(), timeout=3600, poll_fn=lambda: None,
                         inactivity_timeout=0.5)
    events, result = _drain(gen)
    elapsed = time.monotonic() - start
    stall.set()

    assert result.timed_out is True
    assert elapsed < 5  # inactivity 0.5s + join grace 0.2s, nowhere near 3600s
    assert len(events) == 1


def test_normal_completion_is_not_flagged_as_timed_out() -> None:
    """A stream that finishes on its own must not trip the watchdog."""
    def finishing_stream():
        yield (b"hello\n", b"")
        yield (b"", b"world\n")

    exit_codes = iter([None, None, 0])
    gen = process_stream(finishing_stream(), timeout=3600,
                         poll_fn=lambda: next(exit_codes, 0),
                         inactivity_timeout=30)
    events, result = _drain(gen)

    assert result.timed_out is False
    assert any(e.text == "hello\n" for e in events)
