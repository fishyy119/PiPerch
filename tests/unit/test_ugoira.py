from __future__ import annotations

import zipfile
from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image, WebPImagePlugin

from piperch.domain.artworks import UgoiraFrame
from piperch.paths import AppPaths
from piperch.services.ugoira import UgoiraAnimationCache

if TYPE_CHECKING:
    from pathlib import Path


def test_animation_preserves_metadata_frame_order_and_timing(tmp_path: Path) -> None:
    source = tmp_path / "ugoira.zip"
    with zipfile.ZipFile(source, "w") as archive:
        for name, color in (("a.png", "red"), ("b.png", "green"), ("c.png", "blue")):
            data = BytesIO()
            with Image.new("RGB", (16, 12), color) as image:
                image.save(data, "PNG")
            archive.writestr(name, data.getvalue())
    frames = (UgoiraFrame("c.png", 40), UgoiraFrame("a.png", 100), UgoiraFrame("b.png", 160))
    cache = UgoiraAnimationCache(AppPaths.from_data_dir(tmp_path / "data"))
    target = cache.ensure_animation(123, source, frames, 85)

    with Image.open(target) as animation:
        assert isinstance(animation, WebPImagePlugin.WebPImageFile)
        assert animation.n_frames == 3
        for index, (delay, dominant_channel) in enumerate(((40, 2), (100, 0), (160, 1))):
            animation.seek(index)
            animation.load()
            assert animation.info["duration"] == delay
            color = animation.convert("RGB").getpixel((0, 0))
            assert isinstance(color, tuple)
            assert color[dominant_channel] == max(color)
