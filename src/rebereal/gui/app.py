"""Qt root window — folder pickers, preview, run, progress, log."""

from __future__ import annotations

import logging
import shutil
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from rebereal.config import Config
from rebereal.gui.landing import LandingPage
from rebereal.gui.preview import PreviewPane
from rebereal.gui.theme import PALETTE, build_stylesheet
from rebereal.gui.worker import (
    DoneEvent,
    IngestDoneEvent,
    IngestWorker,
    LogEvent,
    ProgressEvent,
    Worker,
    drain_once,
)
from rebereal.ingest import ExportNotFound
from rebereal.layouts import LAYOUTS
from rebereal.logging_setup import configure
from rebereal.pipeline import RunSummary, build

log = logging.getLogger(__name__)

POLL_INTERVAL_MS = 100

# Resolution slider works in integer percent (1–100) and maps to 0.01–1.0.
_RES_MIN = 1
_RES_MAX = 100


def _section_label(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setObjectName("SectionLabel")
    return label


def _field_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("FieldLabel")
    return label


def _hint_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("HintLabel")
    label.setWordWrap(True)
    return label


def _rule() -> QFrame:
    rule = QFrame()
    rule.setObjectName("Rule")
    rule.setFrameShape(QFrame.Shape.HLine)
    return rule


def _ingest_error_message(error: BaseException) -> str:
    if isinstance(error, ExportNotFound):
        return (
            "No posts.json was found in that folder or .zip. "
            "Make sure you selected your BeReal data export."
        )
    return str(error)


class AppWindow(QMainWindow):
    """Main reBeReal window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("reBeReal")
        self.resize(1040, 720)
        self.setMinimumSize(880, 660)

        # Resolved real directory containing posts.json; set by ingest, consumed
        # by preview + Run. None until a source is loaded.
        self._export_root: Path | None = None
        # Scratch dir for an extracted zip; cleaned on re-pick and on close.
        self._tmp: tempfile.TemporaryDirectory | None = None

        self._worker: Worker | None = None
        self._done_seen = False
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._drain_events)

        self._ingest: IngestWorker | None = None
        self._ingest_done_seen = False
        self._ingest_timer = QTimer(self)
        self._ingest_timer.setInterval(POLL_INTERVAL_MS)
        self._ingest_timer.timeout.connect(self._drain_ingest)

        # Debounce settings-driven preview refreshes so dragging a slider or
        # flipping the layout doesn't fire a render on every intermediate value.
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(1000)
        self._preview_timer.timeout.connect(self._render_preview)

        self._build_ui()

    # --- ui ---------------------------------------------------------------

    def _build_ui(self) -> None:
        # Two phases: the landing/drop screen (index 0) and the working UI
        # (index 1). A source is loaded on the landing page; on success the
        # stack swaps to the working UI. Restart swaps back.
        self._stack = QStackedWidget()

        self.landing = LandingPage()
        self.landing.sourceDropped.connect(self._start_ingest)
        self.landing.folderRequested.connect(self._pick_folder)
        self.landing.zipRequested.connect(self._pick_zip)
        self._stack.addWidget(self.landing)

        self._stack.addWidget(self._build_main_page())
        self.setCentralWidget(self._stack)

    def _build_main_page(self) -> QWidget:
        page = QWidget()
        root = QHBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content(), 1)
        return page

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(360)

        col = QVBoxLayout(sidebar)
        col.setContentsMargins(24, 18, 24, 20)
        col.setSpacing(12)

        # Compact title — just the wordmark, so the fields below get the room.
        wordmark = QLabel("rebereal")
        wordmark.setObjectName("Wordmark")
        col.addWidget(wordmark)
        col.addWidget(_rule())

        # All editable settings live in one panel so a run can disable + dim them
        # wholesale (see _set_busy) while the Cancel button below stays live.
        self._settings_panel = self._build_settings_panel()
        self._settings_opacity = QGraphicsOpacityEffect(self._settings_panel)
        self._settings_opacity.setOpacity(1.0)
        self._settings_panel.setGraphicsEffect(self._settings_opacity)
        col.addWidget(self._settings_panel)

        col.addStretch(1)
        col.addWidget(_rule())

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.btn_restart = QPushButton("Restart")
        self.btn_restart.setObjectName("GhostButton")
        self.btn_restart.clicked.connect(self._restart)
        # One button toggles between Run (idle) and Cancel (running); see
        # _on_run_button / _set_run_button_mode.
        self.btn_run = QPushButton("Run")
        self.btn_run.setObjectName("PrimaryButton")
        self.btn_run.clicked.connect(self._on_run_button)
        actions.addWidget(self.btn_restart)
        actions.addWidget(self.btn_run, 1)
        col.addLayout(actions)

        return sidebar

    def _build_settings_panel(self) -> QWidget:
        panel = QWidget()
        col = QVBoxLayout(panel)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(12)

        # Source -----------------------------------------------------------
        # Read-only: the loaded export is chosen on the landing page. To pick a
        # different one the user hits Restart (below).
        col.addWidget(_section_label("Source"))
        self.in_source = QLineEdit()
        self.in_source.setPlaceholderText("No export loaded")
        self.in_source.setReadOnly(True)
        source_box = QVBoxLayout()
        source_box.setSpacing(4)
        source_box.addWidget(_field_label("BeReal export"))
        source_box.addWidget(self.in_source)
        col.addLayout(source_box)

        # Output -----------------------------------------------------------
        col.addWidget(_section_label("Output"))
        self.in_output = QLineEdit()
        self.in_output.setPlaceholderText("Output folder")
        col.addLayout(self._folder_row("Folder", self.in_output, self._pick_output))

        # Composition ------------------------------------------------------
        col.addWidget(_section_label("Composition"))
        comp = QVBoxLayout()
        comp.setSpacing(4)
        comp.addWidget(_field_label("Layout"))
        self.cb_layout = QComboBox()
        self.cb_layout.addItems(sorted(LAYOUTS.keys()))
        self.cb_layout.setCurrentText("classic")
        self.cb_layout.currentTextChanged.connect(lambda *_: self._schedule_preview())
        comp.addWidget(self.cb_layout)
        col.addLayout(comp)

        # Metadata ---------------------------------------------------------
        col.addWidget(_section_label("Metadata"))
        self.chk_gps = QCheckBox("Embed GPS")
        self.chk_gps.setChecked(True)
        self.chk_caption = QCheckBox("Embed caption")
        self.chk_caption.setChecked(True)
        meta = QHBoxLayout()
        meta.setSpacing(16)
        meta.addWidget(self.chk_gps)
        meta.addWidget(self.chk_caption)
        meta.addStretch(1)
        col.addLayout(meta)

        # Quality ----------------------------------------------------------
        col.addWidget(_section_label("Quality"))
        col.addLayout(self._build_resolution_row())
        col.addLayout(self._build_quality_row())

        return panel

    def _folder_row(self, label: str, line: QLineEdit, handler) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(4)
        box.addWidget(_field_label(label))
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(line, 1)
        browse = QPushButton("Browse…")
        browse.setObjectName("GhostButton")
        browse.clicked.connect(handler)
        row.addWidget(browse)
        box.addLayout(row)
        return box

    def _build_resolution_row(self) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(4)
        header = QHBoxLayout()
        header.addWidget(_field_label("Resolution"))
        header.addStretch(1)
        self.lbl_resolution = QLabel("1.00")
        self.lbl_resolution.setObjectName("ValueReadout")
        header.addWidget(self.lbl_resolution)
        box.addLayout(header)

        self.sld_resolution = QSlider(Qt.Orientation.Horizontal)
        self.sld_resolution.setMinimum(_RES_MIN)
        self.sld_resolution.setMaximum(_RES_MAX)
        self.sld_resolution.setValue(_RES_MAX)
        self.sld_resolution.valueChanged.connect(
            lambda v: self.lbl_resolution.setText(f"{v / 100:.2f}")
        )
        self.sld_resolution.valueChanged.connect(lambda *_: self._schedule_preview())
        box.addWidget(self.sld_resolution)
        return box

    def _build_quality_row(self) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(4)
        box.addWidget(_field_label("JPEG quality (1–100)"))
        self.spn_quality = QSpinBox()
        self.spn_quality.setRange(1, 100)
        self.spn_quality.setValue(80)
        self.spn_quality.setToolTip(
            "1–100. Past ~85 the quality gain is hard to see, "
            "but the file size keeps climbing."
        )
        self.spn_quality.valueChanged.connect(lambda *_: self._schedule_preview())
        box.addWidget(self.spn_quality)
        box.addWidget(
            _hint_label(
                "Higher isn't always visibly better — past ~85 the quality gain "
                "is hard to see but the file size keeps climbing."
            )
        )
        return box

    def _build_content(self) -> QWidget:
        content = QWidget()
        col = QVBoxLayout(content)
        col.setContentsMargins(24, 24, 24, 24)
        col.setSpacing(16)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Preview ----------------------------------------------------------
        preview_box = QWidget()
        pv = QVBoxLayout(preview_box)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.setSpacing(12)
        pv.addWidget(_section_label("Preview"))
        self.preview_pane = PreviewPane()
        pv.addWidget(self.preview_pane)
        pv.addStretch(1)
        splitter.addWidget(preview_box)

        # Log --------------------------------------------------------------
        log_box = QWidget()
        lv = QVBoxLayout(log_box)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(8)
        lv.addWidget(_section_label("Log"))
        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("LogView")
        self.log_view.setReadOnly(True)
        lv.addWidget(self.log_view, 1)
        splitter.addWidget(log_box)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        col.addWidget(splitter, 1)

        # Progress ---------------------------------------------------------
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        col.addWidget(self.progress)
        self.lbl_status = QLabel("Idle.")
        self.lbl_status.setObjectName("StatusLabel")
        col.addWidget(self.lbl_status)

        return content

    # --- callbacks --------------------------------------------------------

    def _pick_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select BeReal export folder")
        if d:
            self._start_ingest(Path(d))

    def _pick_zip(self) -> None:
        f, _ = QFileDialog.getOpenFileName(
            self, "Select BeReal export .zip", "", "Zip archives (*.zip)"
        )
        if f:
            self._start_ingest(Path(f))

    def _pick_output(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select output folder")
        if d:
            self.in_output.setText(d)

    # --- ingest -----------------------------------------------------------

    def _start_ingest(self, selected: Path) -> None:
        if (self._ingest is not None and self._ingest.is_running()) or (
            self._worker is not None and self._worker.is_running()
        ):
            return
        selected = selected.expanduser()
        self.in_source.setText(str(selected))
        # Fresh scratch dir per ingest so a re-pick never mingles with a prior
        # extraction. Always created; for a folder source it stays empty.
        self._reset_tmp()
        assert self._tmp is not None
        # Ingest runs on the landing page, so progress/status show there.
        self.landing.set_busy(True)
        self.landing.begin_progress("Reading export…")
        self._ingest_done_seen = False
        self._ingest = IngestWorker(selected, Path(self._tmp.name))
        self._ingest.start()
        self._ingest_timer.start()

    def _drain_ingest(self) -> None:
        if self._ingest is None:
            return
        if drain_once(self._ingest.events, self._handle_ingest_event, (IngestDoneEvent,)):
            self._ingest_done_seen = True
        if self._ingest_done_seen:
            self._ingest_timer.stop()

    def _handle_ingest_event(self, event: object) -> None:
        if isinstance(event, ProgressEvent):
            pct = int(event.done / event.total * 100) if event.total else 0
            self.landing.set_progress(pct, f"Extracting {event.done} / {event.total}")
        elif isinstance(event, IngestDoneEvent):
            if event.error is not None:
                self._export_root = None
                self.in_source.clear()
                self.landing.show_error(_ingest_error_message(event.error))
                return
            self._export_root = event.export_root
            self.landing.reset()
            # Swap to the working UI now that an export is loaded.
            self._stack.setCurrentIndex(1)
            self.lbl_status.setText("Export loaded.")
            self._append_log(f"Loaded export: {event.export_root}")
            self._render_preview()

    # --- preview ----------------------------------------------------------

    def _schedule_preview(self) -> None:
        """Debounced refresh — only once a source is loaded.

        Dim the current strip immediately (before the debounce elapses) so a
        setting change visibly registers instead of looking like a no-op.
        """
        if self._export_root is not None:
            self.preview_pane.set_pending()
            self.lbl_status.setText("Updating preview…")
            self._preview_timer.start()

    def _render_preview(self) -> None:
        if self._export_root is None:
            return
        config = self._preview_config()
        try:
            recon = build(config)
            self.preview_pane.render(
                recon,
                n=3,
                scale=config.resolution_scale,
                jpeg_quality=config.jpeg_quality,
            )
            self.lbl_status.setText("Preview updated.")
            self._append_log("Preview rendered.")
        except Exception as e:
            log.exception("preview failed")
            QMessageBox.critical(self, "Preview failed", str(e))

    def _preview_config(self) -> Config:
        # Preview never resolves or writes output, so output_root is unused on
        # this path; reuse export_root as a harmless placeholder.
        assert self._export_root is not None
        return Config(
            export_root=self._export_root,
            output_root=self._export_root,
            layout=self.cb_layout.currentText(),
            embed_gps=self.chk_gps.isChecked(),
            embed_caption=self.chk_caption.isChecked(),
            resolution_scale=round(self.sld_resolution.value() / 100, 2),
            jpeg_quality=self.spn_quality.value(),
        )

    def _make_config(self) -> Config | None:
        if self._export_root is None:
            QMessageBox.critical(
                self, "No export loaded", "Load a BeReal export (folder or .zip) first."
            )
            return None
        output = self.in_output.text().strip()
        if not output:
            QMessageBox.critical(self, "Missing output folder", "Please choose an output folder.")
            return None
        return Config(
            export_root=self._export_root,
            output_root=Path(output).expanduser().resolve(),
            layout=self.cb_layout.currentText(),
            embed_gps=self.chk_gps.isChecked(),
            embed_caption=self.chk_caption.isChecked(),
            resolution_scale=round(self.sld_resolution.value() / 100, 2),
            jpeg_quality=self.spn_quality.value(),
        )

    def _on_run_button(self) -> None:
        """The single action button: Cancel while running, Run otherwise."""
        if self._worker is not None and self._worker.is_running():
            self._on_cancel()
        else:
            self._on_run()

    def _on_run(self) -> None:
        if self._worker is not None and self._worker.is_running():
            return
        config = self._make_config()
        if config is None:
            return
        try:
            recon = build(config)
        except Exception as e:
            QMessageBox.critical(self, "Configuration error", str(e))
            return

        # No settings can change mid-run, so a pending preview render is moot.
        self._preview_timer.stop()
        self._set_busy(True)
        self._done_seen = False
        self.progress.setValue(0)
        self.lbl_status.setText("Starting…")
        self._worker = Worker(recon)
        self._worker.start()
        self._timer.start()

    def _on_cancel(self) -> None:
        if self._worker is None or not self._worker.is_running():
            return
        self._worker.cancel()
        # Block a second click; _set_busy re-enables on the DoneEvent.
        self.btn_run.setEnabled(False)
        self.lbl_status.setText("Cancelling…")

    def _drain_events(self) -> None:
        if self._worker is None:
            return
        if drain_once(self._worker.events, self._handle_event):
            self._done_seen = True
        # Stop polling once a DoneEvent has been seen, not on thread liveness —
        # the worker can push DoneEvent and exit between an empty drain and an
        # is_running() check, which would otherwise strand the final event.
        if self._done_seen:
            self._timer.stop()

    def _handle_event(self, event: object) -> None:
        if isinstance(event, ProgressEvent):
            pct = int(event.done / event.total * 100) if event.total else 0
            self.progress.setValue(pct)
            self.lbl_status.setText(f"Processing {event.done} / {event.total}")
        elif isinstance(event, LogEvent):
            self._append_log(event.message)
        elif isinstance(event, DoneEvent):
            self._set_busy(False)
            if event.error is not None:
                self.lbl_status.setText("Failed.")
                QMessageBox.critical(self, "Run failed", str(event.error))
            elif event.summary is not None and event.summary.cancelled:
                self._handle_cancelled(event.summary)
            else:
                s = event.summary
                assert s is not None
                self.lbl_status.setText(
                    f"Done. written={s.written} "
                    f"skipped={s.skipped} warnings={len(s.warnings)}"
                )
                if s.output_dir is not None:
                    self._append_log(f"Output folder: {s.output_dir}")

    def _handle_cancelled(self, summary: RunSummary) -> None:
        """A cancelled run leaves partial output; let the user keep or delete it."""
        self.lbl_status.setText("Cancelled.")
        self._append_log(f"Run cancelled after writing {summary.written} file(s).")

        out = summary.output_dir
        if out is None or not out.exists():
            # Cancelled before anything hit disk — nothing to clean up.
            return

        box = QMessageBox(self)
        box.setWindowTitle("Run cancelled")
        box.setText(
            f"The run was cancelled after writing {summary.written} file(s) to:\n"
            f"{out}\n\nKeep the files that were already processed?"
        )
        keep_btn = box.addButton("Keep files", QMessageBox.ButtonRole.AcceptRole)
        delete_btn = box.addButton("Delete files", QMessageBox.ButtonRole.DestructiveRole)
        box.setDefaultButton(keep_btn)
        box.exec()

        if box.clickedButton() is delete_btn:
            shutil.rmtree(out, ignore_errors=True)
            self._append_log(f"Deleted partial output: {out}")
            self.lbl_status.setText("Cancelled — partial output deleted.")
        else:
            self._append_log(f"Kept partial output: {out}")
            self.lbl_status.setText("Cancelled — partial output kept.")

    def _set_busy(self, busy: bool) -> None:
        # Lock + visibly grey the settings; the run button stays live so it can
        # act as Cancel.
        self._settings_panel.setEnabled(not busy)
        self._settings_opacity.setOpacity(0.4 if busy else 1.0)
        self.btn_restart.setEnabled(not busy)
        self.btn_run.setEnabled(True)
        self._set_run_button_mode(running=busy)

    def _set_run_button_mode(self, running: bool) -> None:
        """Swap the action button between Run (primary) and Cancel (danger)."""
        self.btn_run.setText("Cancel" if running else "Run")
        self.btn_run.setObjectName("DangerButton" if running else "PrimaryButton")
        # objectName drives the QSS selector, so re-polish to repaint.
        self.btn_run.style().unpolish(self.btn_run)
        self.btn_run.style().polish(self.btn_run)

    def _restart(self) -> None:
        """Return to the landing page and forget the loaded export."""
        if self._worker is not None and self._worker.is_running():
            return
        if self._tmp is not None:
            self._tmp.cleanup()
            self._tmp = None
        self._export_root = None
        self._preview_timer.stop()
        self.in_source.clear()
        self.in_output.clear()
        self.log_view.clear()
        self.progress.setValue(0)
        self.lbl_status.setText("Idle.")
        self.landing.reset()
        self._stack.setCurrentIndex(0)

    def _append_log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def _reset_tmp(self) -> None:
        if self._tmp is not None:
            self._tmp.cleanup()
        self._tmp = tempfile.TemporaryDirectory(prefix="rebereal-")

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt override)
        if self._tmp is not None:
            self._tmp.cleanup()
            self._tmp = None
        super().closeEvent(event)


def main() -> int:
    configure()
    app = QApplication.instance() or QApplication(sys.argv)
    # Use the platform's real UI font (San Francisco on macOS) so the QSS never
    # references a CSS keyword Qt can't resolve.
    app.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
    app.setStyleSheet(build_stylesheet(PALETTE))
    window = AppWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
