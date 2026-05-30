"""EXIF writer — stamps DateTimeOriginal and GPS via piexif.

Caption is intentionally not written here: Apple Photos and Google Photos
don't surface EXIF `ImageDescription`. The caption is delivered via
`XmpWriter` and `IptcWriter` instead.
"""

from __future__ import annotations

import logging
from datetime import datetime
from io import BytesIO

import piexif

from rebereal.config import Config
from rebereal.models import Post

log = logging.getLogger(__name__)


class ExifWriter:
    """Inject EXIF tags into a JPEG byte stream."""

    def inject(self, image_bytes: bytes, post: Post, config: Config) -> bytes:
        exif = self._build_exif(post, config)
        try:
            exif_bytes = piexif.dump(exif)
        except Exception:
            log.exception("piexif.dump failed; writing image without EXIF")
            return image_bytes

        out = BytesIO()
        try:
            piexif.insert(exif_bytes, image_bytes, out)
        except Exception:
            log.exception("piexif.insert failed; writing image without EXIF")
            return image_bytes
        return out.getvalue()

    def _build_exif(self, post: Post, config: Config) -> dict:
        dt_str = post.taken_at.strftime("%Y:%m:%d %H:%M:%S")
        subsec = f"{post.taken_at.microsecond // 1000:03d}"

        zeroth: dict = {
            piexif.ImageIFD.DateTime: dt_str,
        }
        exif_ifd: dict = {
            piexif.ExifIFD.DateTimeOriginal: dt_str,
            piexif.ExifIFD.DateTimeDigitized: dt_str,
            piexif.ExifIFD.SubSecTimeOriginal: subsec,
            piexif.ExifIFD.SubSecTimeDigitized: subsec,
        }

        gps_ifd: dict = {}
        if config.embed_gps and post.location is not None:
            gps_ifd = _gps_ifd(post.location[0], post.location[1])

        return {"0th": zeroth, "Exif": exif_ifd, "GPS": gps_ifd, "1st": {}, "thumbnail": None}


def _gps_ifd(lat: float, lon: float) -> dict:
    return {
        piexif.GPSIFD.GPSVersionID: (2, 2, 0, 0),
        piexif.GPSIFD.GPSLatitudeRef: b"N" if lat >= 0 else b"S",
        piexif.GPSIFD.GPSLatitude: _deg_to_dms_rational(abs(lat)),
        piexif.GPSIFD.GPSLongitudeRef: b"E" if lon >= 0 else b"W",
        piexif.GPSIFD.GPSLongitude: _deg_to_dms_rational(abs(lon)),
    }


def _deg_to_dms_rational(deg: float) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    """Convert decimal degrees to EXIF (deg, min, sec) rationals.

    Cascades rollover so a value like 12.9999999999 emits (13, 0, 0) rather
    than the invalid (12, 60, 0) / (12, 59, 60).
    """
    d = int(deg)
    m_float = (deg - d) * 60.0
    m = int(m_float)
    s = (m_float - m) * 60.0
    s_milli = int(round(s * 1000))
    if s_milli >= 60_000:
        s_milli -= 60_000
        m += 1
    if m >= 60:
        m -= 60
        d += 1
    return ((d, 1), (m, 1), (s_milli, 1000))


# Keep `datetime` referenced for static analyzers — used implicitly via Post.taken_at.
_ = datetime
