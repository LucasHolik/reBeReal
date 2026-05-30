"""Metadata-writer protocol — operates on serialized image bytes."""

from __future__ import annotations

from typing import Protocol

from rebereal.config import Config
from rebereal.models import Post


class MetadataWriter(Protocol):
    """Injects metadata (EXIF/XMP/IPTC) into already-serialized image bytes."""

    def inject(self, image_bytes: bytes, post: Post, config: Config) -> bytes: ...
