"""`build()` validates `resolution_scale` and `jpeg_quality` ranges."""

from __future__ import annotations

from pathlib import Path

import pytest

from rebereal.config import Config
from rebereal.pipeline import build


@pytest.mark.parametrize("scale", [0.0, -0.5, 1.5])
def test_out_of_range_resolution_raises(tmp_path: Path, scale: float) -> None:
    cfg = Config(export_root=tmp_path, output_root=tmp_path, resolution_scale=scale)
    with pytest.raises(ValueError) as exc:
        build(cfg)
    assert "resolution_scale" in str(exc.value)


@pytest.mark.parametrize("quality", [0, 101])
def test_out_of_range_jpeg_quality_raises(tmp_path: Path, quality: int) -> None:
    cfg = Config(export_root=tmp_path, output_root=tmp_path, jpeg_quality=quality)
    with pytest.raises(ValueError) as exc:
        build(cfg)
    assert "jpeg_quality" in str(exc.value)


def test_defaults_accepted(tmp_path: Path) -> None:
    cfg = Config(export_root=tmp_path, output_root=tmp_path)
    recon = build(cfg)
    assert recon.config.resolution_scale == 1.0
    assert recon.config.jpeg_quality == 80
