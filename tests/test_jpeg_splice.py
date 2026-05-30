"""Byte-level tests for the JPEG APP-segment splicer."""

from __future__ import annotations

from rebereal.metadata._jpeg import insert_app_segment


def _app0_jfif() -> bytes:
    # Minimal JFIF APP0: FF E0, len=16, "JFIF\0", 1.01, units=0, x/y density=1,
    # thumbX=0, thumbY=0.
    body = b"JFIF\x00" + bytes([1, 1, 0, 0, 1, 0, 1, 0, 0])
    return b"\xff\xe0" + (16).to_bytes(2, "big") + body


def _sos_and_eoi() -> bytes:
    # FF DA + tiny scan body + FF D9.
    return b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00" + b"\xff\xd9"


def test_insert_after_app0() -> None:
    jpeg = b"\xff\xd8" + _app0_jfif() + _sos_and_eoi()
    out = insert_app_segment(jpeg, 0xE1, b"hello")
    # New APP1 should follow APP0 and precede SOS.
    app0_end = 2 + len(_app0_jfif())
    assert out[app0_end:app0_end + 2] == b"\xff\xe1"
    seg_len = int.from_bytes(out[app0_end + 2:app0_end + 4], "big")
    assert seg_len == 2 + len(b"hello")
    assert out[app0_end + 4:app0_end + 4 + 5] == b"hello"


def test_insert_skips_fill_byte() -> None:
    # Insert an extra 0xFF fill byte between SOI and APP0 — the splicer must
    # still find the end-of-APP-run correctly and not insert mid-marker.
    jpeg = b"\xff\xd8\xff" + _app0_jfif() + _sos_and_eoi()
    out = insert_app_segment(jpeg, 0xE1, b"x")
    # The new APP1 segment must appear after the APP0 segment.
    app1_pos = out.find(b"\xff\xe1")
    app0_pos = out.find(b"\xff\xe0")
    sos_pos = out.find(b"\xff\xda")
    assert app0_pos < app1_pos < sos_pos


def test_rejects_non_jpeg() -> None:
    try:
        insert_app_segment(b"not a jpeg", 0xE1, b"")
    except ValueError:
        return
    raise AssertionError("expected ValueError")
