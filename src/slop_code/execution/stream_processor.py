"""Utilities for processing runtime output streams with threading.

This module provides utilities for handling streaming output from runtime processes
with proper threading and timeout management:

- **ensure_string**: Convert bytes to string with error handling
- **start_stream_pump**: Start threaded stream processing
- **make_timeout_fn**: Create timeout calculation functions
- **process_stream**: Main stream processing with timeout and filtering

The utilities support both Docker and local runtime streams, providing
consistent behavior across different execution environments with proper cleanup
and timeout handling.
"""

from __future__ import annotations

import os
import queue
import threading
import time
from collections.abc import Callable
from collections.abc import Generator
from collections.abc import Iterator
from typing import Literal

import structlog

from slop_code.execution.runtime import RuntimeEvent
from slop_code.execution.runtime import RuntimeResult

logger = structlog.get_logger(__name__)

DEFAULT_WAIT_TIMEOUT = 7200.0  # 2 hours

# Stream-inactivity watchdog. The agent `timeout` above is a wall-clock cap on the
# WHOLE run; it does not notice a stream that has simply gone silent, and — worse —
# a provider connection that stalls mid-stream can wedge the pump thread so the run
# never returns even after that cap fires (the join below used to be unbounded).
# This is an INDEPENDENT deadline: if no stdout/stderr event arrives for
# INACTIVITY_TIMEOUT seconds, the stream is reaped regardless of how much of the
# wall-clock cap remains. Default 180s — a model can think quietly, but three
# minutes of total silence on a chatty agent stream is a stall, not thinking.
# Override with SCB_STREAM_INACTIVITY_TIMEOUT_S (0 disables).
INACTIVITY_TIMEOUT = float(os.environ.get("SCB_STREAM_INACTIVITY_TIMEOUT_S", "180"))
# How long to wait for the pump thread to drain after we stop reading before giving
# up on it. The pump is a daemon blocked on a pipe read that only unblocks when the
# runtime kills the exec process; we must not block on it (that was the deadlock).
STREAM_JOIN_GRACE = float(os.environ.get("SCB_STREAM_JOIN_GRACE_S", "10"))


def ensure_string(data: bytes | str) -> str:
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return data


def start_stream_pump(
    stream: Iterator[tuple[bytes | str, bytes | str]],
    event_queue: queue.Queue[
        tuple[Literal["stdout", "stderr", "finished"], str | None]
    ],
    stop_event: threading.Event,
) -> threading.Thread:
    """Start a thread to pump a demuxed stream into an event queue.

    Args:
        stream: Iterator yielding (stdout, stderr) tuples
        event_queue: Queue to receive events
        stop_event: Event to check for early termination
        ensure_string: Function to convert bytes to string
    """

    def pump() -> None:
        """Pump demuxed stream to event queue."""
        for stdout, stderr in stream:
            if stdout:
                contents = ensure_string(stdout)
                event_queue.put(("stdout", contents))
            if stderr:
                contents = ensure_string(stderr)
                event_queue.put(("stderr", contents))
            if stop_event.is_set():
                break
        event_queue.put(("finished", None))

    thread = threading.Thread(target=pump, daemon=True)
    thread.start()
    return thread


def make_timeout_fn(
    timeout: float | None, start_time: float
) -> Callable[[], float]:
    deadline = start_time + (timeout or DEFAULT_WAIT_TIMEOUT)

    def timeout_fn() -> float:
        return deadline - time.monotonic()

    return timeout_fn


class _StreamAssembler:
    """Assemble one output stream (stdout or stderr) in O(total) time.

    The previous implementation did ``buf += payload`` per chunk and rescanned
    the ENTIRE accumulated buffer for the setup/agent split marker on every
    chunk. Both are O(n) per chunk, so a checkpoint that emits a large volume of
    output (e.g. a tool dumping megabytes) pinned a CPU core for many minutes in
    a hot loop — the real reason SCB runs appeared to "hang". Here chunks go into
    a list joined once, and the marker is searched only across the new chunk plus
    a marker-width overlap, so total work is linear.
    """

    def __init__(self, marker: str | None):
        self._marker = marker
        self._yielding = marker is None  # no marker => stream everything
        self._pre: list[str] = []        # chunks seen before the marker
        self._pre_len = 0                # total chars in self._pre
        self._tail = ""                  # last marker-1 chars, for a split marker
        self._out: list[str] = []        # chunks after the marker (or all if none)
        self._setup = ""                 # pre-marker text, captured at the split

    def feed(self, payload: str) -> str | None:
        """Consume a chunk; return the text to yield downstream, or None."""
        if self._yielding:
            self._out.append(payload)
            return payload if payload.strip() else None

        marker = self._marker
        assert marker is not None
        probe = self._tail + payload
        idx = probe.find(marker)
        if idx == -1:
            self._pre.append(payload)
            self._pre_len += len(payload)
            self._tail = probe[-(len(marker) - 1):] if len(marker) > 1 else ""
            return None

        # Marker found: reconstruct the full pre-marker buffer once and split.
        full = "".join(self._pre) + payload
        pos = (self._pre_len - len(self._tail)) + idx
        self._setup = full[:pos]
        after = full[pos + len(marker):]
        self._yielding = True
        self._pre = []
        self._tail = ""
        if after:
            self._out.append(after)
        return after if after.strip() else None

    def finalize(self) -> tuple[str, str]:
        """Return (main_output, setup_output), matching the original semantics:
        marker found -> (after-marker, before-marker); never found -> (all, "")."""
        if self._yielding:
            return "".join(self._out), self._setup
        return "".join(self._pre), ""


