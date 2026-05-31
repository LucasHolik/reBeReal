"""Pipeline orchestrator: parse → resolve → compose → metadata → write."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from io import BytesIO
from pathlib import Path
from typing import Callable

from PIL import Image

from rebereal.config import Config
from rebereal.layouts import ComposedImage, Layout, get_layout
from rebereal.media import resolve, scale_image
from rebereal.metadata import (
    CompositeMetadataWriter,
    ExifWriter,
    IptcWriter,
    MetadataWriter,
    XmpWriter,
)
from rebereal.models import Post
from rebereal.naming import NamingStrategy, get_naming
from rebereal.output_dir import resolve_export_dir
from rebereal.parsers import PARSERS, PostParser

log = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int], None]

# Maps `Config.image_format` to the Pillow format name passed to `Image.save`.
# Add new entries here (plus matching extension support in `naming/by_year.py`)
# when other output formats land — metadata writers are JPEG-specific today,
# so any new format will also need them gated.
IMAGE_FORMATS: dict[str, str] = {"jpeg": "JPEG", "jpg": "JPEG"}


@dataclass
class RunSummary:
    """Outcome of a single reconstruction run."""

    written: int = 0
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)
    output_dir: Path | None = None


@dataclass
class PreviewItem:
    """One in-memory composite produced by `Reconstructor.preview`."""

    post: Post
    images: list[ComposedImage]


class Reconstructor:
    """Wires parser + layout + metadata writer + naming strategy + config."""

    def __init__(
        self,
        config: Config,
        parser: PostParser,
        layout: Layout,
        metadata_writer: MetadataWriter,
        naming: NamingStrategy,
    ) -> None:
        self.config = config
        self.parser = parser
        self.layout = layout
        self.metadata_writer = metadata_writer
        self.naming = naming

    # --- public API -------------------------------------------------------

    def run(
        self,
        progress_cb: ProgressCallback | None = None,
        posts_path: Path | None = None,
    ) -> RunSummary:
        """Execute the full reconstruction. Returns a RunSummary."""
        # Rebase output_root onto a fresh per-run wrapper folder so each run is
        # self-contained. Resolved once here (not in build/preview) so previewing
        # never claims a folder name. Reconstructor is single-use.
        export_dir = resolve_export_dir(self.config.output_root)
        self.config = replace(self.config, output_root=export_dir)
        log.info("writing output to: %s", export_dir)

        summary = RunSummary(output_dir=export_dir)
        posts = list(self._load_posts(posts_path))
        total = len(posts)
        log.info("loaded %d posts", total)

        for i, post in enumerate(posts, start=1):
            try:
                wrote = self._process_post(post)
                summary.written += wrote
                if wrote == 0:
                    summary.skipped += 1
            except _SkipPost as e:
                log.warning("skipping post %s: %s", post.taken_at.isoformat(), e)
                summary.skipped += 1
                summary.warnings.append(str(e))
            except Exception as e:
                log.exception("unexpected error on post %s", post.taken_at.isoformat())
                summary.skipped += 1
                summary.warnings.append(f"{post.taken_at.isoformat()}: {e}")
            if progress_cb is not None:
                progress_cb(i, total)

        log.info(
            "done: %d written, %d skipped",
            summary.written,
            summary.skipped,
        )
        return summary

    def preview(self, n: int = 3, posts_path: Path | None = None) -> list[PreviewItem]:
        """Compose the first `n` non-skipped posts without writing to disk."""
        out: list[PreviewItem] = []
        for post in self._load_posts(posts_path):
            try:
                back_p = resolve(post.back_path, self.config.export_root)
                front_p = resolve(post.front_path, self.config.export_root)
                if not back_p.exists() or not front_p.exists():
                    continue
                with Image.open(back_p) as back, Image.open(front_p) as front:
                    composed = self.layout.compose(back, front)
                out.append(PreviewItem(post=post, images=composed))
                if len(out) >= n:
                    break
            except Exception:
                log.exception("preview failed for post %s", post.taken_at.isoformat())
                continue
        return out

    # --- internals --------------------------------------------------------

    def _load_posts(self, posts_path: Path | None):
        path = posts_path or (self.config.export_root / "posts.json")
        if not path.exists():
            raise FileNotFoundError(f"posts source not found: {path}")
        return self.parser.parse(path)

    def _process_post(self, post: Post) -> int:
        """Process a single post; return the number of images written."""
        back_p = resolve(post.back_path, self.config.export_root)
        front_p = resolve(post.front_path, self.config.export_root)
        if not back_p.exists():
            raise _SkipPost(f"missing back image: {back_p.name}")
        if not front_p.exists():
            raise _SkipPost(f"missing front image: {front_p.name}")

        with Image.open(back_p) as back, Image.open(front_p) as front:
            back.load()
            front.load()
            composed = self.layout.compose(back, front)

        written = 0
        for item in composed:
            out_path = self.naming.output_path(post, item.suffix, self.config)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_image(item.image, out_path, post)
            written += 1
        return written

    def _write_image(self, image: Image.Image, out_path: Path, post: Post) -> None:
        buf = BytesIO()
        image = scale_image(image, self.config.resolution_scale)
        pil_format = IMAGE_FORMATS[self.config.image_format.lower()]
        save_kwargs = {
            "format": pil_format,
            "quality": self.config.jpeg_quality,
            "optimize": True,
        }
        image.convert("RGB").save(buf, **save_kwargs)
        data = self.metadata_writer.inject(buf.getvalue(), post, self.config)
        out_path.write_bytes(data)


class _SkipPost(Exception):
    """Internal signal: skip this post and continue with the next."""


def build(config: Config, parser_name: str = "posts_json") -> Reconstructor:
    """Construct a Reconstructor from a Config and the chosen registry keys."""
    if config.image_format.lower() not in IMAGE_FORMATS:
        raise ValueError(
            f"unsupported image_format {config.image_format!r}; "
            f"supported: {sorted(IMAGE_FORMATS)}"
        )
    if not 0 < config.resolution_scale <= 1.0:
        raise ValueError(
            f"resolution_scale must be in (0, 1.0], got {config.resolution_scale}"
        )
    if not 1 <= config.jpeg_quality <= 100:
        raise ValueError(
            f"jpeg_quality must be in [1, 100], got {config.jpeg_quality}"
        )
    try:
        parser_factory = PARSERS[parser_name]
    except KeyError as e:
        raise KeyError(f"unknown parser {parser_name!r}") from e

    metadata_writer = CompositeMetadataWriter(
        [ExifWriter(), XmpWriter(), IptcWriter()]
    )

    return Reconstructor(
        config=config,
        parser=parser_factory(),
        layout=get_layout(config.layout),
        metadata_writer=metadata_writer,
        naming=get_naming(config.naming),
    )
