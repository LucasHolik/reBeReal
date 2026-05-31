"""Tk root window — folder pickers, preview, run, progress, log."""

from __future__ import annotations

import logging
import queue
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from rebereal.config import Config
from rebereal.gui.preview import PreviewPane
from rebereal.gui.worker import DoneEvent, LogEvent, ProgressEvent, Worker
from rebereal.layouts import LAYOUTS
from rebereal.logging_setup import configure
from rebereal.pipeline import build

log = logging.getLogger(__name__)

POLL_INTERVAL_MS = 100


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


class AppWindow(tk.Tk):
    """Main reBeReal window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("reBeReal")
        self.geometry("900x680")
        self.minsize(720, 560)

        self._worker: Worker | None = None
        self._done_seen: bool = False
        self._build_vars()
        self._build_widgets()

    # --- variables / widgets ---------------------------------------------

    def _build_vars(self) -> None:
        self.var_export = tk.StringVar()
        self.var_output = tk.StringVar()
        self.var_layout = tk.StringVar(value="classic")
        self.var_embed_gps = tk.BooleanVar(value=True)
        self.var_embed_caption = tk.BooleanVar(value=True)
        self.var_resolution = tk.DoubleVar(value=1.0)
        self.var_jpeg_quality = tk.IntVar(value=80)
        self.var_progress = tk.DoubleVar(value=0.0)
        self.var_status = tk.StringVar(value="Idle.")

    def _build_widgets(self) -> None:
        pad = {"padx": 8, "pady": 4}

        form = ttk.Frame(self)
        form.pack(fill="x", **pad)

        ttk.Label(form, text="Export folder:").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_export, width=70).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(form, text="Browse…", command=self._pick_export).grid(row=0, column=2)

        ttk.Label(form, text="Output folder:").grid(row=1, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_output, width=70).grid(row=1, column=1, sticky="ew", padx=4)
        ttk.Button(form, text="Browse…", command=self._pick_output).grid(row=1, column=2)

        ttk.Label(form, text="Layout:").grid(row=2, column=0, sticky="w")
        layout_cb = ttk.Combobox(
            form, textvariable=self.var_layout, values=sorted(LAYOUTS.keys()), state="readonly", width=20
        )
        layout_cb.grid(row=2, column=1, sticky="w", padx=4)

        form.columnconfigure(1, weight=1)

        opts = ttk.Frame(self)
        opts.pack(fill="x", **pad)
        ttk.Checkbutton(opts, text="Embed GPS", variable=self.var_embed_gps).pack(side="left", padx=4)
        ttk.Checkbutton(opts, text="Embed caption", variable=self.var_embed_caption).pack(side="left", padx=4)

        quality = ttk.Frame(self)
        quality.pack(fill="x", **pad)

        ttk.Label(quality, text="Resolution:").pack(side="left", padx=4)
        res_value = ttk.Label(quality, width=5)
        res_scale = ttk.Scale(
            quality,
            from_=0.01,
            to=1.0,
            variable=self.var_resolution,
            orient="horizontal",
            length=180,
            command=lambda _v: res_value.configure(text=f"{self.var_resolution.get():.2f}"),
        )
        res_scale.pack(side="left", padx=4)
        res_value.configure(text=f"{self.var_resolution.get():.2f}")
        res_value.pack(side="left", padx=(0, 12))

        ttk.Label(quality, text="JPEG quality:").pack(side="left", padx=4)
        ttk.Spinbox(
            quality, from_=1, to=100, textvariable=self.var_jpeg_quality, width=5
        ).pack(side="left", padx=4)

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", **pad)
        self.btn_preview = ttk.Button(buttons, text="Preview", command=self._on_preview)
        self.btn_preview.pack(side="left", padx=4)
        self.btn_run = ttk.Button(buttons, text="Run", command=self._on_run)
        self.btn_run.pack(side="left", padx=4)

        self.preview_pane = PreviewPane(self)
        self.preview_pane.pack(fill="x", **pad)

        progress = ttk.Frame(self)
        progress.pack(fill="x", **pad)
        ttk.Progressbar(progress, variable=self.var_progress, maximum=100.0).pack(fill="x")
        ttk.Label(progress, textvariable=self.var_status).pack(anchor="w")

        log_frame = ttk.LabelFrame(self, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(log_frame, height=12, state="disabled", wrap="none")
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scroll.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scroll.set)

    # --- callbacks --------------------------------------------------------

    def _pick_export(self) -> None:
        d = filedialog.askdirectory(title="Select BeReal export folder")
        if d:
            self.var_export.set(d)

    def _pick_output(self) -> None:
        d = filedialog.askdirectory(title="Select output folder")
        if d:
            self.var_output.set(d)

    def _make_config(self) -> Config | None:
        export = self.var_export.get().strip()
        output = self.var_output.get().strip()
        if not export or not output:
            messagebox.showerror("Missing folders", "Please choose both an export and an output folder.")
            return None
        try:
            resolution_scale = round(self.var_resolution.get(), 2)
            jpeg_quality = self.var_jpeg_quality.get()
        except tk.TclError:
            messagebox.showerror("Invalid value", "Resolution and JPEG quality must be numbers.")
            return None
        return Config(
            export_root=Path(export).expanduser().resolve(),
            output_root=Path(output).expanduser().resolve(),
            layout=self.var_layout.get(),
            embed_gps=self.var_embed_gps.get(),
            embed_caption=self.var_embed_caption.get(),
            resolution_scale=resolution_scale,
            jpeg_quality=jpeg_quality,
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
            messagebox.showerror("Preview failed", str(e))

    def _on_run(self) -> None:
        if self._worker is not None and self._worker.is_running():
            return
        config = self._make_config()
        if config is None:
            return
        try:
            recon = build(config)
        except Exception as e:
            messagebox.showerror("Configuration error", str(e))
            return

        self._set_busy(True)
        self._done_seen = False
        self.var_progress.set(0.0)
        self.var_status.set("Starting…")
        self._worker = Worker(recon)
        self._worker.start()
        self.after(POLL_INTERVAL_MS, self._drain_events)

    def _drain_events(self) -> None:
        if self._worker is None:
            return
        if drain_once(self._worker.events, self._handle_event):
            self._done_seen = True
        # Re-arm based on whether we have seen a DoneEvent, not on thread
        # liveness — the worker can push DoneEvent and exit between an empty
        # drain and an is_running() check, which previously stranded the
        # final event in the queue.
        if not self._done_seen:
            self.after(POLL_INTERVAL_MS, self._drain_events)

    def _handle_event(self, event: object) -> None:
        if isinstance(event, ProgressEvent):
            pct = (event.done / event.total * 100.0) if event.total else 0.0
            self.var_progress.set(pct)
            self.var_status.set(f"Processing {event.done} / {event.total}")
        elif isinstance(event, LogEvent):
            self._append_log(event.message)
        elif isinstance(event, DoneEvent):
            self._set_busy(False)
            if event.error is not None:
                self.var_status.set("Failed.")
                messagebox.showerror("Run failed", str(event.error))
            else:
                s = event.summary
                assert s is not None
                self.var_status.set(
                    f"Done. written={s.written} "
                    f"skipped={s.skipped} warnings={len(s.warnings)}"
                )
                if s.output_dir is not None:
                    self._append_log(f"Output folder: {s.output_dir}")

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.btn_preview.configure(state=state)
        self.btn_run.configure(state=state)

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")


def main() -> int:
    configure()
    app = AppWindow()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
