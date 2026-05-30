"""Composite metadata writer — chains several writers, threading bytes through."""

from __future__ import annotations

from typing import Iterable

from rebereal.config import Config
from rebereal.metadata.base import MetadataWriter
from rebereal.models import Post


class CompositeMetadataWriter:
    """Runs each child writer in order; each operates on the prior output."""

    def __init__(self, writers: Iterable[MetadataWriter]) -> None:
        self.writers = tuple(writers)

    def inject(self, image_bytes: bytes, post: Post, config: Config) -> bytes:
        data = image_bytes
        for writer in self.writers:
            data = writer.inject(data, post, config)
        return data
