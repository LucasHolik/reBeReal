"""Output-path / naming strategies. Drop in new modules to add groupings."""

from __future__ import annotations

from typing import Callable

from rebereal.naming.base import NamingStrategy
from rebereal.naming.by_year import ByYearNaming

NAMING_STRATEGIES: dict[str, Callable[[], NamingStrategy]] = {
    "by_year": ByYearNaming,
}


def get_naming(name: str) -> NamingStrategy:
    try:
        factory = NAMING_STRATEGIES[name]
    except KeyError as e:
        known = ", ".join(sorted(NAMING_STRATEGIES)) or "(none)"
        raise KeyError(f"unknown naming strategy {name!r}; known: {known}") from e
    return factory()


__all__ = ["NamingStrategy", "ByYearNaming", "NAMING_STRATEGIES", "get_naming"]
