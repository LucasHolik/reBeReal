"""IptcWriter — APP13 Photoshop IRB carries Caption-Abstract as UTF-8."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image

from rebereal.config import Config
from rebereal.metadata.iptc_writer import IptcWriter, PHOTOSHOP_HEADER
from rebereal.models import Post


def _jpeg_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (16, 16), (4, 5, 6)).save(buf, format="JPEG")
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


def test_iptc_segment_present_with_caption() -> None:
    caption = "lunchtime 🍔"
    out = IptcWriter().inject(_jpeg_bytes(), _post(caption), _config())
    assert PHOTOSHOP_HEADER in out
    assert b"8BIM" in out
    # 0x0404 = IPTC IIM resource id
    assert b"\x04\x04" in out
    # UTF-8 declaration: 1:90 with ESC % G
    assert b"\x1c\x01\x5a\x00\x03\x1b%G" in out
    # The caption bytes are present verbatim (UTF-8).
    assert caption.encode("utf-8") in out
    # Still a JPEG.
    assert out.startswith(b"\xff\xd8")


def test_iptc_skips_when_no_caption() -> None:
    original = _jpeg_bytes()
    out = IptcWriter().inject(original, _post(None), _config())
    assert out == original


def test_iptc_skips_when_embed_caption_disabled() -> None:
    cfg = Config(export_root=Path("."), output_root=Path("."), embed_caption=False)
    original = _jpeg_bytes()
    out = IptcWriter().inject(original, _post("hi"), cfg)
    assert out == original


def test_caption_truncation_preserves_utf8_boundary() -> None:
    # 600 burger emoji = 2400 UTF-8 bytes, exceeds the 2000-byte 2:120 cap.
    caption = "🍔" * 600
    out = IptcWriter().inject(_jpeg_bytes(), _post(caption), _config())

    # Anchor on the Photoshop header so we don't false-match a stray byte
    # sequence in the JPEG image data.
    ps_idx = out.find(PHOTOSHOP_HEADER)
    assert ps_idx >= 0
    # Locate the 2:120 (Caption-Abstract) dataset: 0x1C 0x02 0x78 len_hi len_lo ...
    marker = b"\x1c\x02\x78"
    idx = out.find(marker, ps_idx)
    assert idx >= 0, "Caption-Abstract dataset not found"
    length = (out[idx + 3] << 8) | out[idx + 4]
    assert length <= 2000
    payload = out[idx + 5 : idx + 5 + length]
    # Must decode cleanly — no half-emoji at the tail.
    decoded = payload.decode("utf-8")
    assert decoded and all(ch == "🍔" for ch in decoded)
