"""Logging configuration for both CLI and GUI runs."""

from __future__ import annotations

import logging
from typing import Callable

_LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_DATE_FORMAT = "%H:%M:%S"


class CallbackHandler(logging.Handler):
    """Forwards every log record to a callable — used by the GUI worker."""

    def __init__(self, callback: Callable[[str], None], level: int = logging.INFO) -> None:
        super().__init__(level)
        self._callback = callback
        self.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._callback(self.format(record))
        except Exception:
            self.handleError(record)


def configure(
    level: int = logging.INFO,
    callback: Callable[[str], None] | None = None,
) -> None:
    """Install a stderr handler, plus an optional callback handler for the GUI.

    Idempotent — calling twice will not duplicate handlers of the same type.
    """
    root = logging.getLogger()
    root.setLevel(level)

    have_stream = False
    for h in root.handlers:
        if isinstance(h, CallbackHandler):
            h.setLevel(level)
        elif isinstance(h, logging.StreamHandler):
            h.setLevel(level)
            have_stream = True

    if not have_stream:
        stream = logging.StreamHandler()
        stream.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
        stream.setLevel(level)
        root.addHandler(stream)

    if callback is not None and not any(isinstance(h, CallbackHandler) for h in root.handlers):
        root.addHandler(CallbackHandler(callback, level=level))
