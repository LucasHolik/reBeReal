"""Smoke tests for the classic composite layout."""

from __future__ import annotations

from PIL import Image

from rebereal.layouts.classic import ClassicLayout


def _solid(size: tuple[int, int], color: tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", size, color)


def test_classic_output_size_matches_back() -> None:
    layout = ClassicLayout()
    back = _solid((1500, 2000), (10, 20, 30))
    front = _solid((1500, 2000), (200, 200, 200))
    composed = layout.compose(back, front)
    assert len(composed) == 1
    out = composed[0].image
    assert composed[0].suffix == ""
    assert out.size == back.size
    assert out.mode == "RGB"


def test_classic_inset_visible_in_top_left() -> None:
    """The front-camera inset should change a top-left pixel away from the back color."""
    layout = ClassicLayout()
    back = _solid((1500, 2000), (10, 20, 30))
    front = _solid((1500, 2000), (240, 240, 240))
    out = layout.compose(back, front)[0].image
    # A pixel well inside the inset region should be brighter than the back color.
    px = out.getpixel((250, 200))
    assert px != (10, 20, 30)
    assert sum(px) > sum((10, 20, 30))


def test_classic_bottom_right_untouched() -> None:
    layout = ClassicLayout()
    back = _solid((1500, 2000), (10, 20, 30))
    front = _solid((1500, 2000), (240, 240, 240))
    out = layout.compose(back, front)[0].image
    assert out.getpixel((1400, 1900)) == (10, 20, 30)
