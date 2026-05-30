"""XmpWriter — APP1 splice carries dc:description with the caption."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image

from rebereal.config import Config
from rebereal.metadata.xmp_writer import XMP_NS_HEADER, XmpWriter
from rebereal.models import Post


def _jpeg_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (16, 16), (1, 2, 3)).save(buf, format="JPEG")
    return buf.getvalue()


def _config() -> Config:
    return Config(export_root=Path("."), output_root=Path("."))


def _post(caption: str | None) -> Post:
    return Post(
        taken_at=datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        back_path="x",
        front_path="y",
        caption=caption,
        location=None,
    )


def test_xmp_segment_present_with_caption() -> None:
    out = XmpWriter().inject(_jpeg_bytes(), _post("hello world"), _config())
    assert XMP_NS_HEADER in out
    assert b"<dc:description>" in out
    assert b"hello world" in out
    # Output is still a valid-looking JPEG byte stream.
    assert out.startswith(b"\xff\xd8")


def test_xmp_skips_when_no_caption() -> None:
    original = _jpeg_bytes()
    out = XmpWriter().inject(original, _post(None), _config())
    assert out == original


def test_xmp_skips_when_embed_caption_disabled() -> None:
    cfg = Config(export_root=Path("."), output_root=Path("."), embed_caption=False)
    original = _jpeg_bytes()
    out = XmpWriter().inject(original, _post("hi"), cfg)
    assert out == original


def test_xmp_escapes_xml_special_chars() -> None:
    out = XmpWriter().inject(_jpeg_bytes(), _post("a < b & c > d"), _config())
    assert b"a &lt; b &amp; c &gt; d" in out
    assert b"a < b & c > d" not in out
