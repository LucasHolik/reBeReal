"""Naming-strategy protocol — maps a Post + suffix to an output Path."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from rebereal.config import Config
from rebereal.models import Post


class NamingStrategy(Protocol):
    """Compute the on-disk output path for a single composed image."""

    name: str

    def output_path(self, post: Post, suffix: str, config: Config) -> Path: ...
