"""Smoke tests for the inverted-classic composite layout."""

from __future__ import annotations

from PIL import Image

from rebereal.layouts.inverted_classic import InvertedClassicLayout


def _solid(size: tuple[int, int], color: tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", size, color)


def test_inverted_output_size_matches_front() -> None:
    layout = InvertedClassicLayout()
    back = _solid((1500, 2000), (10, 20, 30))
    front = _solid((1200, 1600), (200, 200, 200))
    composed = layout.compose(back, front)
    assert len(composed) == 1
    out = composed[0].image
    assert composed[0].suffix == ""
    # Front is the canvas in the inverted layout.
    assert out.size == front.size
    assert out.mode == "RGB"


def test_inverted_inset_visible_in_top_left() -> None:
    """The back-camera inset should change a top-left pixel away from the front color."""
    layout = InvertedClassicLayout()
    back = _solid((1500, 2000), (240, 240, 240))
    front = _solid((1500, 2000), (10, 20, 30))
    out = layout.compose(back, front)[0].image
    px = out.getpixel((250, 200))
    assert px != (10, 20, 30)
    assert sum(px) > sum((10, 20, 30))


def test_inverted_bottom_right_untouched() -> None:
    layout = InvertedClassicLayout()
    back = _solid((1500, 2000), (240, 240, 240))
    front = _solid((1500, 2000), (10, 20, 30))
    out = layout.compose(back, front)[0].image
    assert out.getpixel((1400, 1900)) == (10, 20, 30)
