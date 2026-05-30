"""Headless entry point: `python -m rebereal --export ./Data --output ./Output`."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from rebereal.config import Config
from rebereal.logging_setup import configure
from rebereal.pipeline import build

log = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rebereal",
        description="Reconstruct BeReal posts from a BeReal data export.",
    )
    p.add_argument("--export", type=Path, required=True, help="Path to the BeReal export root")
    p.add_argument("--output", type=Path, required=True, help="Output directory for composites")
    p.add_argument("--layout", default="classic", help="Layout strategy name (default: classic)")
    p.add_argument("--naming", default="by_year", help="Naming strategy name (default: by_year)")
    p.add_argument("--jpeg-quality", type=int, default=80, help="JPEG quality 1-100 (default: 80)")
    p.add_argument(
        "--resolution",
        type=float,
        default=1.0,
        help="Output resolution as a fraction of source, 0.01-1.0; "
        "keeps aspect ratio (default: 1.0 = full)",
    )
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing output files")
    p.add_argument("--no-gps", action="store_true", help="Do not embed GPS EXIF tags")
    p.add_argument("--no-caption", action="store_true", help="Do not embed caption in XMP/IPTC metadata")
    p.add_argument("-v", "--verbose", action="store_true", help="Enable DEBUG logging")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    configure(level=logging.DEBUG if args.verbose else logging.INFO)

    config = Config(
        export_root=args.export.resolve(),
        output_root=args.output.resolve(),
        layout=args.layout,
        naming=args.naming,
        jpeg_quality=args.jpeg_quality,
        resolution_scale=args.resolution,
        overwrite=args.overwrite,
        embed_gps=not args.no_gps,
        embed_caption=not args.no_caption,
    )

    try:
        recon = build(config)
    except (KeyError, ValueError) as e:
        log.error("%s", e)
        return 2

    def progress(done: int, total: int) -> None:
        if total and (done % 25 == 0 or done == total):
            log.info("progress: %d / %d", done, total)

    summary = recon.run(progress_cb=progress)
    log.info("written=%d existing=%d skipped=%d warnings=%d",
             summary.written, summary.existing, summary.skipped, len(summary.warnings))
    return 0 if (summary.written + summary.existing) > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
