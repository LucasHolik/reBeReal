"""Layout strategies and the registry that exposes them by name."""

from rebereal.layouts.base import ComposedImage, Layout
from rebereal.layouts.classic import ClassicLayout
from rebereal.layouts.registry import LAYOUTS, get_layout

__all__ = ["ComposedImage", "Layout", "ClassicLayout", "LAYOUTS", "get_layout"]
