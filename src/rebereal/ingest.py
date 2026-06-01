"""Resolve a user-selected data source (a folder or a `.zip`) to an export root.

The rest of the pipeline is filesystem-based: it reads `posts.json` and the
`Photos/` tree from a real directory on disk (see `pipeline.Reconstructor` and
`media.resolve`). This module is the thin adapter in front of that: given
whatever the user dropped or picked, it returns a plain directory that directly
contains `posts.json`, extracting a zip to a scratch directory first when
needed. Keeping it here (headless, no GUI import) lets the CLI grow zip support
later without depending on Qt.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int], None]

# The file whose presence marks a directory as a BeReal export root.
_MARKER = "posts.json"


class ExportNotFound(Exception):
    """No directory containing `posts.json` was found in the given source."""


def find_export_root(root: Path, max_depth: int = 2) -> Path:
    """Return the directory at or below `root` that directly contains `posts.json`.

    A BeReal export does not always sit at the top level of what the user hands
    us: a zip frequently expands into a single wrapper folder, and a user may
    pick the parent of the export. So we look at `root` itself and descend up to
    `max_depth` levels of subdirectories, breadth-first, returning the first
    match (shallowest wins).

    Raises `ExportNotFound` if no marker file is found within the depth budget.
    """
    # (directory, depth) queue, breadth-first so the shallowest match wins.
    queue: list[tuple[Path, int]] = [(root, 0)]
    while queue:
        directory, depth = queue.pop(0)
        if (directory / _MARKER).is_file():
            return directory
        if depth < max_depth:
            for child in sorted(directory.iterdir()):
                if child.is_dir():
                    queue.append((child, depth + 1))
    raise ExportNotFound(f"no {_MARKER} found under {root}")


def extract_zip(
    zip_path: Path,
    dest: Path,
    progress_cb: ProgressCallback | None = None,
) -> None:
    """Extract every member of `zip_path` into `dest`.

    `progress_cb(done, total)` is invoked after each member so a caller can
    drive a progress bar. Extraction can be slow for multi-GB exports, so this
    is expected to run off the UI thread.
    """
    with zipfile.ZipFile(zip_path) as archive:
        members = archive.infolist()
        total = len(members)
        for i, member in enumerate(members, start=1):
            archive.extract(member, dest)
            if progress_cb is not None:
                progress_cb(i, total)


def prepare_source(
    selected: Path,
    dest: Path,
    progress_cb: ProgressCallback | None = None,
) -> Path:
    """Resolve a picked/dropped path to a usable export-root directory.

    - A `.zip` is extracted into `dest` (with progress) and then searched for
      the export root.
    - A directory is searched directly; `dest` is unused.

    Returns the resolved export root. Raises `ExportNotFound` if no `posts.json`
    turns up, or `ValueError` if `selected` is neither a directory nor a zip.
    """
    if selected.is_file() and selected.suffix.lower() == ".zip":
        log.info("extracting %s", selected.name)
        extract_zip(selected, dest, progress_cb)
        return find_export_root(dest)
    if selected.is_dir():
        return find_export_root(selected)
    raise ValueError(f"not a folder or .zip: {selected}")
