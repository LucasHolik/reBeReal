"""Qt root window — folder pickers, preview, run, progress, log."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
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
    QVBoxLayout,
    QWidget,
)

from rebereal.config import Config
from rebereal.gui.preview import PreviewPane
from rebereal.gui.theme import PALETTE, build_stylesheet
from rebereal.gui.worker import DoneEvent, LogEvent, ProgressEvent, Worker, drain_once
from rebereal.layouts import LAYOUTS
from rebereal.logging_setup import configure
from rebereal.pipeline import build

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


def _rule() -> QFrame:
    rule = QFrame()
    rule.setObjectName("Rule")
    rule.setFrameShape(QFrame.Shape.HLine)
    return rule


class AppWindow(QMainWindow):
    """Main reBeReal window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("reBeReal")
        self.resize(1040, 700)
        self.setMinimumSize(880, 600)

        self._worker: Worker | None = None
        self._done_seen = False
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._drain_events)

        self._build_ui()

    # --- ui ---------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content(), 1)
        self.setCentralWidget(central)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(360)

        col = QVBoxLayout(sidebar)
        col.setContentsMargins(24, 24, 24, 24)
        col.setSpacing(16)

        wordmark = QLabel("rebereal")
        wordmark.setObjectName("Wordmark")
        tagline = QLabel("Rebuild your BeReals as importable photos.")
        tagline.setObjectName("Tagline")
        tagline.setWordWrap(True)
        col.addWidget(wordmark)
        col.addWidget(tagline)
        col.addWidget(_rule())

        # Folders ----------------------------------------------------------
        col.addWidget(_section_label("Folders"))
        self.in_export = QLineEdit()
        self.in_export.setPlaceholderText("BeReal export folder")
        col.addLayout(self._folder_row("Export", self.in_export, self._pick_export))
        self.in_output = QLineEdit()
        self.in_output.setPlaceholderText("Output folder")
        col.addLayout(self._folder_row("Output", self.in_output, self._pick_output))

        # Composition ------------------------------------------------------
        col.addWidget(_section_label("Composition"))
        comp = QVBoxLayout()
        comp.setSpacing(4)
        comp.addWidget(_field_label("Layout"))
        self.cb_layout = QComboBox()
        self.cb_layout.addItems(sorted(LAYOUTS.keys()))
        self.cb_layout.setCurrentText("classic")
        comp.addWidget(self.cb_layout)
        col.addLayout(comp)

        # Metadata ---------------------------------------------------------
        col.addWidget(_section_label("Metadata"))
        self.chk_gps = QCheckBox("Embed GPS")
        self.chk_gps.setChecked(True)
        self.chk_caption = QCheckBox("Embed caption")
        self.chk_caption.setChecked(True)
        col.addWidget(self.chk_gps)
        col.addWidget(self.chk_caption)

        # Quality ----------------------------------------------------------
        col.addWidget(_section_label("Quality"))
        col.addLayout(self._build_resolution_row())
        col.addLayout(self._build_quality_row())

        col.addStretch(1)
        col.addWidget(_rule())

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.btn_preview = QPushButton("Preview")
        self.btn_preview.setObjectName("GhostButton")
        self.btn_preview.clicked.connect(self._on_preview)
        self.btn_run = QPushButton("Run")
        self.btn_run.setObjectName("PrimaryButton")
        self.btn_run.clicked.connect(self._on_run)
        actions.addWidget(self.btn_preview)
        actions.addWidget(self.btn_run, 1)
        col.addLayout(actions)

        return sidebar

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
        box.addWidget(self.sld_resolution)
        return box

    def _build_quality_row(self) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(4)
        box.addWidget(_field_label("JPEG quality"))
        self.spn_quality = QSpinBox()
        self.spn_quality.setRange(1, 100)
        self.spn_quality.setValue(80)
        box.addWidget(self.spn_quality)
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

    def _pick_export(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select BeReal export folder")
        if d:
            self.in_export.setText(d)

    def _pick_output(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select output folder")
        if d:
            self.in_output.setText(d)

    def _make_config(self) -> Config | None:
        export = self.in_export.text().strip()
        output = self.in_output.text().strip()
        if not export or not output:
            QMessageBox.critical(
                self, "Missing folders", "Please choose both an export and an output folder."
            )
            return None
        return Config(
            export_root=Path(export).expanduser().resolve(),
            output_root=Path(output).expanduser().resolve(),
            layout=self.cb_layout.currentText(),
            embed_gps=self.chk_gps.isChecked(),
            embed_caption=self.chk_caption.isChecked(),
            resolution_scale=round(self.sld_resolution.value() / 100, 2),
            jpeg_quality=self.spn_quality.value(),
        )

    def _on_preview(self) -> None:
        config = self._make_config()
        if config is None:
            return
        try:
            recon = build(config)
            self.preview_pane.render(recon, n=3)
            self._append_log("Preview rendered.")
        except Exception as e:
            log.exception("preview failed")
            QMessageBox.critical(self, "Preview failed", str(e))

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

        self._set_busy(True)
        self._done_seen = False
        self.progress.setValue(0)
        self.lbl_status.setText("Starting…")
        self._worker = Worker(recon)
        self._worker.start()
        self._timer.start()

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
            else:
                s = event.summary
                assert s is not None
                self.lbl_status.setText(
                    f"Done. written={s.written} "
                    f"skipped={s.skipped} warnings={len(s.warnings)}"
                )
                if s.output_dir is not None:
                    self._append_log(f"Output folder: {s.output_dir}")

    def _set_busy(self, busy: bool) -> None:
        self.btn_preview.setEnabled(not busy)
        self.btn_run.setEnabled(not busy)

    def _append_log(self, message: str) -> None:
        self.log_view.appendPlainText(message)


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
