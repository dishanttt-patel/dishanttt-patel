#!/usr/bin/env python3
"""
make_ascii_svg.py
Converts a prepped photo into a high-fidelity animated ASCII art SVG portrait.
Features multi-tone character rendering, sharp contrast equalization, and SMIL wipes.
"""

import os
import sys
import argparse
import html
from PIL import Image, ImageEnhance, ImageOps
import numpy as np

# Ultra-fine 15-level character density ramp for dark theme background (#0d1117)
ASCII_RAMP = ["█", "▓", "▒", "░", "@", "#", "$", "%", "*", "+", "=", ":", "-", ".", " "]


def get_char_color(char: str) -> str:
    """Returns multi-tone color matching character density for high-contrast depth."""
    if char in ["█", "▓", "▒"]:
        return "#a5d6ff"  # Brightest highlight
    elif char in ["░", "@", "#"]:
        return "#79c0ff"  # Primary blue highlight
    elif char in ["$", "%", "*"]:
        return "#58a6ff"  # Mid cyan
    elif char in ["+", "=", ":"]:
        return "#8b949e"  # Slate gray
    elif char in ["-", "."]:
        return "#484f58"  # Dim gray
    return "#30363d"


def image_to_ascii(image_path: str, width: int = 115, invert: bool = False) -> list:
    """Downsamples image and maps pixels to ASCII characters with contrast enhancement."""
    if not os.path.exists(image_path):
        print(f"Warning: Image '{image_path}' not found. Generating sample avatar pattern.")
        return generate_sample_ascii(width, int(width * 0.52))

    img = Image.open(image_path).convert("L")

    # Histogram equalization for maximum facial detail expression
    img = ImageOps.equalize(img)

    # Boost contrast and sharpness
    img = ImageEnhance.Contrast(img).enhance(1.6)
    img = ImageEnhance.Sharpness(img).enhance(1.8)

    # Monospace aspect ratio correction (~1:0.50 ratio)
    aspect_ratio = img.height / img.width
    height = int(width * aspect_ratio * 0.50)

    img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
    np_img = np.array(img_resized)

    if invert:
        np_img = 255 - np_img

    num_levels = len(ASCII_RAMP)
    indices = (np_img.astype(float) / 255.0 * (num_levels - 1)).clip(0, num_levels - 1).astype(int)

    lines = []
    for row in indices:
        line = [ASCII_RAMP[val] for val in row]
        lines.append(line)
    return lines


def generate_sample_ascii(width: int = 100, height: int = 50) -> list:
    lines = []
    center_x, center_y = width / 2, height / 2
    for y in range(height):
        row = []
        for x in range(width):
            dx = (x - center_x) / (width / 2.5)
            dy = (y - center_y) / (height / 2.5)
            dist = (dx*dx + dy*dy) ** 0.5
            if dist < 0.3:
                char = "█"
            elif dist < 0.6:
                char = "@"
            elif dist < 0.8:
                char = "*"
            elif dist < 1.0:
                char = ":"
            else:
                char = " "
            row.append(char)
        lines.append(row)
    return lines


def render_ascii_svg(lines: list, output_path: str, font_size: float = 5.5, line_height: float = 7.0,
                     char_width: float = 3.2, duration_per_line: float = 0.04):
    """Renders ASCII lines into a multi-toned animated SMIL SVG file."""
    num_rows = len(lines)
    max_cols = max(len(line) for line in lines) if lines else 100

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

    print(f"Successfully generated ultra-high-fidelity ASCII SVG at '{output_path}' ({svg_width}x{svg_height}px).")


def main():
    parser = argparse.ArgumentParser(description="Convert prepped photo to high-fidelity animated ASCII SVG")
    parser.add_argument("--input", "-i", default="assets/source-prepped.png", help="Path to prepped photo")
    parser.add_argument("--output", "-o", default="avi-ascii.svg", help="Path to output SVG")
    parser.add_argument("--width", "-w", type=int, default=115, help="Character grid width (~100-120)")
    parser.add_argument("--invert", action="store_true", help="Invert brightness mapping")

    args = parser.parse_args()

    lines = image_to_ascii(args.input, width=args.width, invert=args.invert)
    render_ascii_svg(lines, args.output)


if __name__ == "__main__":
    main()
