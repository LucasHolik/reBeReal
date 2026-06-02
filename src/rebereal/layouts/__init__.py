"""Layout strategies and the registry that exposes them by name."""

from rebereal.layouts.base import ComposedImage, Layout
from rebereal.layouts.classic import ClassicLayout
from rebereal.layouts.inverted_classic import InvertedClassicLayout
from rebereal.layouts.registry import LAYOUTS, get_layout, layout_labels
from rebereal.layouts.side_by_side import SideBySideLayout

__all__ = [
    "ComposedImage",
    "Layout",
    "ClassicLayout",
    "InvertedClassicLayout",
    "SideBySideLayout",
    "LAYOUTS",
    "get_layout",
    "layout_labels",
]
