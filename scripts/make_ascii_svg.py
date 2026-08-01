#!/usr/bin/env python3
"""
===============================================================================
  HIGH-FIDELITY ASCII PORTRAIT GENERATOR — COMPLETE REWRITE
===============================================================================

Converts a preprocessed grayscale portrait into a centered, animated ASCII
SVG suitable for GitHub profile READMEs.

Design philosophy:
  - The CHARACTER RAMP does the heavy lifting. A 70-char ramp gives us 70
    distinct density levels — far more than enough for photorealistic output.
  - We do NOT over-process the image. The prepped photo already has good
    contrast. We just resize and map faithfully.
  - The INVERSION matters: in the source photo, dark pixels = hair/glasses.
    On a dark SVG background, we want those features BRIGHT. So dark source
    pixels → dense characters → bright colors. This is naturally handled by
    mapping low pixel values to the front of the ramp (dense chars).

Usage:
  python scripts/make_ascii_svg.py -i assets/source-prepped.png -o avi-ascii.svg -w 120
===============================================================================
"""

import os
import sys
import argparse
import html
import cv2
import numpy as np
from PIL import Image


# ---------------------------------------------------------------------------
# CHARACTER DENSITY RAMP (70 levels, dense → sparse)
# ---------------------------------------------------------------------------
# Characters sorted by approximate visual density when rendered in a
# monospace font. Index 0 is the densest (darkest source pixel → brightest
# on dark background), last index is space (brightest source pixel → empty).
RAMP = list(
    "$@B%8&WM#*oahkbdpqwm"
    "ZO0QLCJUYXzcvuxrjft/"
    "\\|()1{}[]?-_+~<>i!lI"
    ";:,\"^`'. "
)
NUM_LEVELS = len(RAMP) - 1  # 69


# ---------------------------------------------------------------------------
# GITHUB DARK THEME PALETTE
# ---------------------------------------------------------------------------
def pixel_to_color(px: float) -> str:
    """
    Map source pixel luminance to a GitHub-dark-friendly color.
    Lower pixel value = darker in source = brighter/more prominent character.
    """
    if px < 50:
        return "#e6edf3"   # near-white: hair, glasses frames, pupils, shirt
    elif px < 100:
        return "#79c0ff"   # cyan: facial contours, beard, mustache
    elif px < 150:
        return "#58a6ff"   # blue: mid-tone skin, shadows
    elif px < 200:
        return "#8b949e"   # gray: light skin, teeth, eye whites
    else:
        return "#484f58"   # dim gray: faint details near background


# ---------------------------------------------------------------------------
# CORE PIPELINE
# ---------------------------------------------------------------------------
def load_and_prepare(image_path: str, width: int) -> tuple:
    """
    Load the prepped grayscale image, build a foreground mask, and resize
    to the target column width with correct monospace aspect ratio.

    Returns: (resized_gray, resized_mask, grid_width, grid_height)
    """
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        img = np.array(Image.open(image_path))

    # Extract grayscale + foreground mask
    if len(img.shape) == 3 and img.shape[2] == 4:
        gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
        fg_mask = img[:, :, 3] > 20
    elif len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        fg_mask = gray < 240
    else:
        gray = img
        fg_mask = gray < 240

    # Resize with correct monospace aspect ratio
    # Monospace chars are ~2:1 height:width, so we scale height by 0.5
    h_orig, w_orig = gray.shape
    aspect = h_orig / w_orig
    height = int(width * aspect * 0.5)

    resized = np.array(
        Image.fromarray(gray).resize((width, height), Image.Resampling.LANCZOS)
    )
    mask_resized = np.array(
        Image.fromarray((fg_mask * 255).astype(np.uint8)).resize(
            (width, height), Image.Resampling.NEAREST
        )
    ) > 128

    return resized, mask_resized, width, height


def image_to_ascii(gray: np.ndarray, mask: np.ndarray) -> tuple:
    """
    Convert a resized grayscale image into a 2D grid of (character, color) tuples.

    The mapping is simple and faithful:
      pixel_value / 255 * NUM_LEVELS → index into RAMP

    Background pixels (mask=False) become spaces.
    """
    h, w = gray.shape
    char_grid = []
    color_grid = []

    for y in range(h):
        char_row = []
        color_row = []
        for x in range(w):
            if not mask[y, x] or gray[y, x] >= 245:
                char_row.append(" ")
                color_row.append("#0d1117")  # matches background
            else:
                px = gray[y, x]
                idx = int(round((px / 255.0) * NUM_LEVELS))
                idx = max(0, min(NUM_LEVELS, idx))
                char_row.append(RAMP[idx])
                color_row.append(pixel_to_color(px))
        char_grid.append(char_row)
        color_grid.append(color_row)

    return char_grid, color_grid


