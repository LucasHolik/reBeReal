"""Name → Layout factory registry. Drop-in extension point for future layouts."""

from __future__ import annotations

from typing import Callable

from rebereal.layouts.base import Layout
from rebereal.layouts.classic import ClassicLayout
from rebereal.layouts.inverted_classic import InvertedClassicLayout
from rebereal.layouts.side_by_side import SideBySideLayout

LAYOUTS: dict[str, Callable[[], Layout]] = {
    "classic": ClassicLayout,
    "inverted_classic": InvertedClassicLayout,
    "side_by_side": SideBySideLayout,
}


def get_layout(name: str) -> Layout:
    """Construct the layout registered under `name`. Raises KeyError if unknown."""
    try:
        factory = LAYOUTS[name]
    except KeyError as e:
        known = ", ".join(sorted(LAYOUTS)) or "(none)"
        raise KeyError(f"unknown layout {name!r}; known: {known}") from e
    return factory()


def layout_labels() -> dict[str, str]:
    """Map each registry key to its human-friendly display label (for UI menus)."""
    return {name: factory().label for name, factory in LAYOUTS.items()}
