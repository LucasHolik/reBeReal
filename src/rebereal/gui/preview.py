"""Preview pane — renders the first N composites as thumbnails."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from PIL import Image, ImageTk

if TYPE_CHECKING:
    from rebereal.pipeline import Reconstructor

log = logging.getLogger(__name__)

THUMB_SIZE = (200, 267)


class PreviewPane(ttk.Frame):
    """A horizontal strip of composite thumbnails."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self._photo_refs: list[ImageTk.PhotoImage] = []
        self._placeholder = ttk.Label(self, text="No preview yet. Click Preview to render samples.")
        self._placeholder.pack(padx=8, pady=8)

    def render(self, reconstructor: "Reconstructor", n: int = 3) -> None:
        for child in self.winfo_children():
            child.destroy()
        self._photo_refs.clear()

        items = reconstructor.preview(n=n)
        if not items:
            ttk.Label(self, text="No previewable posts found.").pack(padx=8, pady=8)
            return

        row = ttk.Frame(self)
        row.pack(fill="x", padx=4, pady=4)
        for item in items:
            for composed in item.images:
                thumb = _thumbnail(composed.image, THUMB_SIZE)
                photo = ImageTk.PhotoImage(thumb)
                self._photo_refs.append(photo)
                cell = ttk.Frame(row)
                cell.pack(side="left", padx=4)
                tk.Label(cell, image=photo, borderwidth=1, relief="solid").pack()
                ttk.Label(cell, text=item.post.taken_at.strftime("%Y-%m-%d %H:%M")).pack()


def _thumbnail(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    copy = image.copy()
    copy.thumbnail(size, Image.LANCZOS)
    return copy
