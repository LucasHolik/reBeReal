"""Tests for the data-source ingest adapter (folder / zip → export root)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from rebereal.ingest import (
    ExportNotFound,
    extract_zip,
    find_export_root,
    prepare_source,
)


def _make_export(root: Path) -> Path:
    """Create a minimal export (posts.json + a Photos file) under `root`."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "posts.json").write_text("[]", encoding="utf-8")
    photos = root / "Photos" / "post"
    photos.mkdir(parents=True)
    (photos / "x.webp").write_bytes(b"fake")
    return root


# --- find_export_root -----------------------------------------------------


def test_find_export_root_at_top_level(tmp_path: Path) -> None:
    _make_export(tmp_path)
    assert find_export_root(tmp_path) == tmp_path


def test_find_export_root_one_level_nested(tmp_path: Path) -> None:
    inner = _make_export(tmp_path / "BeReal_export")
    assert find_export_root(tmp_path) == inner


def test_find_export_root_prefers_shallowest(tmp_path: Path) -> None:
    _make_export(tmp_path)
    _make_export(tmp_path / "nested")
    assert find_export_root(tmp_path) == tmp_path


def test_find_export_root_raises_when_absent(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    with pytest.raises(ExportNotFound):
        find_export_root(tmp_path)


def test_find_export_root_respects_depth_budget(tmp_path: Path) -> None:
    _make_export(tmp_path / "a" / "b" / "c")
    with pytest.raises(ExportNotFound):
        find_export_root(tmp_path, max_depth=2)


# --- extract_zip ----------------------------------------------------------


def test_extract_zip_extracts_and_reports_progress(tmp_path: Path) -> None:
    src = _make_export(tmp_path / "src")
    archive = tmp_path / "export.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for path in sorted(src.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(src))

    dest = tmp_path / "out"
    seen: list[tuple[int, int]] = []
    extract_zip(archive, dest, progress_cb=lambda done, total: seen.append((done, total)))

    assert (dest / "posts.json").is_file()
    assert (dest / "Photos" / "post" / "x.webp").is_file()
    # Progress is reported once per member and ends at done == total.
    assert seen and seen[-1][0] == seen[-1][1]


# --- prepare_source -------------------------------------------------------


def test_prepare_source_with_directory(tmp_path: Path) -> None:
    export = _make_export(tmp_path / "export")
    assert prepare_source(export, tmp_path / "scratch") == export


def test_prepare_source_with_zip(tmp_path: Path) -> None:
    src = _make_export(tmp_path / "src")
    archive = tmp_path / "export.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for path in sorted(src.rglob("*")):
            if path.is_file():
                zf.write(path, Path("BeReal_export") / path.relative_to(src))

    dest = tmp_path / "scratch"
    root = prepare_source(archive, dest)
    assert root == dest / "BeReal_export"
    assert (root / "posts.json").is_file()


def test_prepare_source_rejects_other(tmp_path: Path) -> None:
    bogus = tmp_path / "note.txt"
    bogus.write_text("hi", encoding="utf-8")
    with pytest.raises(ValueError):
        prepare_source(bogus, tmp_path / "scratch")
