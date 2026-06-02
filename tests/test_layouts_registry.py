"""Guards the registry wiring that the CLI and GUI depend on."""

from __future__ import annotations

import pytest

from rebereal.layouts import LAYOUTS, get_layout, layout_labels


def test_expected_layouts_registered() -> None:
    assert {"classic", "inverted_classic", "side_by_side"} <= set(LAYOUTS)


@pytest.mark.parametrize("name", sorted(LAYOUTS))
def test_each_layout_resolves_with_label(name: str) -> None:
    layout = get_layout(name)
    assert layout.name == name
    assert isinstance(layout.label, str) and layout.label


def test_layout_labels_cover_every_key() -> None:
    labels = layout_labels()
    assert set(labels) == set(LAYOUTS)
    assert all(v for v in labels.values())


def test_unknown_layout_raises() -> None:
    with pytest.raises(KeyError):
        get_layout("does_not_exist")
