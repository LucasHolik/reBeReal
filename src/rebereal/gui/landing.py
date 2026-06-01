"""Landing page — the full-window drop target shown before a source is loaded.

A large dashed drop zone fills the window, with *Choose folder…* / *Choose .zip…*
buttons in the bottom corners. Dropping a folder or `.zip`, or pressing either
button, asks the window to ingest a source; while a zip extracts, this page shows
the progress inline. Once a source loads the window swaps this page out for the
working UI (see `app.AppWindow`).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class LandingPage(QWidget):
    """Initial drop screen. Emits a path to ingest; shows extraction progress."""

    sourceDropped = Signal(Path)
    folderRequested = Signal()
    zipRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._build_ui()

    # --- ui ---------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(48, 40, 48, 40)
        outer.setSpacing(24)

        wordmark = QLabel("rebereal")
        wordmark.setObjectName("LandingWordmark")
        wordmark.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        outer.addWidget(wordmark)

        # Big dashed drop zone fills the available space.
        self._zone = QFrame()
        self._zone.setObjectName("DropZone")
        zone = QVBoxLayout(self._zone)
        zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone.setSpacing(10)

        hint = QLabel("Drop your BeReal export folder or .zip here")
        hint.setObjectName("DropHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone.addWidget(hint)

        subhint = QLabel("…or use the buttons below.")
        subhint.setObjectName("DropSubhint")
        subhint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone.addWidget(subhint)

        self._status = QLabel("")
        self._status.setObjectName("StatusLabel")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone.addWidget(self._status)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setMaximumWidth(360)
        self._progress.hide()
        zone.addWidget(self._progress, 0, Qt.AlignmentFlag.AlignHCenter)

        outer.addWidget(self._zone, 1)

        # Buttons pinned to the bottom corners.
        row = QHBoxLayout()
        self._btn_folder = QPushButton("Choose folder…")
        self._btn_folder.setObjectName("GhostButton")
        self._btn_folder.clicked.connect(lambda: self.folderRequested.emit())
        self._btn_zip = QPushButton("Choose .zip…")
        self._btn_zip.setObjectName("GhostButton")
        self._btn_zip.clicked.connect(lambda: self.zipRequested.emit())
        row.addWidget(self._btn_folder)
        row.addStretch(1)
        row.addWidget(self._btn_zip)
        outer.addLayout(row)

    # --- public API -------------------------------------------------------

    def set_busy(self, busy: bool) -> None:
        self._btn_folder.setEnabled(not busy)
        self._btn_zip.setEnabled(not busy)

    def begin_progress(self, text: str) -> None:
        self._status.setText(text)
        self._progress.setValue(0)
        self._progress.show()

    def set_progress(self, pct: int, text: str) -> None:
        self._progress.setValue(pct)
        self._status.setText(text)

    def show_error(self, text: str) -> None:
        self._progress.hide()
        self._status.setText(text)
        self.set_busy(False)

    def reset(self) -> None:
        self._status.setText("")
        self._progress.hide()
        self._progress.setValue(0)
        self.set_busy(False)

    # --- drag and drop ----------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802 (Qt override)
        if _dropped_source(event) is not None:
            event.acceptProposedAction()
            self._set_drag_active(True)
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:  # noqa: N802 (Qt override)
        if _dropped_source(event) is not None:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: object) -> None:  # noqa: N802 (Qt override)
        self._set_drag_active(False)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802 (Qt override)
        self._set_drag_active(False)
        source = _dropped_source(event)
        if source is None:
            event.ignore()
            return
        event.acceptProposedAction()
        self.sourceDropped.emit(source)

    # --- internals --------------------------------------------------------

    def _set_drag_active(self, active: bool) -> None:
        """Toggle the dashed-border highlight by re-polishing the zone's QSS."""
        self._zone.setProperty("dragActive", active)
        self._zone.style().unpolish(self._zone)
        self._zone.style().polish(self._zone)


def _dropped_source(event: QDragEnterEvent | QDragMoveEvent | QDropEvent) -> Path | None:
    """Return the single dropped folder or `.zip` path, or None if not droppable."""
    mime = event.mimeData()
    if not mime.hasUrls():
        return None
    urls = mime.urls()
    if len(urls) != 1:
        return None
    path = Path(urls[0].toLocalFile())
    if path.is_dir() or (path.is_file() and path.suffix.lower() == ".zip"):
        return path
    return None
