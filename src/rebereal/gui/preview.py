"""Preview pane — renders the first N composites as a thumbnail strip."""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

from PIL import Image
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeyEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from rebereal.media import scale_image

if TYPE_CHECKING:
    from rebereal.pipeline import Reconstructor

log = logging.getLogger(__name__)

THUMB_SIZE = (200, 267)

# Fraction of the screen's available area the enlarged view may occupy.
_LIGHTBOX_SCREEN_FRACTION = 0.9

# Opacity the strip drops to while a re-render is pending, so a stale preview
# reads as "about to change" rather than "unchanged".
_PENDING_OPACITY = 0.3


class ClickableLabel(QLabel):
    """A QLabel that emits ``clicked`` and shows a pointer cursor."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt override)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class PreviewPane(QWidget):
    """A horizontal strip of composite thumbnails; click one to enlarge it."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(12)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        # Held so the modeless lightbox isn't garbage-collected while open.
        self._lightbox: _Lightbox | None = None
        # Dims the whole strip while a re-render is pending (see set_pending).
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity)
        self._show_placeholder("Rendering preview…")

    def set_pending(self) -> None:
        """Dim the current thumbnails to flag that they're being recomputed.

        Called the moment a setting changes — well before the debounced render
        fires — so a quick glance never mistakes a stale preview for the new one.
        """
        self._opacity.setOpacity(_PENDING_OPACITY)

    def render(
        self,
        reconstructor: "Reconstructor",
        n: int = 3,
        scale: float = 1.0,
        jpeg_quality: int = 80,
    ) -> None:
        """Render the first `n` composites, reflecting `scale` and `jpeg_quality`.

        Applying the resolution/quality knobs here (not just at Run) keeps the
        preview a faithful "what you'll get" sample, so the sidebar controls
        visibly affect it.
        """
        self._clear()
        self._opacity.setOpacity(1.0)

        items = reconstructor.preview(n=n)
        if not items:
            self._show_placeholder("No previewable posts found.")
            return

        for item in items:
            caption = item.post.taken_at.strftime("%Y-%m-%d %H:%M")
            for composed in item.images:
                sample = _apply_output_quality(composed.image, scale, jpeg_quality)
                full = _pil_to_pixmap(sample)
                thumb = _pil_to_pixmap(_thumbnail(sample, THUMB_SIZE))
                self._layout.addWidget(self._thumb_cell(thumb, full, caption))
        self._layout.addStretch(1)

    # --- internals --------------------------------------------------------

    def _thumb_cell(self, thumb: QPixmap, full: QPixmap, caption: str) -> QWidget:
        cell = QWidget()
        box = QVBoxLayout(cell)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(6)

        image = ClickableLabel()
        image.setObjectName("Thumb")
        image.setPixmap(thumb)
        image.setToolTip("Click to enlarge")
        image.clicked.connect(lambda: self._open_lightbox(full, caption))
        box.addWidget(image)

        label = QLabel(caption)
        label.setObjectName("ThumbCaption")
        box.addWidget(label)
        return cell

    def _open_lightbox(self, pixmap: QPixmap, caption: str) -> None:
        self._lightbox = _Lightbox(pixmap, caption, self)
        self._lightbox.show()

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


def _apply_output_quality(image: Image.Image, scale: float, jpeg_quality: int) -> Image.Image:
    """Mirror the Run pipeline's resolution + JPEG steps for a faithful preview."""
    sample = scale_image(image, scale).convert("RGB")
    buffer = io.BytesIO()
    sample.save(buffer, format="JPEG", quality=jpeg_quality, optimize=True)
    buffer.seek(0)
    return Image.open(buffer)


class _Lightbox(QDialog):
    """Modeless dialog showing one composite enlarged to fit the screen."""

    def __init__(self, pixmap: QPixmap, caption: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Lightbox")
        self.setWindowTitle(caption)
        # Free the C++ object on close so repeated opens don't pile up hidden
        # dialogs. PreviewPane only ever holds the *current* one (see below).
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)

        image = ClickableLabel()
        image.setObjectName("LightboxImage")
        image.setPixmap(_fit_to_screen(pixmap))
        image.setToolTip("Click to close")
        image.clicked.connect(self.accept)
        box.addWidget(image)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (Qt override)
        if event.key() == Qt.Key.Key_Escape:
            self.accept()
            return
        super().keyPressEvent(event)


def _fit_to_screen(pixmap: QPixmap) -> QPixmap:
    """Scale `pixmap` down to fit the screen, keeping aspect ratio."""
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return pixmap
    available = screen.availableGeometry()
    max_w = int(available.width() * _LIGHTBOX_SCREEN_FRACTION)
    max_h = int(available.height() * _LIGHTBOX_SCREEN_FRACTION)
    if pixmap.width() <= max_w and pixmap.height() <= max_h:
        return pixmap
    return pixmap.scaled(
        max_w,
        max_h,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


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
