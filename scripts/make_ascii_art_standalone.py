#!/usr/bin/env python3
"""
===============================================================================
                     HIGH-DEFINITIONAL ASCII ART & SVG GENERATOR
===============================================================================
Description:
    Converts a preprocessed profile photo into a high-fidelity monospaced ASCII
    portrait with SMIL row-by-row reveal animations and multi-tone terminal styling.

Features:
    1. 120-Column Ultra-HD Grid Resolution.
    2. Adaptive Aspect Ratio Correction (~1:0.52 monospaced character ratio).
    3. Multi-tone Terminal Styling (White, Cyan, Blue, Slate, Dim Gray).
    4. SMIL Animated SVG Output & Optional Plain Text (.txt) Output.

Usage:
    python make_ascii_art_standalone.py --input assets/source-prepped.png --output avi-ascii.svg --width 120
===============================================================================
"""

import os
import sys
import argparse
import html
import numpy as np
from PIL import Image, ImageEnhance, ImageOps

# High-precision 17-level character density ramp matching dark-to-light features
ASCII_RAMP = ["@", "#", "8", "$", "%", "&", "W", "M", "0", "Q", "P", "+", "=", ":", "-", ".", "."]


def get_char_color(char: str) -> str:
    """
    Returns multi-tone terminal color hexadecimal strings based on character density.
    
    Colors:
        - White (#ffffff): Glasses frames, dark hair, eyes, facial outlines
        - Bright Cyan (#79c0ff): Secondary hair highlights & primary features
        - Blue (#58a6ff): Mid-tone facial shading
        - Slate Gray (#8b949e): Soft skin tone transitions
        - Dim Gray (#484f58): Background dot-matrix grid
    """
    if char in ["@", "#", "8"]:
        return "#ffffff"
    elif char in ["$", "%", "&", "W"]:
        return "#79c0ff"
    elif char in ["M", "0", "Q", "P"]:
        return "#58a6ff"
    elif char in ["+", "=", ":"]:
        return "#8b949e"
    elif char in ["-", "."]:
        return "#484f58"
    return "#30363d"


def image_to_ascii_grid(image_path: str, width: int = 120) -> list:
    """
    Loads, crops, contrast-boosts, and downsamples an image into a 2D grid of ASCII characters.

    Args:
        image_path (str): Path to input image file (e.g. assets/source-prepped.png)
        width (int): Grid column count (default: 120 for Ultra-HD detail)

    Returns:
        list of list of str: 2D array of character rows
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Input image file '{image_path}' not found.")

    # Load image as Grayscale (8-bit pixels, 0..255)
    img = Image.open(image_path).convert("L")

    # 1. Crop upper 72% (head & shoulders) for maximum facial feature resolution
    w_orig, h_orig = img.size
    crop_img = img.crop((0, 0, w_orig, int(h_orig * 0.72)))

    # 2. Histogram Equalization & Sharpness Contrast Enhancement
    equalized = ImageOps.equalize(crop_img)
    enhanced = ImageEnhance.Contrast(equalized).enhance(1.4)
    enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.6)

    # 3. Monospaced Aspect Ratio Scaling (Standard font height-to-width ratio is ~1 : 0.52)
    aspect_ratio = enhanced.height / enhanced.width
    height = int(width * aspect_ratio * 0.52)

    # Downsample using high-quality Lanczos resampling
    img_resized = enhanced.resize((width, height), Image.Resampling.LANCZOS)
    np_img = np.array(img_resized)

    # 4. Map Grayscale Luminance (0..255) to Character Density Ramp
    num_ramp = len(ASCII_RAMP) - 1
    ascii_grid = []

    for y in range(height):
        row = []
        for x in range(width):
            pixel_val = np_img[y, x]
            idx = min(int((pixel_val / 255.0) * num_ramp), num_ramp)
            char = ASCII_RAMP[idx]
            row.append(char)
        ascii_grid.append(row)

    return ascii_grid


def render_animated_svg(ascii_grid: list, output_path: str, font_size: float = 4.2, line_height: float = 5.6):
    """
    Renders 2D ASCII character grid into an animated SMIL vector SVG card.

    Args:
        ascii_grid (list): 2D array of ASCII characters
        output_path (str): File path for generated SVG
        font_size (float): Character font size in pixels (default: 4.2px)
        line_height (float): Line height spacing in pixels (default: 5.6px)
    """
    num_rows = len(ascii_grid)
    svg_width = 370  # Standard container width matching GitHub README layout
    svg_height = max(500, int(num_rows * line_height) + 24)
    start_y = 18
    duration_per_line = 0.03  # Wipe animation duration per row (seconds)

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" width="{svg_width}" height="{svg_height}">',
        '  <style>',
        '    .bg { fill: #0d1117; rx: 8px; stroke: #30363d; stroke-width: 1px; }',
        f'    .ascii-text {{ font-family: ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Courier New", monospace; font-size: {font_size}px; white-space: pre; font-weight: 700; }}',
        '  </style>',
        f'  <rect width="{svg_width}" height="{svg_height}" class="bg" />',
        '  <defs>'
    ]

    # SMIL row-by-row horizontal wipe clip paths
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

    # Group adjacent identical colors into optimized <tspan> elements
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
    parser = argparse.ArgumentParser(description="High-Quality Monospaced ASCII Portrait & SVG Generator")
    parser.add_argument("--input", "-i", default="assets/source-prepped.png", help="Path to prepped photo")
    parser.add_argument("--output", "-o", default="avi-ascii.svg", help="Path to output SVG file")
    parser.add_argument("--txt", "-t", default=None, help="Optional path to save plain text ASCII (.txt)")
    parser.add_argument("--width", "-w", type=int, default=120, help="Grid width columns (default: 120)")

    args = parser.parse_args()

    # Generate 2D ASCII Grid
    ascii_grid = image_to_ascii_grid(args.input, width=args.width)

    # Render Animated SVG
    render_animated_svg(ascii_grid, args.output)

    # Save Plain Text if requested
    if args.txt:
        save_plain_text(ascii_grid, args.txt)


if __name__ == "__main__":
    main()
