"""Side-by-side composite — both cameras at equal size, stitched horizontally (back | front)."""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from rebereal.layouts.base import ComposedImage


@dataclass(frozen=True)
class SideBySideLayout:
    """Back and front stitched left-to-right, normalized to a common height.

    `gutter_pct` is a thin white separator between the two frames (fraction of the
    common height); it defaults to 0 (no gap). A future orientation field could
    switch to vertical stacking without changing the registry wiring.
    """

    name: str = "side_by_side"
    label: str = "Side by side"
    gutter_pct: float = 0.0

    def compose(self, back: Image.Image, front: Image.Image) -> list[ComposedImage]:
        back_rgb = back.convert("RGB")
        front_rgb = front.convert("RGB")

        # Normalize both frames to a common height (the back camera's), scaling the
        # front to match while preserving its aspect ratio.
        height = back_rgb.height
        if front_rgb.height != height:
            front_w = max(1, int(round(front_rgb.width * height / front_rgb.height)))
            front_rgb = front_rgb.resize((front_w, height), Image.LANCZOS)

        gutter = max(0, int(round(height * self.gutter_pct)))
        total_w = back_rgb.width + gutter + front_rgb.width

        canvas = Image.new("RGB", (total_w, height), (255, 255, 255))
        canvas.paste(back_rgb, (0, 0))
        canvas.paste(front_rgb, (back_rgb.width + gutter, 0))
        return [ComposedImage(image=canvas, suffix="")]
