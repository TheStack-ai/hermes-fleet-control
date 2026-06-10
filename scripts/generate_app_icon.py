#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets" / "icons"
ICONSET = ASSET_DIR / "HermesFleetControl.iconset"
ICNS = ASSET_DIR / "HermesFleetControl.icns"
PREVIEW = ASSET_DIR / "HermesFleetControl-1024.png"

ICON_FILES = {
    "icon_16x16.png": 16,
    "icon_16x16@2x.png": 32,
    "icon_32x32.png": 32,
    "icon_32x32@2x.png": 64,
    "icon_128x128.png": 128,
    "icon_128x128@2x.png": 256,
    "icon_256x256.png": 256,
    "icon_256x256@2x.png": 512,
    "icon_512x512.png": 512,
    "icon_512x512@2x.png": 1024,
}


def rounded_rect_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size, size), radius=radius, fill=255)
    return mask


def draw_h_icon(size: int) -> Image.Image:
    scale = size / 1024
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # Premium dark-blue squircle with a subtle vertical/radial feel.
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg_pixels = bg.load()
    assert bg_pixels is not None
    for y in range(size):
        for x in range(size):
            nx = (x / max(size - 1, 1)) - 0.5
            ny = (y / max(size - 1, 1)) - 0.5
            radial = max(0.0, 1.0 - (nx * nx + ny * ny) * 2.2)
            vertical = y / max(size - 1, 1)
            r = int(12 + 14 * radial + 2 * vertical)
            g = int(24 + 36 * radial + 8 * vertical)
            b = int(45 + 70 * radial + 18 * vertical)
            bg_pixels[x, y] = (r, g, b, 255)

    mask = rounded_rect_mask(size, int(220 * scale))
    canvas.alpha_composite(Image.composite(bg, Image.new("RGBA", (size, size), (0, 0, 0, 0)), mask))

    draw = ImageDraw.Draw(canvas)
    margin = int(92 * scale)
    # Outer hairline and inner glow.
    draw.rounded_rectangle(
        (margin, margin, size - margin, size - margin),
        radius=int(164 * scale),
        outline=(195, 235, 255, 58),
        width=max(2, int(8 * scale)),
    )
    draw.rounded_rectangle(
        (margin + int(24 * scale), margin + int(24 * scale), size - margin - int(24 * scale), size - margin - int(24 * scale)),
        radius=int(138 * scale),
        outline=(88, 198, 255, 34),
        width=max(1, int(4 * scale)),
    )

    # H monogram: two vertical rails + command bridge. Rounded and cut like a control glyph.
    stroke = int(118 * scale)
    radius = int(54 * scale)
    x1 = int(296 * scale)
    x2 = int(728 * scale)
    y_top = int(242 * scale)
    y_bot = int(782 * scale)
    y_mid = int(512 * scale)
    bridge_h = int(118 * scale)
    cyan = (156, 232, 255, 255)
    white = (238, 250, 255, 255)

    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for gx in (x1, x2):
        gd.rounded_rectangle((gx - stroke // 2, y_top, gx + stroke // 2, y_bot), radius=radius, fill=(75, 194, 255, 185))
    gd.rounded_rectangle((x1 - stroke // 2, y_mid - bridge_h // 2, x2 + stroke // 2, y_mid + bridge_h // 2), radius=radius, fill=(75, 194, 255, 185))
    glow = glow.filter(ImageFilter.GaussianBlur(max(4, int(18 * scale))))
    canvas.alpha_composite(glow)

    for gx in (x1, x2):
        draw.rounded_rectangle((gx - stroke // 2, y_top, gx + stroke // 2, y_bot), radius=radius, fill=white)
    draw.rounded_rectangle((x1 - stroke // 2, y_mid - bridge_h // 2, x2 + stroke // 2, y_mid + bridge_h // 2), radius=radius, fill=cyan)

    # Top-left reflection, clipped to the app shape.
    shine = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shine)
    sd.ellipse((int(-120 * scale), int(-180 * scale), int(650 * scale), int(460 * scale)), fill=(255, 255, 255, 22))
    shine.putalpha(Image.composite(shine.getchannel("A"), Image.new("L", (size, size), 0), mask))
    canvas.alpha_composite(shine)
    return canvas


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    if ICONSET.exists():
        shutil.rmtree(ICONSET)
    ICONSET.mkdir(parents=True)

    master = draw_h_icon(1024)
    master.save(PREVIEW)
    for name, size in ICON_FILES.items():
        image = master if size == 1024 else master.resize((size, size), Image.Resampling.LANCZOS)
        image.save(ICONSET / name)

    subprocess.run(["iconutil", "-c", "icns", str(ICONSET), "-o", str(ICNS)], check=True)
    print(ICNS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
