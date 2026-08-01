#!/usr/bin/env python3
"""
===============================================================================
  HIGH-ACCURACY ASCII PORTRAIT GENERATOR
===============================================================================

Uses SVG textLength attribute to guarantee each row of characters fills
the exact card width. No guessing at character widths.

Usage:
  python scripts/make_ascii_svg.py
===============================================================================
"""

import os
import sys
import argparse
import html
import cv2
import numpy as np
from PIL import Image


# 10-level ramp with visually distinct characters
RAMP = "@%#WMohd=:. "
NUM_LEVELS = len(RAMP) - 1  # 11


def pixel_to_color(px: float) -> str:
    """5-tier GitHub dark theme palette."""
    if px < 50:
        return "#e6edf3"
    elif px < 100:
        return "#79c0ff"
    elif px < 150:
        return "#58a6ff"
    elif px < 200:
        return "#8b949e"
    return "#484f58"


def load_and_resize(image_path: str, width: int) -> tuple:
    """Load image, extract foreground, resize."""
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        img = np.array(Image.open(image_path))

    if len(img.shape) == 3 and img.shape[2] == 4:
        gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
        fg_mask = img[:, :, 3] > 20
    elif len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        fg_mask = gray < 240
    else:
        gray = img
        fg_mask = gray < 240

    h_orig, w_orig = gray.shape
    # Character cells in monospace are ~2x taller than wide.
    # Scale height accordingly.
    height = int(width * (h_orig / w_orig) * 0.45)

    resized = np.array(
        Image.fromarray(gray).resize((width, height), Image.Resampling.LANCZOS)
    )
    mask_r = np.array(
        Image.fromarray((fg_mask * 255).astype(np.uint8)).resize(
            (width, height), Image.Resampling.NEAREST
        )
    ) > 128

    return resized, mask_r, width, height


def image_to_ascii(gray: np.ndarray, mask: np.ndarray) -> tuple:
    """Map pixels to characters and colors."""
    h, w = gray.shape
    chars, colors = [], []

    for y in range(h):
        cr, clr = [], []
        for x in range(w):
            if not mask[y, x] or gray[y, x] >= 248:
                cr.append(" ")
                clr.append("#0d1117")
            else:
                px = gray[y, x]
                idx = int(round((px / 255.0) * NUM_LEVELS))
                idx = max(0, min(NUM_LEVELS, idx))
                cr.append(RAMP[idx])
                clr.append(pixel_to_color(px))
        chars.append(cr)
        colors.append(clr)

    return chars, colors


def render_svg(chars: list, colors: list, output_path: str, cols: int):
    """
    Render SVG using textLength to guarantee characters fill the card width.
    """
    num_rows = len(chars)

    svg_w = 480
    x_margin = 6
    text_w = svg_w - 2 * x_margin  # usable text width

    # Font size determines line height only
    font_size = text_w / (cols * 0.62)  # approximate, but textLength forces fit
    line_height = font_size * 1.2
    svg_h = int(num_rows * line_height) + 20

    y_start = font_size + 6

    out = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
               f'viewBox="0 0 {svg_w} {svg_h}" '
               f'width="{svg_w}" height="{svg_h}">')
    out.append('  <style>')
    out.append('    .bg { fill: #0d1117; rx: 6; stroke: #30363d; stroke-width: 0.5; }')
    out.append(f'    text {{ font-family: ui-monospace, SFMono-Regular, '
               f'"SF Mono", Menlo, Consolas, monospace; '
               f'font-size: {font_size:.2f}px; white-space: pre; '
               f'letter-spacing: 0; }}')
    out.append('  </style>')
    out.append(f'  <rect width="{svg_w}" height="{svg_h}" class="bg"/>')

    # Row-by-row animation
    out.append('  <defs>')
    for i in range(num_rows):
        cy = y_start + i * line_height - font_size
        delay = round(i * 0.012, 3)
        out.append(f'    <clipPath id="r{i}">')
        out.append(f'      <rect x="0" y="{cy:.1f}" width="0" height="{line_height + 2:.1f}">')
        out.append(f'        <animate attributeName="width" from="0" to="{svg_w}" '
                   f'begin="{delay}s" dur="0.025s" fill="freeze"/>')
        out.append(f'      </rect>')
        out.append(f'    </clipPath>')
    out.append('  </defs>')

    out.append('  <g>')
    for i in range(num_rows):
        y_pos = y_start + i * line_height
        row_chars = chars[i]
        row_colors = colors[i]

        # Build row with <tspan> color groups
        spans = []
        cc, ct = None, ""
        for ch, col in zip(row_chars, row_colors):
            esc = html.escape(ch)
            if col == cc:
                ct += esc
            else:
                if ct:
                    spans.append(f'<tspan fill="{cc}">{ct}</tspan>')
                cc, ct = col, esc
        if ct:
            spans.append(f'<tspan fill="{cc}">{ct}</tspan>')

        # textLength forces the row to fill exactly text_w pixels
        out.append(f'    <text x="{x_margin}" y="{y_pos:.1f}" '
                   f'textLength="{text_w}" lengthAdjust="spacing" '
                   f'clip-path="url(#r{i})">'
                   f'{"".join(spans)}</text>')

    out.append('  </g>')
    out.append('</svg>')

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    print(f"Generated: '{output_path}' ({svg_w}×{svg_h}px, "
          f"{num_rows}×{cols}, font: {font_size:.2f}px)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-i", "--input", default="assets/source-prepped.png")
    p.add_argument("-o", "--output", default="avi-ascii.svg")
    p.add_argument("-w", "--width", type=int, default=100)
    args = p.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: '{args.input}' not found."); sys.exit(1)

    print(f"[1/3] Loading '{args.input}', resizing to {args.width} cols...")
    gray, mask, gw, gh = load_and_resize(args.input, args.width)

    print(f"[2/3] Mapping {gw}x{gh} grid -> {NUM_LEVELS+1}-level ramp...")
    chars, colors = image_to_ascii(gray, mask)

    print(f"[3/3] Rendering SVG with textLength fill...")
    render_svg(chars, colors, args.output, gw)


if __name__ == "__main__":
    main()
