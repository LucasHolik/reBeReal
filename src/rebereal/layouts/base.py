"""Layout protocol — compositing strategies plug in here."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from PIL import Image


@dataclass(frozen=True)
class ComposedImage:
    """A single output image from a layout pass.

    `suffix` is appended to the base filename — empty for single-output layouts,
    `"_back"` / `"_front"` for split layouts like options C and D.
    """

    image: Image.Image
    suffix: str = ""


class Layout(Protocol):
    """Composes the two source frames into one or more output images."""

    name: str
    label: str

    def compose(self, back: Image.Image, front: Image.Image) -> list[ComposedImage]: ...
