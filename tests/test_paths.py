"""Tests for media-path resolution edge cases."""

from __future__ import annotations

from pathlib import Path

import pytest

from rebereal.media.paths import resolve


def test_resolve_leading_slash(tmp_path: Path) -> None:
    p = resolve("/Photos/user-123/post/abc.webp", tmp_path)
    assert p == tmp_path / "Photos" / "post" / "abc.webp"


def test_resolve_no_leading_slash(tmp_path: Path) -> None:
    p = resolve("Photos/user-123/bereal/xyz-1657272804.jpg", tmp_path)
    assert p == tmp_path / "Photos" / "bereal" / "xyz-1657272804.jpg"


def test_resolve_secondary_suffix(tmp_path: Path) -> None:
    p = resolve("/Photos/u/bereal/abc-1657272804-secondary.jpg", tmp_path)
    assert p.name == "abc-1657272804-secondary.jpg"
    assert p.parent.name == "bereal"


def test_resolve_too_short_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        resolve("/Photos/userOnly", tmp_path)


def test_resolve_empty_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        resolve("", tmp_path)
