"""XMP writer — embeds `dc:description` so the caption surfaces in Apple
Photos, Google Photos, Lightroom, and any other Adobe-model consumer.

EXIF `ImageDescription` is ignored by Apple Photos' info panel; XMP
`dc:description` is the channel modern photo apps actually read.
"""

from __future__ import annotations

import logging
from xml.sax.saxutils import escape

from rebereal.config import Config
from rebereal.metadata._jpeg import insert_app_segment
from rebereal.models import Post

log = logging.getLogger(__name__)

XMP_NS_HEADER = b"http://ns.adobe.com/xap/1.0/\x00"
APP1 = 0xE1


class XmpWriter:
    """Inject an XMP APP1 segment carrying the post's caption."""

    def inject(self, image_bytes: bytes, post: Post, config: Config) -> bytes:
        if not config.embed_caption or not post.caption:
            return image_bytes

        packet = _build_xmp_packet(post.caption)
        try:
            return insert_app_segment(image_bytes, APP1, XMP_NS_HEADER + packet)
        except Exception:
            log.exception("XMP injection failed; writing image without XMP")
            return image_bytes


def _build_xmp_packet(caption: str) -> bytes:
    """Return a minimal XMP packet containing `dc:description`."""
    safe = escape(caption)
    xml = (
        '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/">'
        "<dc:description>"
        '<rdf:Alt><rdf:li xml:lang="x-default">'
        f"{safe}"
        "</rdf:li></rdf:Alt>"
        "</dc:description>"
        "</rdf:Description>"
        "</rdf:RDF>"
        "</x:xmpmeta>"
        '<?xpacket end="w"?>'
    )
    return xml.encode("utf-8")
