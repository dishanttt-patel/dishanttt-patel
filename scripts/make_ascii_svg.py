#!/usr/bin/env python3
"""
make_ascii_svg.py

High-quality ASCII portrait SVG generator (User Script with Floyd-Steinberg Dithering).

Features
--------
- Auto contrast
- Histogram equalization
- Unsharp masking
- Gamma correction
- High-quality resize
- Floyd-Steinberg dithering
- 70-level ASCII ramp
- Animated SVG (row-by-row reveal)
"""

import argparse
import html
import os
import numpy as np
from PIL import Image, ImageFilter, ImageOps

ASCII_RAMP = (
    "$@B%8&WM#*oahkbdpqwm"
    "ZO0QLCJUYXzcvuxrjft/\\|()1{}[]?-_+~<>i!"
    "lI;:,\"^`'. "
)


def get_char_color(v):
    if v < 40:
        return "#79c0ff"
    elif v < 80:
        return "#58a6ff"
    elif v < 130:
        return "#8ab4f8"
    elif v < 180:
        return "#8b949e"
    return "#484f58"


def preprocess(img):
    img = ImageOps.autocontrast(img)
    img = ImageOps.equalize(img)
    img = img.filter(
        ImageFilter.UnsharpMask(radius=2, percent=220, threshold=2)
    )
    gamma = 0.85
    lut = [pow(i / 255.0, gamma) * 255 for i in range(256)]
    return img.point(lut)


def floyd(arr):
    h, w = arr.shape
    levels = len(ASCII_RAMP) - 1

    for y in range(h - 1):
        for x in range(w - 1):
            old = arr[y, x]
            new = round(old / 255 * levels) * (255 / levels)
            err = old - new
            arr[y, x] = new
            arr[y, x + 1] += err * 7 / 16
            if x > 0:
                arr[y + 1, x - 1] += err * 3 / 16
            arr[y + 1, x] += err * 5 / 16
            arr[y + 1, x + 1] += err * 1 / 16
    return np.clip(arr, 0, 255)


def image_to_ascii(path, width):
    img = Image.open(path).convert("L")
    img = preprocess(img)

    aspect = img.height / img.width
    height = int(width * aspect * 0.52)

    img = img.resize((width, height), Image.Resampling.LANCZOS)

    px = np.array(img, dtype=np.float32)
    px = floyd(px)

    chars = []
    vals = []

    for row in px:
        crow = []
        vrow = []
        for p in row:
            idx = int((p / 255) * (len(ASCII_RAMP) - 1))
            crow.append(ASCII_RAMP[idx])
            vrow.append(int(p))
        chars.append(crow)
        vals.append(vrow)

    return chars, vals


def render_svg(chars, vals, output,
               font_size=5.2,
               line_height=6.7,
               duration=0.035):

    rows = len(chars)
    cols = len(chars[0])

    width = cols * 4.35 + 20
    height = rows * line_height + 25

    y0 = 18

    out = []

    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width:.0f} {height:.0f}" width="{width:.0f}" height="{height:.0f}">'
    )

    out.append("<style>")
    out.append(".bg{fill:#0d1117;rx:8px;stroke:#30363d;stroke-width:1px;}")
    out.append(
        f'.ascii{{font-family:Consolas,"Courier New",monospace;'
        f'font-size:{font_size}px;font-weight:700;white-space:pre;}}'
    )
    out.append("</style>")

    out.append(f'<rect class="bg" width="{width:.0f}" height="{height:.0f}"/>')

    out.append("<defs>")

    for r in range(rows):
        delay = r * duration
        out.append(f'<clipPath id="c{r}">')
        out.append(
            f'<rect x="0" y="{y0+r*line_height-font_size}" width="0" '
            f'height="{line_height+2}">'
        )
        out.append(
            f'<animate attributeName="width" from="0" '
            f'to="{width}" begin="{delay:.3f}s" '
            f'dur="{duration*1.5:.3f}s" fill="freeze"/>'
        )
        out.append("</rect></clipPath>")

    out.append("</defs>")
    out.append('<g class="ascii">')

    for r in range(rows):

        spans = []
        current = None
        text = ""

        for c in range(cols):

            color = get_char_color(vals[r][c])
            ch = html.escape(chars[r][c])

            if color == current:
                text += ch
            else:
                if text:
                    spans.append(
                        f'<tspan fill="{current}">{text}</tspan>'
                    )
                current = color
                text = ch

        if text:
            spans.append(f'<tspan fill="{current}">{text}</tspan>')

        out.append(
            f'<text x="10" y="{y0+r*line_height}" '
            f'clip-path="url(#c{r})">{"".join(spans)}</text>'
        )

    out.append("</g></svg>")

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    with open(output, "w", encoding="utf8") as f:
        f.write("\n".join(out))


def main():
    p = argparse.ArgumentParser(description="High-quality ASCII portrait SVG generator")
    p.add_argument("-i", "--input", default="assets/source-prepped.png", help="Path to input image")
    p.add_argument("-o", "--output", default="avi-ascii.svg", help="Output SVG path")
    p.add_argument("-w", "--width", type=int, default=80, help="Grid width")

    args = p.parse_args()

    chars, vals = image_to_ascii(args.input, args.width)
    render_svg(chars, vals, args.output)

    print("Saved:", args.output)


if __name__ == "__main__":
    main()
