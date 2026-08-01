#!/usr/bin/env python3
"""
tune_ascii.py
Generates 3 distinct high-quality ASCII portrait variants from source-prepped.png:
1. Sharp Outlines (avi-ascii-sharp.svg)
2. Soft Photorealistic Shading (avi-ascii-soft.svg)
3. High-Definition 120-col Grid (avi-ascii-hd.svg)
"""

import os
import sys
import html
import numpy as np
from PIL import Image, ImageEnhance, ImageOps

# SVG styling helper
def render_svg(lines: list, output_path: str, font_size: float = 5.5, line_height: float = 7.0):
    num_rows = len(lines)
    max_cols = max(len(line) for line in lines) if lines else 95
    svg_width = 370
    svg_height = max(500, int(num_rows * line_height) + 24)
    start_y = 18

    def get_color(char):
        if char in ["@", "#", "█", "▓"]:
            return "#ffffff"
        elif char in ["$", "%", "▒", "░"]:
            return "#a5d6ff"
        elif char in ["*", "+"]:
            return "#79c0ff"
        elif char in ["=", ":"]:
            return "#58a6ff"
        elif char in ["-", "."]:
            return "#484f58"
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
    print(f"Generated variant: '{output_path}'")


def make_sharp_variant(img_path: str, output_path: str):
    """Sharp Outlines Variant: Boosts contrast to define crisp facial edges."""
    img = Image.open(img_path).convert("L")
    img = ImageEnhance.Contrast(img).enhance(1.8)
    img = ImageEnhance.Sharpness(img).enhance(2.0)

    w = 95
    h = int(w * (img.height / img.width) * 0.52)
    resized = img.resize((w, h), Image.Resampling.LANCZOS)
    arr = np.array(resized)

    ramp = [" ", ".", "-", ":", "=", "+", "*", "%", "$", "#", "@"]
    lines = []
    for row in arr:
        lines.append([" " if px >= 245 else ramp[min(int((px / 244.0) * 10), 10)] for px in row])
    render_svg(lines, output_path, font_size=5.5, line_height=7.0)


def make_soft_variant(img_path: str, output_path: str):
    """Soft Photorealistic Variant: Uses 15-level smooth shading ramp."""
    img = Image.open(img_path).convert("L")
    img = ImageOps.equalize(img)

    w = 95
    h = int(w * (img.height / img.width) * 0.52)
    resized = img.resize((w, h), Image.Resampling.LANCZOS)
    arr = np.array(resized)

    ramp = [" ", ".", "`", "'", "-", ":", ";", "=", "+", "*", "%", "&", "$", "#", "@"]
    lines = []
    for row in arr:
        lines.append([" " if px >= 245 else ramp[min(int((px / 244.0) * 14), 14)] for px in row])
    render_svg(lines, output_path, font_size=5.5, line_height=7.0)


def make_hd_variant(img_path: str, output_path: str):
    """High-Definition 120-Col Grid Variant: Maximum spatial facial detail."""
    img = Image.open(img_path).convert("L")
    img = ImageEnhance.Contrast(img).enhance(1.5)

    w = 120
    h = int(w * (img.height / img.width) * 0.50)
    resized = img.resize((w, h), Image.Resampling.LANCZOS)
    arr = np.array(resized)

    ramp = [" ", ".", "-", ":", "=", "+", "*", "%", "$", "#", "@"]
    lines = []
    for row in arr:
        lines.append([" " if px >= 245 else ramp[min(int((px / 244.0) * 10), 10)] for px in row])
    render_svg(lines, output_path, font_size=4.5, line_height=6.0)


def main():
    img_path = "assets/source-prepped.png"
    if not os.path.exists(img_path):
        print(f"Error: {img_path} not found.")
        sys.exit(1)

    make_sharp_variant(img_path, "avi-ascii-sharp.svg")
    make_soft_variant(img_path, "avi-ascii-soft.svg")
    make_hd_variant(img_path, "avi-ascii-hd.svg")

    # Set default avi-ascii.svg to HD variant
    make_hd_variant(img_path, "avi-ascii.svg")


if __name__ == "__main__":
    main()
