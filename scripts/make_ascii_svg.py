#!/usr/bin/env python3
"""
make_ascii_svg.py
Converts prepped photo into a crisp, photorealistic ASCII portrait SVG using Atkinson Dithering.
"""

import os
import sys
import argparse
import html
import cv2
import numpy as np
from PIL import Image

RAMP = ['@', '#', '$', '%', '&', '*', '+', '=', ':', '.', ' ']

def get_char_color(char: str) -> str:
    mapping = {
        "@": "#ffffff",  # Bright white for dark features / hair
        "#": "#ffffff",  # Bright white
        "$": "#79c0ff",  # Bright cyan
        "%": "#79c0ff",  # Bright cyan
        "&": "#58a6ff",  # Primary blue
        "*": "#388bfd",  # Vibrant blue
        "+": "#58a6ff",  # Mid blue
        "=": "#a5d6ff",  # Ice blue
        ":": "#8b949e",  # Slate gray
        ".": "#484f58",  # Dim gray
        " ": "#30363d",  # Canvas space
    }
    return mapping.get(char, "#30363d")


def image_to_atkinson_ascii(image_path: str, width: int = 90) -> list:
    """Atkinson Dithering technique for photorealistic stippling."""
    if not os.path.exists(image_path):
        print(f"Warning: Image '{image_path}' not found.")
        return [[" " for _ in range(width)] for _ in range(45)]

    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        pil_img = Image.open(image_path).convert("L")
        img = np.array(pil_img)

    aspect_ratio = img.shape[0] / img.shape[1]
    height = int(width * aspect_ratio * 0.52)

    resized = cv2.resize(img, (width, height), interpolation=cv2.INTER_LANCZOS4)
    dither_arr = resized.astype(float)
    num_levels = len(RAMP) - 1

    lines = []
    for y in range(height):
        row = []
        for x in range(width):
            old_val = dither_arr[y, x]
            idx = min(max(int(round((old_val / 255.0) * num_levels)), 0), num_levels)
            new_val = (idx / float(num_levels)) * 255.0
            row.append(RAMP[idx])
            
            err = (old_val - new_val) / 8.0
            if x + 1 < width: dither_arr[y, x + 1] += err
            if x + 2 < width: dither_arr[y, x + 2] += err
            if y + 1 < height:
                if x - 1 >= 0: dither_arr[y + 1, x - 1] += err
                dither_arr[y + 1, x] += err
                if x + 1 < width: dither_arr[y + 1, x + 1] += err
            if y + 2 < height:
                dither_arr[y + 2, x] += err
        lines.append(row)
    return lines


def render_ascii_svg(lines: list, output_path: str, font_size: float = 5.0, line_height: float = 6.4,
                     duration_per_line: float = 0.035):
    num_rows = len(lines)
    svg_width = 370
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

    print(f"Successfully generated Atkinson Dithering ASCII SVG at '{output_path}' ({svg_width}x{svg_height}px).")


def main():
    parser = argparse.ArgumentParser(description="Convert prepped photo to Atkinson Dithered ASCII SVG")
    parser.add_argument("--input", "-i", default="assets/source-prepped.png", help="Path to prepped photo")
    parser.add_argument("--output", "-o", default="avi-ascii.svg", help="Path to output SVG")
    parser.add_argument("--width", "-w", type=int, default=90, help="Character grid width (~90)")

    args = parser.parse_args()

    lines = image_to_atkinson_ascii(args.input, width=args.width)
    render_ascii_svg(lines, args.output)


if __name__ == "__main__":
    main()
