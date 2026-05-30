"""IPTC writer — embeds the caption as IPTC-IIM `Caption-Abstract` (2:120).

Apple Photos and Google Photos both read this field as the photo description.
It is delivered inside an APP13 "Photoshop 3.0" segment wrapping an Image
Resource Block (resource id `0x0404`) which in turn carries the IPTC IIM
stream.
"""

from __future__ import annotations

import logging

from rebereal.config import Config
from rebereal.metadata._jpeg import insert_app_segment
from rebereal.models import Post

log = logging.getLogger(__name__)

APP13 = 0xED
PHOTOSHOP_HEADER = b"Photoshop 3.0\x00"
IRB_SIGNATURE = b"8BIM"
IRB_ID_IPTC = 0x0404

TAG_MARKER = 0x1C
ESC_UTF8 = b"\x1b%G"  # ISO 2022 escape sequence declaring UTF-8
CAPTION_MAX_BYTES = 2000  # IPTC IIM spec maximum for 2:120 Caption-Abstract


class IptcWriter:
    """Inject an APP13 segment carrying IPTC `Caption-Abstract`."""

    def inject(self, image_bytes: bytes, post: Post, config: Config) -> bytes:
        if not config.embed_caption or not post.caption:
            return image_bytes

        try:
            iptc = _build_iptc_stream(post.caption)
            irb = _wrap_in_irb(iptc)
            return insert_app_segment(image_bytes, APP13, PHOTOSHOP_HEADER + irb)
        except Exception:
            log.exception("IPTC injection failed; writing image without IPTC")
            return image_bytes


def _build_iptc_stream(caption: str) -> bytes:
    """Return the IPTC IIM byte stream for a single Caption-Abstract entry."""
    caption_bytes = caption.encode("utf-8")
    if len(caption_bytes) > CAPTION_MAX_BYTES:
        log.warning(
            "IPTC caption truncated from %d to %d bytes",
            len(caption_bytes),
            CAPTION_MAX_BYTES,
        )
        caption_bytes = _truncate_utf8(caption_bytes, CAPTION_MAX_BYTES)
    return b"".join(
        [
            _dataset(1, 90, ESC_UTF8),          # CodedCharacterSet -> UTF-8
            _dataset(2, 0, b"\x00\x04"),        # ApplicationRecordVersion = 4
            _dataset(2, 120, caption_bytes),    # Caption-Abstract
        ]
    )


def _truncate_utf8(data: bytes, limit: int) -> bytes:
    """Truncate `data` to at most `limit` bytes without splitting a codepoint."""
    if len(data) <= limit:
        return data
    return data[:limit].decode("utf-8", errors="ignore").encode("utf-8")


def _dataset(record: int, dataset: int, value: bytes) -> bytes:
    length = len(value)
    return bytes((TAG_MARKER, record, dataset, length >> 8, length & 0xFF)) + value


def _wrap_in_irb(iptc_stream: bytes) -> bytes:
    """Wrap the IPTC stream in an `8BIM` Image Resource Block with id 0x0404."""
    name = b"\x00\x00"  # empty Pascal string, padded to even
    data_len = len(iptc_stream)
    block = (
        IRB_SIGNATURE
        + bytes((IRB_ID_IPTC >> 8, IRB_ID_IPTC & 0xFF))
        + name
        + bytes((
            (data_len >> 24) & 0xFF,
            (data_len >> 16) & 0xFF,
            (data_len >> 8) & 0xFF,
            data_len & 0xFF,
        ))
        + iptc_stream
    )
    if data_len % 2:
        block += b"\x00"
    return block
