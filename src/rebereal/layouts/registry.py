"""Name → Layout factory registry. Drop-in extension point for future layouts."""

from __future__ import annotations

from typing import Callable

from rebereal.layouts.base import Layout
from rebereal.layouts.classic import ClassicLayout

LAYOUTS: dict[str, Callable[[], Layout]] = {
    "classic": ClassicLayout,
}


def get_layout(name: str) -> Layout:
    """Construct the layout registered under `name`. Raises KeyError if unknown."""
    try:
        factory = LAYOUTS[name]
    except KeyError as e:
        known = ", ".join(sorted(LAYOUTS)) or "(none)"
        raise KeyError(f"unknown layout {name!r}; known: {known}") from e
    return factory()
