"""By-year output: `<output_root>/<YYYY>/<YYYY-MM-DD_HH-MM-SS>_bereal<suffix>.jpg`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rebereal.config import Config
from rebereal.models import Post


@dataclass(frozen=True)
class ByYearNaming:
    """Group outputs by year and timestamp-name each file."""

    name: str = "by_year"

    def output_path(self, post: Post, suffix: str, config: Config) -> Path:
        ts = post.taken_at.strftime("%Y-%m-%d_%H-%M-%S")
        year = post.taken_at.strftime("%Y")
        ext = _ext_for(config.image_format)
        retake = f"_r{post.retake_counter}" if post.retake_counter > 0 else ""
        return config.output_root / year / f"{ts}_bereal{suffix}{retake}.{ext}"


def _ext_for(image_format: str) -> str:
    fmt = image_format.lower()
    if fmt in ("jpeg", "jpg"):
        return "jpg"
    if fmt == "webp":
        return "webp"
    if fmt == "png":
        return "png"
    return fmt
