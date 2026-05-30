"""Format-agnostic value objects produced by parsers and consumed by the pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Post:
    """A single BeReal post, normalized across export-format versions."""

    taken_at: datetime
    back_path: str
    front_path: str
    caption: str | None = None
    location: tuple[float, float] | None = None
    retake_counter: int = 0
