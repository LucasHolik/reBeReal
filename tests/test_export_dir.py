"""Tests for per-run export-folder resolution."""

from __future__ import annotations

from pathlib import Path

from rebereal.output_dir import resolve_export_dir


def test_empty_parent_returns_export(tmp_path: Path) -> None:
    assert resolve_export_dir(tmp_path) == tmp_path / "export"


def test_existing_export_returns_first_numbered(tmp_path: Path) -> None:
    (tmp_path / "export").mkdir()
    assert resolve_export_dir(tmp_path) == tmp_path / "export(1)"


def test_skips_to_next_free_number(tmp_path: Path) -> None:
    (tmp_path / "export").mkdir()
    (tmp_path / "export(1)").mkdir()
    assert resolve_export_dir(tmp_path) == tmp_path / "export(2)"


def test_custom_base(tmp_path: Path) -> None:
    assert resolve_export_dir(tmp_path, base="run") == tmp_path / "run"
