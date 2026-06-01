"""Threaded worker that runs a Reconstructor and pushes events onto a queue."""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from typing import Any, Callable

from rebereal.logging_setup import CallbackHandler
from rebereal.pipeline import Reconstructor, RunSummary

log = logging.getLogger(__name__)


def drain_once(
    events_q: "queue.Queue",
    handler: Callable[[object], None],
) -> bool:
    """Drain every currently-pending event into `handler`.

    Returns True iff a `DoneEvent` was observed during this drain. Callers
    that re-arm polling on `is_running()` would race with the worker thread
    pushing the final DoneEvent and then exiting — so the caller should keep
    polling until this function returns True instead.
    """
    saw_done = False
    try:
        while True:
            event = events_q.get_nowait()
            handler(event)
            if isinstance(event, DoneEvent):
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


Event = ProgressEvent | LogEvent | DoneEvent


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
            summary = self.reconstructor.run(progress_cb=self._on_progress)
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


# Re-exported for clarity in callers that need to type-check event handlers.
__all__: list[str] = ["Worker", "ProgressEvent", "LogEvent", "DoneEvent", "Event", "drain_once"]
_ = Any
