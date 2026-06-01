"""Preview pane — renders the first N composites as a thumbnail strip."""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from rebereal.pipeline import Reconstructor

log = logging.getLogger(__name__)

THUMB_SIZE = (200, 267)


class PreviewPane(QWidget):
    """A horizontal strip of composite thumbnails."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(12)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._show_placeholder("No preview yet. Click Preview to render samples.")

    def render(self, reconstructor: "Reconstructor", n: int = 3) -> None:
        self._clear()

        items = reconstructor.preview(n=n)
        if not items:
            self._show_placeholder("No previewable posts found.")
            return

        for item in items:
            for composed in item.images:
                pixmap = _pil_to_pixmap(_thumbnail(composed.image, THUMB_SIZE))
                self._layout.addWidget(_thumb_cell(pixmap, item.post.taken_at.strftime("%Y-%m-%d %H:%M")))
        self._layout.addStretch(1)

    # --- internals --------------------------------------------------------

    def _clear(self) -> None:
        while self._layout.count():
            child = self._layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()

    def _show_placeholder(self, text: str) -> None:
        self._clear()
        placeholder = QLabel(text)
        placeholder.setObjectName("Placeholder")
        self._layout.addWidget(placeholder)
        self._layout.addStretch(1)


def _thumb_cell(pixmap: QPixmap, caption: str) -> QWidget:
    cell = QWidget()
    box = QVBoxLayout(cell)
    box.setContentsMargins(0, 0, 0, 0)
    box.setSpacing(6)

    image = QLabel()
    image.setObjectName("Thumb")
    image.setPixmap(pixmap)
    box.addWidget(image)

    label = QLabel(caption)
    label.setObjectName("ThumbCaption")
    box.addWidget(label)
    return cell


def _thumbnail(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    copy = image.copy()
    copy.thumbnail(size, Image.LANCZOS)
    return copy


def _pil_to_pixmap(image: Image.Image) -> QPixmap:
    """Convert a PIL image to a QPixmap via an in-memory PNG buffer.

    Going through PNG bytes keeps this independent of the Qt binding's
    ImageQt helper (which is fiddly across PySide/PyQt versions).
    """
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    pixmap = QPixmap()
    pixmap.loadFromData(buffer.getvalue(), "PNG")
    return pixmap
