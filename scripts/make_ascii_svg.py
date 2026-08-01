#!/usr/bin/env python3
"""
make_ascii_svg.py
Converts profile photo into a high-definition, highly detailed ASCII portrait SVG matching the reference artwork.
Uses 115-column resolution, custom character density mapping, and multi-tone cyan/white terminal styling.
"""

import os
import sys
import argparse
import html
import numpy as np
from PIL import Image, ImageEnhance, ImageOps

# High-precision character ramp matching the reference portrait
ASCII_RAMP = ["@", "#", "8", "$", "%", "&", "W", "M", "0", "Q", "P", "+", "=", ":", "-", ".", "."]


def get_char_color(char: str) -> str:
    """Returns vibrant multi-tone colors matching character density."""
    if char in ["@", "#", "8"]:
        return "#ffffff"  # Bright white highlight for dark features/frames
    elif char in ["$", "%", "&", "W"]:
        return "#79c0ff"  # Bright cyan
    elif char in ["M", "0", "Q", "P"]:
        return "#58a6ff"  # Primary blue
    elif char in ["+", "=", ":"]:
        return "#8b949e"  # Slate gray
    elif char in ["-", "."]:
        return "#484f58"  # Dim gray background dot
    return "#30363d"


def image_to_ascii(image_path: str, width: int = 110) -> list:
    """Converts image to clean high-definition ASCII portrait matching reference design."""
    if not os.path.exists(image_path):
        print(f"Warning: Image '{image_path}' not found. Generating sample avatar pattern.")
        return generate_sample_ascii(width, int(width * 0.52))

    img = Image.open(image_path).convert("L")

    # If full body photo, crop upper 70% (head & shoulders) for maximum facial detail
    w_orig, h_orig = img.size
    crop_img = img.crop((0, 0, w_orig, int(h_orig * 0.72)))

    # Enhance contrast & sharpness slightly for crisp glasses & feature contours
    crop_img = ImageEnhance.Contrast(crop_img).enhance(1.3)
    crop_img = ImageEnhance.Sharpness(crop_img).enhance(1.4)

    # Monospace aspect ratio correction (~1 : 0.52 ratio)
    aspect_ratio = crop_img.height / crop_img.width
    height = int(width * aspect_ratio * 0.52)

    img_resized = crop_img.resize((width, height), Image.Resampling.LANCZOS)
    np_img = np.array(img_resized)

    lines = []
    num_ramp = len(ASCII_RAMP) - 1

    for y in range(height):
        row = []
        for x in range(width):
            px = np_img[y, x]
            # Map luminance (0..255) to character density
            idx = min(int((px / 255.0) * num_ramp), num_ramp)
            char = ASCII_RAMP[idx]
            row.append(char)
        lines.append(row)
    return lines


def generate_sample_ascii(width: int = 110, height: int = 55) -> list:
    lines = []
    for y in range(height):
        row = []
        for x in range(width):
            row.append(".")
        lines.append(row)
    return lines


def render_ascii_svg(lines: list, output_path: str, font_size: float = 4.6, line_height: float = 6.0,
                     duration_per_line: float = 0.035):
    """Renders ASCII lines into a multi-toned animated SMIL SVG file."""
    num_rows = len(lines)
    max_cols = max(len(line) for line in lines) if lines else 110

    svg_width = 370  # Fixed width to fit top row layout
    svg_height = max(500, int(num_rows * line_height) + 24)

    start_y = 18

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" width="{svg_width}" height="{svg_height}">',
        '  <style>',
        '    .bg { fill: #0d1117; rx: 8px; stroke: #30363d; stroke-width: 1px; }',
        f'    .ascii-text {{ font-family: ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Courier New", monospace; font-size: {font_size}px; white-space: pre; font-weight: 700; }}',
        '  </style>',
        f'  <rect width="{svg_width}" height="{svg_height}" class="bg" />',
        '  <defs>'
    ]

    # Clip paths for row-by-row horizontal wipe animation
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

    # Render each row with multi-colored character spans
    for i, line_chars in enumerate(lines):
        clip_id = f"clip-row-{i}"
        y_pos = start_y + (i * line_height)

        spans = []
        curr_color = None
        curr_text = ""

        for char in line_chars:
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

    print(f"Successfully generated reference-matching ASCII SVG at '{output_path}' ({svg_width}x{svg_height}px).")


def main():
    parser = argparse.ArgumentParser(description="Convert photo to reference-matching animated ASCII SVG")
    parser.add_argument("--input", "-i", default="assets/input_photo.png", help="Path to input photo")
    parser.add_argument("--output", "-o", default="avi-ascii.svg", help="Path to output SVG")
    parser.add_argument("--width", "-w", type=int, default=110, help="Character grid width (~100-115)")

    args = parser.parse_args()

    lines = image_to_ascii(args.input, width=args.width)
    render_ascii_svg(lines, args.output)


if __name__ == "__main__":
    main()
