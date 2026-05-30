"""Resolve a media-object path from a BeReal export to an on-disk file.

Per `EXPORT_FORMAT.md` §2, every media object carries a path of the form

    /Photos/<userId>/<folder>/<filename>.<ext>

A minority of entries lack the leading slash. In both cases the on-disk file
lives at `<export>/Photos/<folder>/<filename>` — the first two path segments
(the leading `Photos/` and the user-id segment) are discarded.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath


def resolve(media_path: str, export_root: Path) -> Path:
    """Map a media object's `path` field to an absolute on-disk Path.

    Strips the first two path segments (`Photos/<userId>`) regardless of
    whether the input begins with a leading slash. The remaining segments
    are joined under `<export_root>/Photos/`.

    Raises ValueError if the path has fewer than three segments.
    """
    if not media_path:
        raise ValueError("media_path is empty")

    posix = PurePosixPath(media_path)
    parts = [p for p in posix.parts if p not in ("/", "")]
    if len(parts) < 3:
        raise ValueError(f"media_path too short to resolve: {media_path!r}")

    tail = parts[2:]
    return export_root / "Photos" / Path(*tail)
