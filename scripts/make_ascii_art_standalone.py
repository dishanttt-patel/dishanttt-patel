#!/usr/bin/env python3
"""
===============================================================================
               ACCURATE BILATERAL ASCII PORTRAIT & SVG GENERATOR
===============================================================================
Description:
    Converts a profile photo into an accurate monospaced ASCII portrait SVG.
    Uses OpenCV Bilateral Edge-Preserving Filtering to smooth skin noise while
    keeping glasses frames, eyes, pupils, mustache, and facial contours 100% sharp.

Usage:
    python make_ascii_art_standalone.py --input assets/input_photo.png --output avi-ascii.svg --txt avi-ascii.txt --width 110
===============================================================================
"""

import os
import sys
import argparse
import html
import cv2
import numpy as np
from PIL import Image

# 17-level density ramp for smooth feature rendering
ASCII_RAMP = ["@", "#", "8", "$", "%", "&", "W", "M", "0", "Q", "P", "+", "=", ":", "-", ".", "."]


def get_char_color(char: str) -> str:
    """Returns multi-tone colors for SVG rendering."""
    if char in ["@", "#", "8"]:
        return "#ffffff"  # Bright white for glasses, hair, eyes
    elif char in ["$", "%", "&", "W"]:
        return "#79c0ff"  # Bright cyan
    elif char in ["M", "0", "Q", "P"]:
        return "#58a6ff"  # Primary blue
    elif char in ["+", "=", ":"]:
        return "#8b949e"  # Slate gray skin tone
    elif char in ["-", "."]:
        return "#484f58"  # Dim gray background dot
    return "#30363d"


def image_to_ascii_grid(image_path: str, width: int = 110) -> list:
    """Converts image to clean 2D ASCII grid preserving sharp facial features."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Input image file '{image_path}' not found.")

    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        pil_img = Image.open(image_path).convert("L")
        img = np.array(pil_img)

    # Crop upper 72% for head & shoulders focus
    h_orig, w_orig = img.shape
    crop = img[0:int(h_orig * 0.72), 0:w_orig]

    # Bilateral filter to smooth skin noise while preserving sharp glasses/eyes/mustache edges
    filtered = cv2.bilateralFilter(crop, d=9, sigmaColor=75, sigmaSpace=75)

    pil_img = Image.fromarray(filtered)
    aspect_ratio = pil_img.height / pil_img.width
    height = int(width * aspect_ratio * 0.52)

    img_resized = pil_img.resize((width, height), Image.Resampling.LANCZOS)
    np_img = np.array(img_resized)

    num_ramp = len(ASCII_RAMP) - 1
    grid = []

    for y in range(height):
        row = []
        for x in range(width):
            px = np_img[y, x]
            idx = min(int((px / 255.0) * num_ramp), num_ramp)
            char = ASCII_RAMP[idx]
            row.append(char)
        grid.append(row)

    return grid


def render_animated_svg(ascii_grid: list, output_path: str, font_size: float = 4.6, line_height: float = 6.0):
    """Renders 2D ASCII character grid into an animated SMIL vector SVG card."""
    num_rows = len(ascii_grid)
    svg_width = 370
    svg_height = max(500, int(num_rows * line_height) + 24)
    start_y = 18
    duration_per_line = 0.03

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" width="{svg_width}" height="{svg_height}">',
        '  <style>',
        '    .bg { fill: #0d1117; rx: 8px; stroke: #30363d; stroke-width: 1px; }',
        f'    .ascii-text {{ font-family: ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Courier New", monospace; font-size: {font_size}px; white-space: pre; font-weight: 700; }}',
        '  </style>',
        f'  <rect width="{svg_width}" height="{svg_height}" class="bg" />',
        '  <defs>'
    ]

    for i in range(num_rows):
        clip_id = f"clip-row-{i}"
        row_y = start_y + (i * line_height) - font_size
        row_h = line_height + 2
        delay = round(i * duration_per_line, 3)
        anim_dur = round(duration_per_line * 1.5, 3)

        svg_lines.append(f'    <clipPath id="{clip_id}">')
        svg_lines.append(f'      <rect x="8" y="{row_y:.1f}" width="0" height="{row_h:.1f}">')
        svg_lines.append(f'        <animate attributeName="width" from="0" to="{svg_width - 16}" begin="{delay}s" dur="{anim_dur}s" fill="freeze" calcMode="spline" keySplines="0.4 0 0.2 1" />')
        svg_lines.append('      </rect>')
        svg_lines.append('    </clipPath>')

    svg_lines.append('  </defs>')
    svg_lines.append('  <g class="ascii-text">')

    for i, row_chars in enumerate(ascii_grid):
        clip_id = f"clip-row-{i}"
        y_pos = start_y + (i * line_height)

        spans = []
        curr_color = None
        curr_text = ""

        for char in row_chars:
            color = get_char_color(char)
            escaped_char = html.escape(char)
            if color == curr_color:
                curr_text += escaped_char
            else:
                if curr_text:
                    spans.append(f'<tspan fill="{curr_color}">{curr_text}</tspan>')
                curr_color = color
                curr_text = escaped_char
        if curr_text:
            spans.append(f'<tspan fill="{curr_color}">{curr_text}</tspan>')

        row_content = "".join(spans)
        svg_lines.append(f'    <text x="10" y="{y_pos:.1f}" clip-path="url(#{clip_id})">{row_content}</text>')

    svg_lines.append('  </g>')
    svg_lines.append('</svg>')

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_lines))

    print(f"[+] Generated Animated SVG: '{output_path}' ({svg_width}x{svg_height}px)")


def save_plain_text(ascii_grid: list, txt_path: str):
    """Saves the ASCII grid to a plain text (.txt) file."""
    os.makedirs(os.path.dirname(txt_path) or ".", exist_ok=True)
    with open(txt_path, "w", encoding="utf-8") as f:
        for row in ascii_grid:
            f.write("".join(row) + "\n")
    print(f"[+] Saved Plain Text ASCII: '{txt_path}'")


def main():
    parser = argparse.ArgumentParser(description="Accurate Monospaced ASCII Portrait & SVG Generator")
    parser.add_argument("--input", "-i", default="assets/input_photo.png", help="Path to input photo")
    parser.add_argument("--output", "-o", default="avi-ascii.svg", help="Path to output SVG file")
    parser.add_argument("--txt", "-t", default=None, help="Optional path to save plain text ASCII (.txt)")
    parser.add_argument("--width", "-w", type=int, default=110, help="Grid width columns (default: 110)")

    args = parser.parse_args()

    ascii_grid = image_to_ascii_grid(args.input, width=args.width)
    render_animated_svg(ascii_grid, args.output)

    if args.txt:
        save_plain_text(ascii_grid, args.txt)


if __name__ == "__main__":
    main()
