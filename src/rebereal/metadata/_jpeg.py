"""Small helpers for splicing application segments into a JPEG byte stream.

JPEG files start with SOI (`FF D8`) and a sequence of segments. Each segment
begins with a marker (`FF xx`); APPn markers run from `FF E0` to `FF EF` and
each carries a 2-byte big-endian length (length includes the two length bytes
but not the marker). Metadata writers add their data as a new APPn segment,
inserted after the existing APPn run so downstream readers find the standard
metadata blocks in the conventional location.
"""

from __future__ import annotations

SOI = b"\xff\xd8"
APP_RANGE = range(0xE0, 0xF0)  # FF E0 .. FF EF


def insert_app_segment(jpeg_bytes: bytes, marker_byte: int, payload: bytes) -> bytes:
    """Insert a new APPn segment carrying `payload` after the existing APPn run.

    `marker_byte` is the low byte of the marker (e.g. 0xE1 for APP1, 0xED for
    APP13). `payload` is the segment body *excluding* the 2-byte length and
    *excluding* the marker — typically the namespace header followed by the
    actual metadata bytes.
    """
    if not jpeg_bytes.startswith(SOI):
        raise ValueError("not a JPEG (no SOI marker)")
    if marker_byte not in APP_RANGE:
        raise ValueError(f"marker 0xFF{marker_byte:02X} is not in APPn range")

    insertion = _end_of_app_run(jpeg_bytes)
    length = len(payload) + 2  # +2 for the length field itself
    if length > 0xFFFF:
        raise ValueError(f"segment too large: {length} bytes (max 65535)")

    segment = bytes((0xFF, marker_byte, length >> 8, length & 0xFF)) + payload
    return jpeg_bytes[:insertion] + segment + jpeg_bytes[insertion:]


def _end_of_app_run(jpeg_bytes: bytes) -> int:
    """Return the byte offset immediately after the last APPn segment.

    Tolerates 0xFF fill bytes between segments (legal per JPEG spec — the
    real marker byte is the last 0xFF in a run).
    """
    n = len(jpeg_bytes)
    i = 2  # skip SOI
    while i + 4 <= n:
        if jpeg_bytes[i] != 0xFF:
            break
        # Skip fill-byte run; the marker is the byte after the last 0xFF.
        j = i
        while j < n and jpeg_bytes[j] == 0xFF:
            j += 1
        if j >= n:
            break
        marker = jpeg_bytes[j]
        if marker not in APP_RANGE:
            break
        if j + 3 > n:
            break
        seg_len = (jpeg_bytes[j + 1] << 8) | jpeg_bytes[j + 2]
        i = j + 1 + seg_len
    return i
