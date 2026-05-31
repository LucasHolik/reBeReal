"""Run configuration — a single immutable object threaded through the pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """All options for a reconstruction run.

    Future flags should be added here rather than threaded as kwargs through
    call sites, so the pipeline signature stays stable.
    """

    export_root: Path
    output_root: Path
    layout: str = "classic"
    naming: str = "by_year"
    image_format: str = "jpeg"
    jpeg_quality: int = 80
    resolution_scale: float = 1.0
    embed_gps: bool = True
    embed_caption: bool = True
