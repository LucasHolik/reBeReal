"""Proportional image scaling.

A small, layout-agnostic helper used by the pipeline to downscale finished
composites to a fraction of their source resolution. Kept here (rather than
inline in the pipeline) so future layouts and the GUI preview can reuse it.
"""

from __future__ import annotations

from PIL import Image


def scale_image(image: Image.Image, factor: float) -> Image.Image:
    """Return `image` scaled by `factor`, preserving aspect ratio.

    `factor` is a fraction of the source dimensions: ``1.0`` returns the image
    unchanged, ``0.5`` halves each side, ``0.01`` yields 1% of the source. The
    pipeline never upscales, so any ``factor >= 1.0`` is a no-op. Both output
    dimensions are floored at 1px.

    Raises ValueError if `factor <= 0`.
    """
    if factor <= 0:
        raise ValueError(f"scale factor must be > 0, got {factor}")
    if factor >= 1.0:
        return image
    w, h = image.size
    new_size = (max(1, round(w * factor)), max(1, round(h * factor)))
    return image.resize(new_size, Image.LANCZOS)
