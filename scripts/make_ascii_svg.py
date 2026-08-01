#!/usr/bin/env python3
"""
make_ascii_svg.py
Converts prepped photo into a crisp, 100% accurate animated ASCII portrait SVG.
Maps ONLY the dark feature pixels (<200) from source-prepped.png into ASCII characters,
while keeping white background pixels (>=200) as blank space so the SVG background (#0d1117) shows through.
"""

import os
import sys
import argparse
import html
import numpy as np
from PIL import Image

# Density ramp for dark feature pixels (darkest to lightest feature)
ASCII_RAMP = ["@", "#", "$", "%", "*", "+", "=", ":", "-", "."]


def get_char_color(char: str) -> str:
    """Returns vibrant multi-tone colors matching character density."""
    if char in ["@", "#"]:
        return "#79c0ff"  # Bright cyan highlight
    elif char in ["$", "%"]:
        return "#58a6ff"  # Primary blue
    elif char in ["*", "+"]:
        return "#a5d6ff"  # Ice blue
    elif char in ["=", ":"]:
        return "#8b949e"  # Slate gray
    elif char in ["-", "."]:
        return "#484f58"  # Dim gray
    return "#30363d"


def image_to_ascii(image_path: str, width: int = 85) -> list:
    """Converts prepped photo to clean ASCII portrait mapping dark pixels to characters."""
    if not os.path.exists(image_path):
        print(f"Warning: Image '{image_path}' not found. Generating sample avatar pattern.")
        return generate_sample_ascii(width, int(width * 0.52))

    img = Image.open(image_path).convert("L")

    # Monospace aspect ratio correction (~1 : 0.52 ratio)
    aspect_ratio = img.height / img.width
    height = int(width * aspect_ratio * 0.52)

    img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
    np_img = np.array(img_resized)

    lines = []
    num_ramp = len(ASCII_RAMP)

    for y in range(height):
        row = []
        for x in range(width):
            px = np_img[y, x]
            # White background pixels (>= 200) -> blank space ' '
            if px >= 200:
                char = " "
            else:
                # Map dark feature pixels (0..199) to characters
                idx = min(int((px / 200.0) * num_ramp), num_ramp - 1)
                char = ASCII_RAMP[idx]
            row.append(char)
        lines.append(row)
    return lines


def generate_sample_ascii(width: int = 85, height: int = 44) -> list:
    lines = []
    center_x, center_y = width / 2, height / 2
    for y in range(height):
        row = []
        for x in range(width):
            dx = (x - center_x) / (width / 2.5)
            dy = (y - center_y) / (height / 2.5)
            dist = (dx*dx + dy*dy) ** 0.5
            if dist < 0.3:
                char = "@"
            elif dist < 0.6:
                char = "#"
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
                     duration_per_line: float = 0.04):
    """Renders ASCII lines into a multi-toned animated SMIL SVG file."""
    num_rows = len(lines)
    max_cols = max(len(line) for line in lines) if lines else 85

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

    print(f"Successfully generated dark-feature ASCII SVG at '{output_path}' ({svg_width}x{svg_height}px).")


def main():
    parser = argparse.ArgumentParser(description="Convert prepped photo to dark-feature animated ASCII SVG")
    parser.add_argument("--input", "-i", default="assets/source-prepped.png", help="Path to prepped photo")
    parser.add_argument("--output", "-o", default="avi-ascii.svg", help="Path to output SVG")
    parser.add_argument("--width", "-w", type=int, default=85, help="Character grid width (~80-90)")

    args = parser.parse_args()

    lines = image_to_ascii(args.input, width=args.width)
    render_ascii_svg(lines, args.output)


if __name__ == "__main__":
    main()
