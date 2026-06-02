"""Shared inset compositing — one image fills the frame, the other is a rounded,
bordered inset in the top-left. Reused by the classic and inverted-classic layouts."""

from __future__ import annotations

from PIL import Image, ImageDraw


def compose_inset(
    canvas_src: Image.Image,
    inset_src: Image.Image,
    *,
    inset_width_pct: float,
    inset_margin_pct: float,
    inset_corner_pct: float,
    border_width_pct: float,
    supersample: int,
) -> Image.Image:
    """Paste `inset_src` as a rounded, bordered inset in the top-left of `canvas_src`.

    All sizes are computed as fractions of the **canvas** width, so the inset keeps
    the same on-screen proportions regardless of which frame is the canvas. Returns
    a fresh RGB image the size of `canvas_src`.
    """
    canvas = canvas_src.convert("RGB").copy()
    cw, ch = canvas.size

    inset_w = max(1, int(round(cw * inset_width_pct)))
    inset_ar = inset_src.height / inset_src.width if inset_src.width else 1.0
    inset_h = max(1, int(round(inset_w * inset_ar)))
    margin = max(1, int(round(cw * inset_margin_pct)))
    corner = max(1, int(round(inset_w * inset_corner_pct)))
    border = max(1, int(round(cw * border_width_pct)))

    inset_rgb = inset_src.convert("RGB").resize((inset_w, inset_h), Image.LANCZOS)
    rounded = _round_corners(inset_rgb, corner, supersample)
    bordered = _add_border(rounded, border, corner, supersample)

    offset = max(0, margin - border)
    canvas.paste(bordered, (offset, offset), bordered)
    return canvas


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
