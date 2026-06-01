"""Threaded worker that runs a Reconstructor and pushes events onto a queue."""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from rebereal import ingest
from rebereal.logging_setup import CallbackHandler
from rebereal.pipeline import Reconstructor, RunSummary

log = logging.getLogger(__name__)


def drain_once(
    events_q: "queue.Queue",
    handler: Callable[[object], None],
    done_types: tuple[type, ...] = (),
) -> bool:
    """Drain every currently-pending event into `handler`.

    Returns True iff a terminal event was observed during this drain. The
    terminal types default to `DoneEvent`; pass `done_types` to recognise a
    different terminator (e.g. `IngestDoneEvent`). Callers that re-arm polling
    on `is_running()` would race with the worker thread pushing the final event
    and then exiting — so the caller should keep polling until this function
    returns True instead.
    """
    terminal = done_types or (DoneEvent,)
    saw_done = False
    try:
        while True:
            event = events_q.get_nowait()
            handler(event)
            if isinstance(event, terminal):
                saw_done = True
    except queue.Empty:
        pass
    return saw_done


@dataclass
class ProgressEvent:
    done: int
    total: int


@dataclass
class LogEvent:
    message: str


@dataclass
class DoneEvent:
    summary: RunSummary | None
    error: BaseException | None = None


@dataclass
class IngestDoneEvent:
    export_root: Path | None
    error: BaseException | None = None


Event = ProgressEvent | LogEvent | DoneEvent | IngestDoneEvent


class Worker:
    """Run `Reconstructor.run` on a background thread.

    Events are pushed to `self.events` and consumed on the Qt main thread by a
    `QTimer` that polls `drain_once`. The worker installs a log handler that
    forwards records onto the same queue so the GUI sees a unified event stream.
    """

    def __init__(self, reconstructor: Reconstructor) -> None:
        self.reconstructor = reconstructor
        self.events: queue.Queue[Event] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._log_handler: CallbackHandler | None = None
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """Request a cooperative stop; the run ends after the current post."""
        self._cancel.set()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("worker already running")

        self._log_handler = CallbackHandler(self._forward_log)
        logging.getLogger().addHandler(self._log_handler)

        self._thread = threading.Thread(target=self._run, name="rebereal-worker", daemon=True)
        self._thread.start()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # --- internals --------------------------------------------------------

    def _run(self) -> None:
        try:
            summary = self.reconstructor.run(
                progress_cb=self._on_progress,
                should_cancel=self._cancel.is_set,
            )
            self.events.put(DoneEvent(summary=summary))
        except BaseException as e:
            log.exception("worker failed")
            self.events.put(DoneEvent(summary=None, error=e))
        finally:
            if self._log_handler is not None:
                logging.getLogger().removeHandler(self._log_handler)
                self._log_handler = None

    def _on_progress(self, done: int, total: int) -> None:
        self.events.put(ProgressEvent(done=done, total=total))

    def _forward_log(self, message: str) -> None:
        self.events.put(LogEvent(message=message))


class IngestWorker:
    """Resolve a dropped/picked source to an export root on a background thread.

    Mirrors `Worker`: it pushes `ProgressEvent`s while extracting a zip and a
    terminal `IngestDoneEvent` carrying the resolved export root (or an error).
    Drained on the Qt main thread via `drain_once(..., (IngestDoneEvent,))`.
    """

    def __init__(self, selected: Path, dest: Path) -> None:
        self.selected = selected
        self.dest = dest
        self.events: queue.Queue[Event] = queue.Queue()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("ingest worker already running")
        self._thread = threading.Thread(target=self._run, name="rebereal-ingest", daemon=True)
        self._thread.start()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # --- internals --------------------------------------------------------

    def _run(self) -> None:
        try:
            root = ingest.prepare_source(self.selected, self.dest, self._on_progress)
            self.events.put(IngestDoneEvent(export_root=root))
        except BaseException as e:
            log.exception("ingest failed")
            self.events.put(IngestDoneEvent(export_root=None, error=e))

    def _on_progress(self, done: int, total: int) -> None:
        self.events.put(ProgressEvent(done=done, total=total))


# Re-exported for clarity in callers that need to type-check event handlers.
__all__: list[str] = [
    "Worker",
    "IngestWorker",
    "ProgressEvent",
    "LogEvent",
    "DoneEvent",
    "IngestDoneEvent",
    "Event",
    "drain_once",
]
_ = Any
