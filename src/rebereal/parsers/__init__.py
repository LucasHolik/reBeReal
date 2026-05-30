"""Export-format parsers. New formats register a factory in `PARSERS`."""

from __future__ import annotations

from typing import Callable

from rebereal.parsers.base import PostParser
from rebereal.parsers.posts_json import PostsJsonParser

PARSERS: dict[str, Callable[[], PostParser]] = {
    "posts_json": PostsJsonParser,
}

__all__ = ["PARSERS", "PostParser", "PostsJsonParser"]
