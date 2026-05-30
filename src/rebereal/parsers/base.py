"""Parser protocol — every export-format reader implements this."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, Protocol

from rebereal.models import Post


class PostParser(Protocol):
    """Reads an export-format file and yields normalized Post objects."""

    def parse(self, path: Path) -> Iterator[Post]: ...
