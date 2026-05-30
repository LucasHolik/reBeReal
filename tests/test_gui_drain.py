"""Headless regression test for the GUI event-drain race.

The original `_drain_events` re-armed polling based on `worker.is_running()`.
The worker thread pushes `DoneEvent` and then exits — if `_drain_events`
ran with an empty queue, then the worker pushed DoneEvent and terminated
*before* the `is_running()` check, the final event stayed in the queue
forever and the UI hung. The fix re-arms on whether a DoneEvent has been
observed instead. This test drives the drain helper directly to assert
that property without spinning up a Tk root.
"""

from __future__ import annotations

import queue

from rebereal.gui.app import drain_once
from rebereal.gui.worker import DoneEvent, ProgressEvent


def test_drain_handles_currently_pending_events() -> None:
    q: queue.Queue = queue.Queue()
    q.put(ProgressEvent(done=1, total=2))
    q.put(ProgressEvent(done=2, total=2))

    seen: list[object] = []
    saw_done = drain_once(q, seen.append)

    assert saw_done is False
    assert len(seen) == 2


def test_drain_reports_done_when_present() -> None:
    q: queue.Queue = queue.Queue()
    q.put(DoneEvent(summary=None))

    seen: list[object] = []
    saw_done = drain_once(q, seen.append)

    assert saw_done is True
    assert isinstance(seen[0], DoneEvent)


def test_done_pushed_after_empty_drain_is_seen_on_next_call() -> None:
    """Simulates the race: drain finds an empty queue, then the worker
    thread pushes DoneEvent and exits. The caller must poll again and
    observe the event on the next tick."""
    q: queue.Queue = queue.Queue()

    seen: list[object] = []
    saw_done_first = drain_once(q, seen.append)
    assert saw_done_first is False

    # Race window: worker pushed DoneEvent after our drain saw empty.
    q.put(DoneEvent(summary=None))

    saw_done_second = drain_once(q, seen.append)
    assert saw_done_second is True
    assert len(seen) == 1
