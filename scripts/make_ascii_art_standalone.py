#!/usr/bin/env python3
"""
===============================================================================
       70-LEVEL ULTRA-HD PHOTOREALISTIC ASCII PORTRAIT GENERATOR
===============================================================================
Description:
    Converts a profile photo into an 8K-detail monospaced ASCII portrait SVG & TXT file.
    Uses a full 70-level density ramp, OpenCV Bilateral Edge-Preserving Filter,
    and CLAHE Adaptive Local Contrast to capture crisp glasses rims, detailed eyes with pupils,
    smiling teeth, mustache, beard, and smooth tonal skin gradients.

Character Ramp (70 Levels):
    $@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvuxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. 

Usage:
    python make_ascii_art_standalone.py --input assets/input_photo.png --output avi-ascii.svg --txt avi-ascii.txt --width 160
===============================================================================
"""

import os
import sys
import argparse
import html
import cv2
import numpy as np
from PIL import Image

# 70-level density ramp for photorealistic character rendering
ASCII_RAMP = list("$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvuxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. ")


def get_char_color(v_norm: float) -> str:
    """Returns multi-tone terminal colors based on luminance gradient (0.0 to 1.0)."""
    if v_norm < 0.15:
        return "#ffffff"  # White highlight for glasses, pupils, dark hair
    elif v_norm < 0.35:
        return "#79c0ff"  # Bright cyan
    elif v_norm < 0.60:
        return "#58a6ff"  # Primary blue mid-tones
    elif v_norm < 0.85:
        return "#8b949e"  # Slate gray skin highlights
    return "#484f58"     # Dim gray background grid


def image_to_ascii_grid(image_path: str, width: int = 160) -> tuple:
    """Converts image to clean 2D 70-level ASCII grid preserving identity & facial features."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Input image file '{image_path}' not found.")

    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        pil_img = Image.open(image_path).convert("L")
        img = np.array(pil_img)

    # Crop upper 72% for head & shoulders focus
    h_orig, w_orig = img.shape
    crop = img[0:int(h_orig * 0.72), 0:w_orig]

    # Bilateral edge-preserving filter + CLAHE local contrast enhancement
    filt = cv2.bilateralFilter(crop, d=9, sigmaColor=75, sigmaSpace=75)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(filt)

    pil_img = Image.fromarray(enhanced)
    aspect_ratio = pil_img.height / pil_img.width
    height = int(width * aspect_ratio * 0.52)

    img_resized = pil_img.resize((width, height), Image.Resampling.LANCZOS)
    np_img = np.array(img_resized)

    chars, vals = [], []
    num_ramp = len(ASCII_RAMP) - 1

    for y in range(height):
        c_row, v_row = [], []
        for x in range(width):
            px = np_img[y, x]
            norm_v = px / 255.0
            idx = min(int(norm_v * num_ramp), num_ramp)
            char = ASCII_RAMP[idx]
            c_row.append(char)
            v_row.append(norm_v)
        chars.append(c_row)
        vals.append(v_row)

    return chars, vals


def render_animated_svg(chars: list, vals: list, output_path: str, font_size: float = 3.2, line_height: float = 4.2):
    """Renders 2D ASCII character grid into an animated SMIL vector SVG card."""
    num_rows = len(chars)
    svg_width = 370
    svg_height = max(500, int(num_rows * line_height) + 24)
    start_y = 18
    duration_per_line = 0.025

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

    print(f"[+] Generated Animated SVG: '{output_path}' ({svg_width}x{svg_height}px)")


def save_plain_text(chars: list, txt_path: str):
    """Saves the ASCII grid to a plain text (.txt) file."""
    os.makedirs(os.path.dirname(txt_path) or ".", exist_ok=True)
    with open(txt_path, "w", encoding="utf-8") as f:
        for row in chars:
            f.write("".join(row) + "\n")
    print(f"[+] Saved Plain Text ASCII: '{txt_path}'")


def main():
    parser = argparse.ArgumentParser(description="70-Level Ultra-HD Photorealistic ASCII Portrait Generator")
    parser.add_argument("--input", "-i", default="assets/input_photo.png", help="Path to input photo")
    parser.add_argument("--output", "-o", default="avi-ascii.svg", help="Path to output SVG file")
    parser.add_argument("--txt", "-t", default=None, help="Optional path to save plain text ASCII (.txt)")
    parser.add_argument("--width", "-w", type=int, default=160, help="Grid width columns (default: 160)")

    args = parser.parse_args()

    chars, vals = image_to_ascii_grid(args.input, width=args.width)
    render_animated_svg(chars, vals, args.output)

    if args.txt:
        save_plain_text(chars, args.txt)


if __name__ == "__main__":
    main()