# ---------------------------------------------------------------------------
# SVG RENDERER
# ---------------------------------------------------------------------------
def render_svg(char_grid: list, color_grid: list, output_path: str,
               font_size: float = 3.6, line_height: float = 4.8):
    """
    Render the ASCII grid as an animated SVG with:
      - GitHub-dark background (#0d1117)
      - Monospace font stack
      - Row-by-row left-to-right SMIL reveal animation
      - Grouped <tspan> elements for same-color runs (file size optimization)
    """
    num_rows = len(char_grid)
    svg_w = 370
    svg_h = max(400, int(num_rows * line_height) + 30)
    y_start = 16

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
                 f'viewBox="0 0 {svg_w} {svg_h}" '
                 f'width="{svg_w}" height="{svg_h}">')

    # Styles
    lines.append('  <style>')
    lines.append('    .bg { fill: #0d1117; rx: 6; stroke: #30363d; stroke-width: 0.5; }')
    lines.append(f'    text {{ font-family: ui-monospace, SFMono-Regular, '
                 f'"SF Mono", Consolas, "Courier New", monospace; '
                 f'font-size: {font_size}px; white-space: pre; font-weight: 600; }}')
    lines.append('  </style>')
    lines.append(f'  <rect width="{svg_w}" height="{svg_h}" class="bg"/>')

    # Clip-path definitions for row animation
    lines.append('  <defs>')
    for i in range(num_rows):
        cy = y_start + i * line_height - font_size
        delay = round(i * 0.02, 3)
        lines.append(f'    <clipPath id="r{i}">')
        lines.append(f'      <rect x="6" y="{cy:.1f}" width="0" height="{line_height + 2:.1f}">')
        lines.append(f'        <animate attributeName="width" from="0" to="{svg_w - 12}" '
                     f'begin="{delay}s" dur="0.04s" fill="freeze"/>')
        lines.append(f'      </rect>')
        lines.append(f'    </clipPath>')
    lines.append('  </defs>')

    # Text rows
    lines.append('  <g>')
    for i in range(num_rows):
        y_pos = y_start + i * line_height
        row_chars = char_grid[i]
        row_colors = color_grid[i]

        # Group consecutive same-color characters into <tspan> runs
        spans = []
        cur_color = None
        cur_text = ""
        for ch, col in zip(row_chars, row_colors):
            esc = html.escape(ch)
            if col == cur_color:
                cur_text += esc
            else:
                if cur_text:
                    spans.append(f'<tspan fill="{cur_color}">{cur_text}</tspan>')
                cur_color = col
                cur_text = esc
        if cur_text:
            spans.append(f'<tspan fill="{cur_color}">{cur_text}</tspan>')

        lines.append(f'    <text x="8" y="{y_pos:.1f}" clip-path="url(#r{i})">'
                     f'{"".join(spans)}</text>')

    lines.append('  </g>')
    lines.append('</svg>')

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Generated: '{output_path}' ({svg_w}×{svg_h}px, {num_rows} rows)")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="High-fidelity ASCII portrait → animated SVG")
    parser.add_argument("-i", "--input", default="assets/source-prepped.png")
    parser.add_argument("-o", "--output", default="avi-ascii.svg")
    parser.add_argument("-w", "--width", type=int, default=120,
                        help="Grid width in characters (default: 120)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: '{args.input}' not found.")
        sys.exit(1)

    print(f"[1/3] Loading & resizing '{args.input}' to {args.width} columns...")
    gray, mask, gw, gh = load_and_prepare(args.input, args.width)

    print(f"[2/3] Converting {gw}×{gh} grid to ASCII ({NUM_LEVELS + 1} density levels)...")
    chars, colors = image_to_ascii(gray, mask)

    print(f"[3/3] Rendering animated SVG...")
    render_svg(chars, colors, args.output)


if __name__ == "__main__":
    main()
