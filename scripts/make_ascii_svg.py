#!/usr/bin/env python3
"""
make_ascii_svg.py
High-Definition (HD) 130-Column ASCII Portrait SVG Generator.
Uses OpenCV CLAHE adaptive contrast + Bilateral edge-preserving filtering
with a 20-level precision character density ramp to produce a photorealistic,
hyper-accurate ASCII portrait matching the prepped image.
"""

import os
import sys
import argparse
import html
import cv2
import numpy as np
from PIL import Image

# 20-level precision density ramp
RAMP = ['@', '#', '$', '%', '8', '&', 'W', 'M', '0', 'Q', 'P', 'o', 'a', '+', '=', ':', '-', '.', '\'', ' ']


def get_char_color(char: str) -> str:
    """Multi-tone cyan/white color mapping for HD rendering."""
    if char in ["@", "#", "$", "%"]:
        return "#ffffff"  # Bright white for glasses frames, pupils, dark hair, shirt
    elif char in ["8", "&", "W", "M", "0"]:
        return "#79c0ff"  # Bright cyan for mustache, beard, facial contours
    elif char in ["Q", "P", "o", "a"]:
        return "#58a6ff"  # Primary blue for mid-tone skin shading
    elif char in ["+", "=", ":", "-", ".", "'"]:
        return "#8b949e"  # Slate gray for skin highlights
    return "#30363d"     # Background space


def image_to_hd_ascii(image_path: str, width: int = 130) -> list:
    """Converts source-prepped.png into a hyper-accurate 130-column HD ASCII grid."""
    if not os.path.exists(image_path):
        print(f"Warning: Image '{image_path}' not found. Generating sample avatar pattern.")
        return generate_sample_ascii(width, int(width * 0.52))

    # Read image as Grayscale
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        pil_img = Image.open(image_path).convert("L")
        img = np.array(pil_img)

    # Apply Bilateral edge preservation + CLAHE adaptive local contrast
    filt = cv2.bilateralFilter(img, d=7, sigmaColor=50, sigmaSpace=50)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(filt)

    # Monospaced aspect ratio downsampling (~1 : 0.52)
    pil_img = Image.fromarray(enhanced)
    aspect_ratio = pil_img.height / pil_img.width
    height = int(width * aspect_ratio * 0.52)

    img_resized = pil_img.resize((width, height), Image.Resampling.LANCZOS)
    np_img = np.array(img_resized)

    lines = []
    num_ramp = len(RAMP) - 1

    for y in range(height):
        row = []
        for x in range(width):
            px = np_img[y, x]
            if px >= 242:
                row.append(" ")
            else:
                idx = min(int((px / 241.0) * num_ramp), num_ramp)
                row.append(RAMP[idx])
        lines.append(row)

    return lines


def generate_sample_ascii(width: int = 130, height: int = 65) -> list:
    lines = []
    for y in range(height):
        row = [" " for _ in range(width)]
        lines.append(row)
    return lines


def render_ascii_svg(lines: list, output_path: str, font_size: float = 4.2, line_height: float = 5.4,
                     duration_per_line: float = 0.025):
    """Renders 130-column HD ASCII lines into an animated SMIL SVG card."""
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

    print(f"Successfully generated 130-column HD ASCII SVG at '{output_path}' ({svg_width}x{svg_height}px).")


def main():
    parser = argparse.ArgumentParser(description="Convert prepped photo to 130-column HD animated ASCII SVG")
    parser.add_argument("--input", "-i", default="assets/source-prepped.png", help="Path to prepped photo")
    parser.add_argument("--output", "-o", default="avi-ascii.svg", help="Path to output SVG")
    parser.add_argument("--width", "-w", type=int, default=130, help="Character grid width (~130)")

    args = parser.parse_args()

    lines = image_to_hd_ascii(args.input, width=args.width)
    render_ascii_svg(lines, args.output)


if __name__ == "__main__":
    main()
