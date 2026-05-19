"""Render a grid of hero portraits with their accent color swatch below each.

Usage:
    python scripts/render_color_grid.py [--out PATH] [--cols N] [--cell SIZE]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    s = hex_str.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def load_font(size: int) -> ImageFont.ImageFont:
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render(out_path: Path, cols: int, cell: int) -> None:
    heroes = json.loads((REPO / "heroes.json").read_text(encoding="utf-8"))
    heroes.sort(key=lambda h: h["name"].lower())

    pad = 12
    swatch_h = 36
    label_h = 22
    tile_w = cell + 2 * pad
    tile_h = cell + swatch_h + label_h + 3 * pad
    rows = (len(heroes) + cols - 1) // cols

    bg = (24, 24, 28)
    label_color = (230, 230, 230)
    hex_color = (180, 180, 190)

    img = Image.new("RGB", (cols * tile_w, rows * tile_h), bg)
    draw = ImageDraw.Draw(img)
    name_font = load_font(15)
    hex_font = load_font(12)

    for i, h in enumerate(heroes):
        r, c = divmod(i, cols)
        x0 = c * tile_w + pad
        y0 = r * tile_h + pad

        portrait = Image.open(REPO / h["portrait"]).convert("RGB")
        portrait = portrait.resize((cell, cell), Image.LANCZOS)
        img.paste(portrait, (x0, y0))

        sw_y0 = y0 + cell + pad
        draw.rectangle(
            [x0, sw_y0, x0 + cell, sw_y0 + swatch_h],
            fill=hex_to_rgb(h["color"]),
        )

        text_y = sw_y0 + swatch_h + 4
        draw.text((x0, text_y), h["name"], fill=label_color, font=name_font)
        bbox = draw.textbbox((0, 0), h["color"], font=hex_font)
        draw.text(
            (x0 + cell - (bbox[2] - bbox[0]), text_y + 3),
            h["color"],
            fill=hex_color,
            font=hex_font,
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    print(f"wrote {out_path} ({img.width}x{img.height})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=REPO / "scripts" / "hero_colors.png")
    ap.add_argument("--cols", type=int, default=8)
    ap.add_argument("--cell", type=int, default=128)
    args = ap.parse_args()
    render(args.out, args.cols, args.cell)


if __name__ == "__main__":
    main()
