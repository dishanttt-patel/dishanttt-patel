#!/usr/bin/env python3
"""
make_ascii_svg.py
Photorealistic ASCII Portrait Generator using Floyd-Steinberg Error Diffusion Dithering
combined with Canny Structural Edge Overlay.

This technique guarantees:
1. 100% sharp, defined glasses frames, eyes, pupils, mustache, and facial outlines via Canny edge detection.
2. Smooth, photorealistic stippling and tonal skin gradients via Floyd-Steinberg error diffusion dithering.
"""

import os
import sys
import argparse
import html
import cv2
import numpy as np
from PIL import Image

# Multi-level character density ramp for Floyd-Steinberg dithering
ASCII_RAMP = ["@", "#", "$", "%", "&", "*", "+", "=", ":", ".", " "]


def get_char_color(char: str) -> str:
    """Multi-tone terminal color palette matching character density."""
    mapping = {
        "@": "#ffffff",  # Bright white for sharp edges, glasses frames, pupils
        "#": "#ffffff",  # Bright white for dark hair / shirt
        "$": "#79c0ff",  # Bright cyan for beard / mustache
        "%": "#79c0ff",  # Bright cyan for facial contours
        "&": "#58a6ff",  # Primary blue for shadows
        "*": "#388bfd",  # Vibrant blue for mid shadows
        "+": "#58a6ff",  # Mid blue
        "=": "#a5d6ff",  # Ice blue for soft skin
        ":": "#8b949e",  # Slate gray for light skin
        ".": "#484f58",  # Dim gray for highlights
        " ": "#30363d",  # Canvas background space
    }
    return mapping.get(char, "#30363d")


def image_to_dithered_ascii(image_path: str, width: int = 95) -> list:
    """Converts source-prepped.png into a hybrid Floyd-Steinberg dithered ASCII grid with Canny edge overlay."""
    if not os.path.exists(image_path):
        print(f"Warning: Image '{image_path}' not found. Generating sample pattern.")
        return generate_sample_ascii(width, int(width * 0.52))

    # Read image as Grayscale
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        pil_img = Image.open(image_path).convert("L")
        img = np.array(pil_img)

    # Monospaced aspect ratio downsampling (~1 : 0.52)
    aspect_ratio = img.shape[0] / img.shape[1]
    height = int(width * aspect_ratio * 0.52)

    resized = cv2.resize(img, (width, height), interpolation=cv2.INTER_LANCZOS4)

    # Canny Edge Detection for structural features (glasses, eyes, pupils, mustache, outline)
    edges = cv2.Canny(resized, 40, 130)

    # Floyd-Steinberg Error Diffusion Dithering
    dither_arr = resized.astype(float)
    num_levels = len(ASCII_RAMP) - 1

    ascii_grid = []
    for y in range(height):
        row = []
        for x in range(width):
            # If Canny edge detected on subject, force sharp structural character (@)
            if edges[y, x] > 0 and resized[y, x] < 220:
                row.append("@")
            else:
                old_val = dither_arr[y, x]
                idx = min(max(int(round((old_val / 255.0) * num_levels)), 0), num_levels)
                new_val = (idx / float(num_levels)) * 255.0
                char = ASCII_RAMP[idx]
                row.append(char)

                # Distribute quantization error to neighboring pixels
                err = old_val - new_val
                if x + 1 < width:
                    dither_arr[y, x + 1] += err * (7.0 / 16.0)
                if y + 1 < height:
                    if x - 1 >= 0:
                        dither_arr[y + 1, x - 1] += err * (3.0 / 16.0)
                    dither_arr[y + 1, x] += err * (5.0 / 16.0)
                    if x + 1 < width:
                        dither_arr[y + 1, x + 1] += err * (1.0 / 16.0)
        ascii_grid.append(row)

    return ascii_grid


def generate_sample_ascii(width: int = 95, height: int = 50) -> list:
    lines = []
    for y in range(height):
        row = [" " for _ in range(width)]
        lines.append(row)
    return lines


def render_ascii_svg(lines: list, output_path: str, font_size: float = 5.0, line_height: float = 6.4,
                     duration_per_line: float = 0.035):
    """Renders ASCII lines into an animated SMIL SVG card."""
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

    print(f"Successfully generated Floyd-Steinberg + Canny Dithered ASCII SVG at '{output_path}' ({svg_width}x{svg_height}px).")


def main():
    parser = argparse.ArgumentParser(description="Convert prepped photo to Floyd-Steinberg Dithered animated ASCII SVG")
    parser.add_argument("--input", "-i", default="assets/source-prepped.png", help="Path to prepped photo")
    parser.add_argument("--output", "-o", default="avi-ascii.svg", help="Path to output SVG")
    parser.add_argument("--width", "-w", type=int, default=95, help="Character grid width (~95)")

    args = parser.parse_args()

    lines = image_to_dithered_ascii(args.input, width=args.width)
    render_ascii_svg(lines, args.output)


if __name__ == "__main__":
    main()
