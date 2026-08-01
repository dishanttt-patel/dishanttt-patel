#!/usr/bin/env python3
"""
make_ascii_svg.py
High-resolution 70-level ASCII Art Portrait SVG Generator.
Preserves identity, facial proportions, expression, crisp round eyeglasses,
detailed eyes with pupils, nostrils, smiling teeth, and soft beard using adaptive character density.
"""

import os
import sys
import argparse
import html
import cv2
import numpy as np
from PIL import Image

# 70-Level Ultra-Fine Density Ramp
ASCII_RAMP = list("$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvuxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. ")


def get_char_color(v_norm: float) -> str:
    """
    Returns vibrant multi-tone color strings matching pixel luminance gradient (0.0 to 1.0).
    - Darkest features (glasses rims, pupils, hair, shirt): White (#ffffff) / Cyan (#79c0ff)
    - Mid-tones (beard, mustache, facial contours): Blue (#58a6ff) / Slate (#8b949e)
    - Background & light highlights: Slate (#8b949e) / Dim Gray (#484f58)
    """
    if v_norm < 0.15:
        return "#ffffff"  # Bright white for glasses rims, pupils, hair outlines
    elif v_norm < 0.35:
        return "#79c0ff"  # Bright cyan
    elif v_norm < 0.60:
        return "#58a6ff"  # Primary blue mid-tones
    elif v_norm < 0.85:
        return "#8b949e"  # Slate gray skin highlights
    return "#484f58"     # Dim gray outer background grid


def image_to_ascii(image_path: str, width: int = 160) -> tuple:
    """Converts input photo to clean, accurate 70-level high-resolution ASCII portrait."""
    if not os.path.exists(image_path):
        print(f"Warning: Image '{image_path}' not found. Generating sample avatar pattern.")
        return generate_sample_ascii(width, int(width * 0.52))

    # Read image in Grayscale
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        pil_img = Image.open(image_path).convert("L")
        img = np.array(pil_img)

    # Crop upper 72% for head & shoulders focus
    h_orig, w_orig = img.shape
    crop = img[0:int(h_orig * 0.72), 0:w_orig]

    # Bilateral filter for edge preservation (glasses/eyes/teeth) + CLAHE local contrast enhancement
    filt = cv2.bilateralFilter(crop, d=9, sigmaColor=75, sigmaSpace=75)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(filt)

    # Monospaced aspect ratio downsampling (~1 : 0.52)
    pil_img = Image.fromarray(enhanced)
    aspect_ratio = pil_img.height / pil_img.width
    height = int(width * aspect_ratio * 0.52)

    img_resized = pil_img.resize((width, height), Image.Resampling.LANCZOS)
    np_img = np.array(img_resized)

    chars = []
    vals = []
    num_ramp = len(ASCII_RAMP) - 1

    for y in range(height):
        row_chars = []
        row_vals = []
        for x in range(width):
            px = np_img[y, x]
            norm_val = px / 255.0
            idx = min(int(norm_val * num_ramp), num_ramp)
            char = ASCII_RAMP[idx]
            row_chars.append(char)
            row_vals.append(norm_val)
        chars.append(row_chars)
        vals.append(row_vals)

    return chars, vals


def generate_sample_ascii(width: int = 160, height: int = 80) -> tuple:
    chars, vals = [], []
    for y in range(height):
        c_row, v_row = [], []
        for x in range(width):
            c_row.append(".")
            v_row.append(0.9)
        chars.append(c_row)
        vals.append(v_row)
    return chars, vals


def render_ascii_svg(chars: list, vals: list, output_path: str, font_size: float = 3.2, line_height: float = 4.2,
                     duration_per_line: float = 0.025):
    """Renders ASCII lines into a multi-toned animated SMIL SVG file."""
    num_rows = len(chars)
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

    for i, row_chars in enumerate(chars):
        clip_id = f"clip-row-{i}"
        y_pos = start_y + (i * line_height)

        spans = []
        curr_color = None
        curr_text = ""

        for j, char in enumerate(row_chars):
            norm_v = vals[i][j]
            color = get_char_color(norm_v)
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

    print(f"Successfully generated 70-level ultra-HD ASCII SVG at '{output_path}' ({svg_width}x{svg_height}px).")


def main():
    parser = argparse.ArgumentParser(description="Convert photo to 70-level ultra-HD animated ASCII SVG")
    parser.add_argument("--input", "-i", default="assets/input_photo.png", help="Path to input photo")
    parser.add_argument("--output", "-o", default="avi-ascii.svg", help="Path to output SVG")
    parser.add_argument("--width", "-w", type=int, default=160, help="Character grid width (~160)")

    args = parser.parse_args()

    chars, vals = image_to_ascii(args.input, width=args.width)
    render_ascii_svg(chars, vals, args.output)


if __name__ == "__main__":
    main()
