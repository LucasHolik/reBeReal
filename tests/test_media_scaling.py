"""`scale_image` downscales proportionally and no-ops at full resolution."""

from __future__ import annotations

import pytest
from PIL import Image

from rebereal.media import scale_image


def test_half_scale_halves_both_dims() -> None:
    img = Image.new("RGB", (1500, 2000))
    out = scale_image(img, 0.5)
    assert out.size == (750, 1000)


def test_full_scale_returns_same_image() -> None:
    img = Image.new("RGB", (1500, 2000))
    out = scale_image(img, 1.0)
    assert out is img


def test_aspect_ratio_preserved() -> None:
    img = Image.new("RGB", (1600, 900))
    out = scale_image(img, 0.25)
    assert out.size == (400, 225)


def test_tiny_scale_floors_at_one_pixel() -> None:
    img = Image.new("RGB", (10, 10))
    out = scale_image(img, 0.01)
    assert out.size == (1, 1)


def test_non_positive_factor_raises() -> None:
    img = Image.new("RGB", (10, 10))
    with pytest.raises(ValueError):
        scale_image(img, 0.0)
