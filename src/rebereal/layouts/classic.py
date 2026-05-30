"""Classic BeReal composite — back fills the frame, front is a rounded inset top-left."""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw

from rebereal.layouts.base import ComposedImage


@dataclass(frozen=True)
class ClassicLayout:
    """Recreate the in-app look: back at native resolution, front inset top-left.

    Tunables are dataclass fields so callers can construct variants without
    subclassing. The defaults match the visual proportions of the BeReal app.
    """

    name: str = "classic"
    inset_width_pct: float = 0.28      # front-cam width as fraction of canvas width
    inset_margin_pct: float = 0.04     # margin from top/left edges
    inset_corner_pct: float = 0.06     # corner radius as fraction of inset width
    border_width_pct: float = 0.006    # white border width as fraction of canvas width
    supersample: int = 4               # antialiasing factor for the mask + border

    def compose(self, back: Image.Image, front: Image.Image) -> list[ComposedImage]:
        canvas = back.convert("RGB").copy()
        cw, ch = canvas.size

        inset_w = max(1, int(round(cw * self.inset_width_pct)))
        front_ar = front.height / front.width if front.width else 1.0
        inset_h = max(1, int(round(inset_w * front_ar)))
        margin = max(1, int(round(cw * self.inset_margin_pct)))
        corner = max(1, int(round(inset_w * self.inset_corner_pct)))
        border = max(1, int(round(cw * self.border_width_pct)))

        front_rgb = front.convert("RGB").resize((inset_w, inset_h), Image.LANCZOS)
        rounded = _round_corners(front_rgb, corner, self.supersample)
        bordered = _add_border(rounded, border, corner, self.supersample)

        offset = max(0, margin - border)
        canvas.paste(bordered, (offset, offset), bordered)
        return [ComposedImage(image=canvas, suffix="")]


def _round_corners(img: Image.Image, radius: int, supersample: int) -> Image.Image:
    """Return an RGBA copy of `img` with rounded corners (alpha-masked)."""
    w, h = img.size
    big = (w * supersample, h * supersample)
    mask = Image.new("L", big, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, big[0] - 1, big[1] - 1),
        radius=radius * supersample,
        fill=255,
    )
    mask = mask.resize((w, h), Image.LANCZOS)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def _add_border(img: Image.Image, border: int, inner_radius: int, supersample: int) -> Image.Image:
    """Wrap `img` (RGBA) in a black rounded border concentric with its alpha shape."""
    w, h = img.size
    bw, bh = w + 2 * border, h + 2 * border

    big = (bw * supersample, bh * supersample)
    border_mask = Image.new("L", big, 0)
    # Concentric rounded rects: outer arc center coincides with inner arc center
    # when outer_radius = inner_radius + border (uniform gap around the curve).
    outer_radius = (inner_radius + border) * supersample
    ImageDraw.Draw(border_mask).rounded_rectangle(
        (0, 0, big[0] - 1, big[1] - 1),
        radius=outer_radius,
        fill=255,
    )
    border_mask = border_mask.resize((bw, bh), Image.LANCZOS)

    out = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    out.putalpha(border_mask)
    fill = Image.new("RGBA", (bw, bh), (0, 0, 0, 255))
    fill.putalpha(border_mask)
    out.paste(fill, (0, 0), fill)
    out.paste(img, (border, border), img)
    return out
