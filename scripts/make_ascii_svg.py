#!/usr/bin/env python3
"""
make_ascii_svg.py
Converts a prepped photo into a crisp, highly recognizable line-art ASCII portrait SVG.
Uses edge detection + adaptive thresholding to render facial features (eyes, glasses, lips, hair)
clearly without solid block blobs.
"""

import os
import sys
import argparse
import html
import cv2
import numpy as np
from PIL import Image


def get_char_color(char: str) -> str:
    """Returns vibrant multi-tone colors matching character intensity."""
    if char in ["@", "#", "W", "M", "8"]:
        return "#79c0ff"  # Bright cyan highlight
    elif char in ["%", "&", "S", "*"]:
        return "#58a6ff"  # Primary blue
    elif char in ["+", "=", "o"]:
        return "#a5d6ff"  # Ice blue
    elif char in [":", ";"]:
        return "#8b949e"  # Slate gray
    elif char in ["-", "."]:
        return "#484f58"  # Dim gray
    return "#30363d"


def image_to_ascii(image_path: str, width: int = 105, invert: bool = False) -> list:
    """Converts image to clean line-art ASCII portrait using edge-aware adaptive filtering."""
    if not os.path.exists(image_path):
        print(f"Warning: Image '{image_path}' not found. Generating sample avatar pattern.")
        return generate_sample_ascii(width, int(width * 0.52))

    # Read image using OpenCV
    cv_img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if cv_img is None:
        pil_img = Image.open(image_path).convert("L")
        cv_img = np.array(pil_img)

    # 1. Bilateral filter to smooth noise while preserving sharp facial edges
    filtered = cv2.bilateralFilter(cv_img, d=7, sigmaColor=50, sigmaSpace=50)

    # 2. Canny edge detection for facial contours (eyes, glasses, lips, hair outline)
    edges = cv2.Canny(filtered, 50, 150)

    # 3. Adaptive thresholding for subtle shading
    thresh = cv2.adaptiveThreshold(
        filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )

    # Combine edges + adaptive shading
    combined = cv2.addWeighted(edges, 0.6, thresh, 0.4, 0)

    # 4. Aspect ratio scaling for monospace characters (~1 : 0.50 ratio)
    h_orig, w_orig = cv_img.shape
    aspect_ratio = h_orig / w_orig
    height = int(width * aspect_ratio * 0.50)

    resized_combined = cv2.resize(combined, (width, height), interpolation=cv2.INTER_AREA)
    resized_orig = cv2.resize(cv_img, (width, height), interpolation=cv2.INTER_AREA)

    # Character density ramp from light/edge to dark
    ramp = [" ", ".", "-", ":", "=", "+", "*", "%", "#", "@", "W"]

    lines = []
    for y in range(height):
        row = []
        for x in range(width):
            val_comb = resized_combined[y, x]
            val_raw = resized_orig[y, x]

            # Background check: if raw pixel is near pure white (> 245), output space
            if val_raw > 245:
                char = " "
            elif val_comb > 128:
                # Strong edge or feature contour
                edge_intensity = val_comb / 255.0
                idx = int(edge_intensity * (len(ramp) - 1))
                char = ramp[min(idx, len(ramp) - 1)]
            elif val_raw < 100:
                # Dark feature area (hair / dark shadow)
                dark_intensity = (100 - val_raw) / 100.0
                if dark_intensity > 0.6:
                    char = "#"
                elif dark_intensity > 0.3:
                    char = "*"
                else:
                    char = ":"
            else:
                char = " "
            row.append(char)
        lines.append(row)
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

    print(f"Successfully generated line-art ASCII SVG at '{output_path}' ({svg_width}x{svg_height}px).")


def main():
    parser = argparse.ArgumentParser(description="Convert prepped photo to line-art animated ASCII SVG")
    parser.add_argument("--input", "-i", default="assets/source-prepped.png", help="Path to prepped photo")
    parser.add_argument("--output", "-o", default="avi-ascii.svg", help="Path to output SVG")
    parser.add_argument("--width", "-w", type=int, default=105, help="Character grid width (~95-110)")
    parser.add_argument("--invert", action="store_true", help="Invert brightness mapping")

    args = parser.parse_args()

    lines = image_to_ascii(args.input, width=args.width, invert=args.invert)
    render_ascii_svg(lines, args.output)


if __name__ == "__main__":
    main()
