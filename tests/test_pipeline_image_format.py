"""`build()` validates `Config.image_format` against the registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from rebereal.config import Config
from rebereal.pipeline import IMAGE_FORMATS, build


def test_unsupported_image_format_raises(tmp_path: Path) -> None:
    cfg = Config(export_root=tmp_path, output_root=tmp_path, image_format="webp")
    with pytest.raises(ValueError) as exc:
        build(cfg)
    assert "webp" in str(exc.value)
    for supported in IMAGE_FORMATS:
        assert supported in str(exc.value)


def test_jpg_alias_accepted(tmp_path: Path) -> None:
    cfg = Config(export_root=tmp_path, output_root=tmp_path, image_format="jpg")
    recon = build(cfg)
    assert recon.config.image_format == "jpg"


def test_jpeg_default_accepted(tmp_path: Path) -> None:
    cfg = Config(export_root=tmp_path, output_root=tmp_path)
    recon = build(cfg)
    assert recon.config.image_format == "jpeg"
