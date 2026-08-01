#!/usr/bin/env python3
"""
===============================================================================
  HIGH-FIDELITY EDGE-ENHANCED ASCII PORTRAIT GENERATOR (PRODUCTION ENGINE)
===============================================================================
Description:
    Transforms prepped photos (assets/source-prepped.png) into photorealistic
    animated ASCII SVG vector cards for GitHub profile READMEs.

Key Features:
    1. Ingests Edge-Enhanced Prepped Photo
    2. 70-Level High-Density Character Ramp Mapping
    3. Multi-Tone GitHub Dark Theme Color Palette
    4. Monospaced SMIL Left-to-Right Animated SVG Vector Card

Usage:
    python scripts/make_ascii_svg.py --input assets/source-prepped.png --output avi-ascii.svg --width 130
===============================================================================
"""

import os
import sys
import argparse
import html
import cv2
import numpy as np
from PIL import Image

# High-density 70-level character ramp from dark/dense to light/sparse
DENSITY_RAMP = list(
    "$@B%8&WM#*oahkbdpqwm"
    "ZO0QLCJUYXzcvuxrjft/\\|()1{}[]?-_+~<>i!"
    "lI;:,\"^`'. "
)
NUM_DENSITY_LEVELS = len(DENSITY_RAMP) - 1


def load_prepped_image(image_path: str, bg_thresh: int = 242) -> tuple:
    """Loads prepped image and extracts foreground subject mask."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Input file '{image_path}' not found.")

    img_bgr = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img_bgr is None:
        pil_img = Image.open(image_path)
        img_bgr = np.array(pil_img)

    if len(img_bgr.shape) == 3 and img_bgr.shape[2] == 4:
        alpha = img_bgr[:, :, 3]
        gray = cv2.cvtColor(img_bgr[:, :, :3], cv2.COLOR_BGR2GRAY)
        fg_mask = alpha > 30
    elif len(img_bgr.shape) == 3:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        fg_mask = gray < bg_thresh
    else:
        gray = img_bgr.copy()
        fg_mask = gray < bg_thresh

    return gray, fg_mask


def resize_subject(img: np.ndarray, mask: np.ndarray, width: int = 130) -> tuple:
    """Resizes image using Lanczos interpolation with monospaced aspect ratio adjustment (~1 : 0.52)."""
    h_orig, w_orig = img.shape[:2]
    aspect_ratio = h_orig / float(w_orig)
    height = int(width * aspect_ratio * 0.52)

    pil_img = Image.fromarray(img)
    pil_resized = pil_img.resize((width, height), Image.Resampling.LANCZOS)
    img_resized = np.array(pil_resized)

    pil_mask = Image.fromarray(mask.astype(np.uint8) * 255)
    pil_mask_resized = pil_mask.resize((width, height), Image.Resampling.NEAREST)
    mask_resized = np.array(pil_mask_resized) > 128

    return img_resized, mask_resized, width, height


def get_github_dark_color(px: float) -> str:
    """Maps pixel luminance to multi-tone GitHub Dark theme color palette."""
    if px < 40:
        return "#ffffff"  # Bright white for glasses, pupils, dark hair & shirt
    elif px < 80:
        return "#79c0ff"  # Bright cyan for mustache, beard & facial contours
    elif px < 130:
        return "#58a6ff"  # Primary blue for mid-tone skin shading
    elif px < 180:
        return "#8ab4f8"  # Ice blue for light skin tones
    return "#8b949e"     # Slate gray for highlights & teeth


def render_ascii_portrait(image_path: str, output_path: str, width: int = 130):
    """Generates ASCII portrait from edge-enhanced prepped photo."""
    print(f"[1/3] Loading prepped photo from '{image_path}'...")
    gray, fg_mask = load_prepped_image(image_path)

    print(f"[2/3] Resizing to {width} columns via Lanczos interpolation...")
    img_resized, mask_resized, grid_w, grid_h = resize_subject(gray, fg_mask, width=width)

    print("[3/3] Mapping pixels to 70-level high-density ASCII ramp...")
    ascii_grid = []
    color_grid = []

    for y in range(grid_h):
        ascii_row = []
        color_row = []
        for x in range(grid_w):
            px_val = img_resized[y, x]
            is_fg = mask_resized[y, x]

            if not is_fg or px_val >= 242:
                ascii_row.append(" ")
                color_row.append("#30363d")
            else:
                idx = min(int((px_val / 241.0) * NUM_DENSITY_LEVELS), NUM_DENSITY_LEVELS)
                ascii_row.append(DENSITY_RAMP[idx])
                color_row.append(get_github_dark_color(px_val))

        ascii_grid.append(ascii_row)
        color_grid.append(color_row)

    generate_animated_svg(ascii_grid, color_grid, output_path, font_size=4.0, line_height=5.2)


def generate_animated_svg(ascii_grid: list, color_grid: list, output_path: str,
                           font_size: float = 4.0, line_height: float = 5.2):
    """Renders monospaced SVG card with SMIL left-to-right reveal animation."""
    num_rows = len(ascii_grid)
    svg_width = 370  # Standard GitHub README card width
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
        svg_lines.append(f'      <rect x="8" y="{row_y:.1f}" width="0" height="{svg_width - 16}">')
        svg_lines.append(f'        <animate attributeName="width" from="0" to="{svg_width - 16}" begin="{delay}s" dur="{anim_dur}s" fill="freeze" calcMode="spline" keySplines="0.4 0 0.2 1" />')
        svg_lines.append('      </rect>')
        svg_lines.append('    </clipPath>')

    svg_lines.append('  </defs>')
    svg_lines.append('  <g class="ascii-text">')

    for i in range(num_rows):
        clip_id = f"clip-row-{i}"
        y_pos = start_y + (i * line_height)
        row_chars = ascii_grid[i]
        row_colors = color_grid[i]

        spans = []
        curr_color, curr_text = None, ""

        for char, color in zip(row_chars, row_colors):
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

    print(f"Successfully generated High-Fidelity ASCII SVG: '{output_path}' ({svg_width}x{svg_height}px)")


def main():
    parser = argparse.ArgumentParser(description="High-Fidelity ASCII Portrait Generator")
    parser.add_argument("--input", "-i", default="assets/source-prepped.png", help="Path to prepped photo")
    parser.add_argument("--output", "-o", default="avi-ascii.svg", help="Path to output SVG card")
    parser.add_argument("--width", "-w", type=int, default=130, help="Character grid width (default: 130)")

    args = parser.parse_args()

    render_ascii_portrait(args.input, args.output, width=args.width)


if __name__ == "__main__":
    main()
