"""Smoke tests for the side-by-side composite layout."""

from __future__ import annotations

from PIL import Image

from rebereal.layouts.side_by_side import SideBySideLayout


def _solid(size: tuple[int, int], color: tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", size, color)


def test_side_by_side_equal_size_inputs() -> None:
    layout = SideBySideLayout()
    back = _solid((1500, 2000), (10, 20, 30))
    front = _solid((1500, 2000), (200, 200, 200))
    composed = layout.compose(back, front)
    assert len(composed) == 1
    out = composed[0].image
    assert composed[0].suffix == ""
    assert out.mode == "RGB"
    # Horizontal stitch, no gutter: widths add up, height is the common height.
    assert out.size == (3000, 2000)


def test_side_by_side_normalizes_height() -> None:
    """A front frame of a different height is scaled to the back's height."""
    layout = SideBySideLayout()
    back = _solid((1500, 2000), (10, 20, 30))
    front = _solid((1000, 1000), (200, 200, 200))  # square, half-height of back
    out = layout.compose(back, front)[0].image
    # Front scaled to height 2000 -> width 2000; total width 1500 + 2000.
    assert out.size == (3500, 2000)


def test_side_by_side_places_back_left_front_right() -> None:
    layout = SideBySideLayout()
    back = _solid((1500, 2000), (10, 20, 30))
    front = _solid((1500, 2000), (240, 240, 240))
    out = layout.compose(back, front)[0].image
    assert out.getpixel((100, 1000)) == (10, 20, 30)       # left half = back
    assert out.getpixel((2900, 1000)) == (240, 240, 240)   # right half = front
