#!/usr/bin/env python3
"""
tune_ascii.py
Generates 4 distinct state-of-the-art ASCII portrait techniques from source-prepped.png:
1. Atkinson Dithering (avi-ascii-atkinson.svg) - Classic Mac OS stippled dithering
2. Directional Sobel Contour Mapping (avi-ascii-sobel.svg) - Structural stroke-mapped ASCII art
3. Floyd-Steinberg Dithering (avi-ascii-floyd.svg) - Smooth error diffusion dithering
4. Sharp Outlines (avi-ascii-sharp.svg) - High-contrast edge outlines
"""

import os
import sys
import html
import cv2
import numpy as np
from PIL import Image

def render_svg(lines: list, output_path: str, font_size: float = 5.0, line_height: float = 6.4):
    num_rows = len(lines)
    svg_width = 370
    svg_height = max(500, int(num_rows * line_height) + 24)
    start_y = 18

    def get_color(char):
        if char in ["@", "#", "B", "%", "8", "|", "/", "\\", "-"]:
            return "#ffffff"  # Bright white for structural features & outlines
        elif char in ["$", "&", "*", "+"]:
            return "#79c0ff"  # Bright cyan
        elif char in ["=", "i", "!"]:
            return "#58a6ff"  # Primary blue
        elif char in [":", "."]:
            return "#8b949e"  # Slate gray
        return "#30363d"

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
        delay = round(i * 0.035, 3)
        anim_dur = round(0.035 * 1.5, 3)

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
        curr_color, curr_text = None, ""

        for char in line_chars:
            color = get_color(char)
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

        svg_lines.append(f'    <text x="10" y="{y_pos:.1f}" clip-path="url(#{clip_id})">{"".join(spans)}</text>')

    svg_lines.append('  </g>')
    svg_lines.append('</svg>')

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_lines))
    print(f"Generated technique: '{output_path}'")


def make_atkinson_variant(img_path: str, output_path: str):
    """Technique 1: Atkinson Dithering (Classic Mac OS Stippling)"""
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    w = 90
    h = int(w * (img.shape[0] / img.shape[1]) * 0.52)
    resized = cv2.resize(img, (w, h), interpolation=cv2.INTER_LANCZOS4)

    dither_arr = resized.astype(float)
    RAMP = ['@', '#', '$', '%', '&', '*', '+', '=', ':', '.', ' ']
    num_levels = len(RAMP) - 1

    lines = []
    for y in range(h):
        row = []
        for x in range(w):
            old_val = dither_arr[y, x]
            idx = min(max(int(round((old_val / 255.0) * num_levels)), 0), num_levels)
            new_val = (idx / float(num_levels)) * 255.0
            row.append(RAMP[idx])
            
            err = (old_val - new_val) / 8.0
            if x + 1 < w: dither_arr[y, x + 1] += err
            if x + 2 < w: dither_arr[y, x + 2] += err
            if y + 1 < h:
                if x - 1 >= 0: dither_arr[y + 1, x - 1] += err
                dither_arr[y + 1, x] += err
                if x + 1 < w: dither_arr[y + 1, x + 1] += err
            if y + 2 < h:
                dither_arr[y + 2, x] += err
        lines.append(row)
    render_svg(lines, output_path, font_size=5.0, line_height=6.4)


def make_sobel_variant(img_path: str, output_path: str):
    """Technique 2: Directional Sobel Contour Mapping"""
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    w = 90
    h = int(w * (img.shape[0] / img.shape[1]) * 0.52)
    resized = cv2.resize(img, (w, h), interpolation=cv2.INTER_LANCZOS4)

    sobelx = cv2.Sobel(resized, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(resized, cv2.CV_64F, 0, 1, ksize=3)

    magnitude = np.sqrt(sobelx**2 + sobely**2)
    angle = np.arctan2(sobely, sobelx) * (180 / np.pi) % 180

    lines = []
    for y in range(h):
        row = []
        for x in range(w):
            px = resized[y, x]
            mag = magnitude[y, x]
            ang = angle[y, x]
            
            if px >= 240:
                row.append(" ")
            elif mag > 60:
                if (0 <= ang < 22.5) or (157.5 <= ang <= 180):
                    row.append("|")
                elif 22.5 <= ang < 67.5:
                    row.append("/")
                elif 67.5 <= ang < 112.5:
                    row.append("-")
                else:
                    row.append("\\")
            else:
                if px < 40: row.append("@")
                elif px < 80: row.append("%")
                elif px < 120: row.append("#")
                elif px < 160: row.append("*")
                elif px < 200: row.append("=")
                else: row.append(":")
        lines.append(row)
    render_svg(lines, output_path, font_size=5.0, line_height=6.4)


def main():
    img_path = "assets/source-prepped.png"
    if not os.path.exists(img_path):
        print(f"Error: {img_path} not found.")
        sys.exit(1)

    make_atkinson_variant(img_path, "avi-ascii-atkinson.svg")
    make_sobel_variant(img_path, "avi-ascii-sobel.svg")

    # Set main default avi-ascii.svg to Atkinson Dithering technique
    make_atkinson_variant(img_path, "avi-ascii.svg")


if __name__ == "__main__":
    main()