def process_stream(
    stream: Iterator[tuple[str | bytes, str | bytes]],
    timeout: float | None,
    poll_fn: Callable[[], int | None],
    yield_only_after: str | None = None,
    inactivity_timeout: float | None = None,
) -> Generator[RuntimeEvent, None, RuntimeResult]:
    if inactivity_timeout is None:
        inactivity_timeout = INACTIVITY_TIMEOUT
    logger.debug("Starting to consume events with timeout", timeout=timeout,
                 inactivity_timeout=inactivity_timeout)
    start_time = time.monotonic()
    timeout_fn = make_timeout_fn(timeout, start_time)
    last_event = time.monotonic()
    stop_event = threading.Event()
    event_queue: queue.Queue[
        tuple[Literal["stdout", "stderr", "finished"], str | None]
    ] = queue.Queue()
    thread = start_stream_pump(stream, event_queue, stop_event)
    stdout_asm = _StreamAssembler(yield_only_after)
    stderr_asm = _StreamAssembler(yield_only_after)
    timed_out = False

    def handle_event(
        kind: Literal["stdout", "stderr"],
        payload: str,
    ) -> Iterator[RuntimeEvent]:
        if kind == "stdout":
            text = stdout_asm.feed(payload)
            if text is not None:
                yield RuntimeEvent(kind="stdout", text=text)
            return

        if kind == "stderr":
            text = stderr_asm.feed(payload)
            if text is not None:
                yield RuntimeEvent(kind="stderr", text=text)
            return

        logger.error("Received unknown event", kind=kind, payload=payload)

    while (exit_code := poll_fn()) is None:
        if (remaining := timeout_fn()) <= 0:
            timed_out = True
            break

        # Independent inactivity deadline: silence for inactivity_timeout is a
        # stall, reaped without waiting out the (possibly 2-hour) wall-clock cap.
        if inactivity_timeout and inactivity_timeout > 0:
            idle_remaining = (last_event + inactivity_timeout) - time.monotonic()
            if idle_remaining <= 0:
                logger.warning("Stream inactivity timeout — reaping stalled stream",
                               inactivity_timeout=inactivity_timeout)
                timed_out = True
                break
            wait = min(remaining, idle_remaining)
        else:
            wait = remaining

        try:
            kind, payload = event_queue.get(timeout=wait)
        except queue.Empty:
            if (exit_code := poll_fn()) is not None:
                break
            continue

        last_event = time.monotonic()  # any event resets the inactivity clock

        if kind == "finished":
            logger.debug("Received finished event")
            break

        if payload is None:
            logger.error("Received empty stream event", kind=kind)
            break

        yield from handle_event(kind, payload)

    # Handle any remaining events in the queue
    while True:
        try:
            kind, payload = event_queue.get_nowait()
        except queue.Empty:
            break

        if kind == "finished":
            logger.debug("Received finished event")
            break

        if payload is None:
            logger.error("Received empty stream event", kind=kind)
            break

        yield from handle_event(kind, payload)

    elapsed = time.monotonic() - start_time
    stop_event.set()
    # BOUNDED join. The pump is a daemon blocked on a pipe read that only unblocks
    # once the runtime kills the exec process — which happens AFTER this function
    # returns. An unbounded join here therefore deadlocked the whole run on any
    # tail-stall. Give it a short grace to drain a clean finish, then proceed and
    # let the caller's teardown kill the exec process (closing the pipe).
    thread.join(timeout=STREAM_JOIN_GRACE)
    if thread.is_alive():
        logger.warning("Stream pump did not drain within grace; proceeding "
                       "(daemon thread, freed by exec-process teardown)",
                       grace=STREAM_JOIN_GRACE)

    exit_code = exit_code or poll_fn()
    if exit_code is None:
        exit_code = -1
    stdout, setup_stdout = stdout_asm.finalize()
    stderr, setup_stderr = stderr_asm.finalize()
    logger.debug(
        "Setup stdout", setup_stdout=setup_stdout, setup_stderr=setup_stderr
    )
    return RuntimeResult(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        setup_stdout=setup_stdout,
        setup_stderr=setup_stderr,
        elapsed=elapsed,
        timed_out=timed_out,
    )
