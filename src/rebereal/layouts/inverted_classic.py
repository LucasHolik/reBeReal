"""Inverted-classic composite — front fills the frame, back is a rounded inset top-left.

Structurally identical to the classic layout with the two frames swapped: the
selfie becomes the background and the back camera becomes the small inset.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from rebereal.layouts._inset import compose_inset
from rebereal.layouts.base import ComposedImage


@dataclass(frozen=True)
class InvertedClassicLayout:
    """Front at native resolution, back inset top-left. Mirrors ClassicLayout's tunables."""

    name: str = "inverted_classic"
    label: str = "Inverted classic"
    inset_width_pct: float = 0.28      # inset width as fraction of canvas width
    inset_margin_pct: float = 0.04     # margin from top/left edges
    inset_corner_pct: float = 0.06     # corner radius as fraction of inset width
    border_width_pct: float = 0.006    # border width as fraction of canvas width
    supersample: int = 4               # antialiasing factor for the mask + border

    def compose(self, back: Image.Image, front: Image.Image) -> list[ComposedImage]:
        canvas = compose_inset(
            front,
            back,
            inset_width_pct=self.inset_width_pct,
            inset_margin_pct=self.inset_margin_pct,
            inset_corner_pct=self.inset_corner_pct,
            border_width_pct=self.border_width_pct,
            supersample=self.supersample,
        )
        return [ComposedImage(image=canvas, suffix="")]
