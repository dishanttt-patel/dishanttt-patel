#!/usr/bin/env python3
"""
make_ascii_svg.py
Converts prepped photo (assets/source-prepped.png) into a crisp, 100% accurate ASCII SVG portrait.
Uses exact 1-to-1 color-to-character mapping:
Each distinct luminance/color bucket maps to ONE unique ASCII character and ONE unique color!
"""

import os
import sys
import argparse
import html
import numpy as np
from PIL import Image

# 1-to-1 Character Mapping Table for Gray Levels:
# px >= 240 -> ' ' (Blank background)
# px < 35   -> '@' (Darkest hair / glasses frames / pupils)
# px < 70   -> '%' (Beard / mustache / dark contours)
# px < 105  -> '#' (Facial shadow contours / clothing)
# px < 140  -> '*' (Mid shadows / jawline shading)
# px < 175  -> '=' (Soft skin tone transitions)
# px < 210  -> ':' (Light skin tone / forehead)
# px < 240  -> '.' (Bright highlights / teeth / eye whites)


def map_pixel_to_char(px: int) -> str:
    if px >= 240:
        return " "
    elif px < 35:
        return "@"
    elif px < 70:
        return "%"
    elif px < 105:
        return "#"
    elif px < 140:
        return "*"
    elif px < 175:
        return "="
    elif px < 210:
        return ":"
    else:
        return "."


def get_char_color(char: str) -> str:
    """1-to-1 Color mapping for each unique character."""
    mapping = {
        "@": "#ffffff",  # Bright white for hair/glasses
        "%": "#79c0ff",  # Bright cyan for beard/mustache
        "#": "#58a6ff",  # Primary blue for shadows
        "*": "#388bfd",  # Vibrant blue for mid shadows
        "=": "#a5d6ff",  # Ice blue for soft skin
        ":": "#8b949e",  # Slate gray for light skin
        ".": "#484f58",  # Dim gray for highlights
        " ": "#30363d",  # Blank space background
    }
    return mapping.get(char, "#30363d")


def image_to_ascii(image_path: str, width: int = 90) -> list:
    """Converts source-prepped.png into a 1-to-1 color-mapped ASCII portrait."""
    if not os.path.exists(image_path):
        print(f"Warning: Image '{image_path}' not found. Generating sample avatar pattern.")
        return generate_sample_ascii(width, int(width * 0.52))

    img = Image.open(image_path).convert("L")

    # Monospaced aspect ratio scaling (~1 : 0.52)
    aspect_ratio = img.height / img.width
    height = int(width * aspect_ratio * 0.52)

    img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
    np_img = np.array(img_resized)

    lines = []
    for y in range(height):
        row = [map_pixel_to_char(np_img[y, x]) for x in range(width)]
        lines.append(row)
    return lines


def generate_sample_ascii(width: int = 90, height: int = 48) -> list:
    lines = []
    for y in range(height):
        row = [" " for _ in range(width)]
        lines.append(row)
    return lines


def render_ascii_svg(lines: list, output_path: str, font_size: float = 5.2, line_height: float = 6.6,
                     duration_per_line: float = 0.035):
    """Renders ASCII lines into a 1-to-1 color-mapped animated SMIL SVG file."""
    num_rows = len(lines)
    svg_width = 370  # Standard container width
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

    print(f"Successfully generated 1-to-1 color-mapped ASCII SVG at '{output_path}' ({svg_width}x{svg_height}px).")


def main():
    parser = argparse.ArgumentParser(description="Convert prepped photo to 1-to-1 color-mapped animated ASCII SVG")
    parser.add_argument("--input", "-i", default="assets/source-prepped.png", help="Path to prepped photo")
    parser.add_argument("--output", "-o", default="avi-ascii.svg", help="Path to output SVG")
    parser.add_argument("--width", "-w", type=int, default=90, help="Character grid width (~90)")

    args = parser.parse_args()

    lines = image_to_ascii(args.input, width=args.width)
    render_ascii_svg(lines, args.output)


if __name__ == "__main__":
    main()
