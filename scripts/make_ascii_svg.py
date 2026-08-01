#!/usr/bin/env python3
"""
===============================================================================
  DIRECT & CENTERED HIGH-FIDELITY ASCII PORTRAIT GENERATOR (PRODUCTION ENGINE)
===============================================================================
Description:
    Converts an input photograph directly into a centered, photorealistic animated
    ASCII SVG vector card for GitHub profile READMEs.

Key Features:
    1. Direct Input Processing (directly from input photo)
    2. Automatic Foreground Subject Detection & Perfect Horizontal/Vertical Centering
    3. CLAHE Local Contrast Equalization + Bilateral Edge Preservation + Unsharp Masking
    4. 70-Level High-Density Character Ramp Mapping
    5. Multi-Tone GitHub Dark Theme Palette
    6. Monospaced SMIL Left-to-Right Animated SVG Vector Card

Usage:
    python scripts/make_ascii_svg.py --input assets/input_photo.png --output avi-ascii.svg --width 130
===============================================================================
"""

import os
import sys
import argparse
import html
import cv2
import numpy as np
from PIL import Image, ImageFilter

# High-density 70-level character ramp from dark/dense to light/sparse
DENSITY_RAMP = list(
    "$@B%8&WM#*oahkbdpqwm"
    "ZO0QLCJUYXzcvuxrjft/\\|()1{}[]?-_+~<>i!"
    "lI;:,\"^`'. "
)
NUM_DENSITY_LEVELS = len(DENSITY_RAMP) - 1


def load_and_center_subject(image_path: str, bg_thresh: int = 225) -> tuple:
    """
    Loads input photo directly, isolates the subject, crops tight to the subject bounding box,
    and centers the subject on a padded canvas for PERFECT horizontal & vertical alignment.
    """
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

    # Find subject bounding box
    y_indices, x_indices = np.where(fg_mask)
    if len(y_indices) == 0 or len(x_indices) == 0:
        return gray, fg_mask

    min_y, max_y = np.min(y_indices), np.max(y_indices)
    min_x, max_x = np.min(x_indices), np.max(x_indices)

    cropped_gray = gray[min_y:max_y, min_x:max_x]
    cropped_mask = fg_mask[min_y:max_y, min_x:max_x]

    # Create padded square canvas to center subject perfectly
    h_crop, w_crop = cropped_gray.shape
    max_dim = max(h_crop, w_crop)

    centered_gray = np.ones((max_dim, max_dim), dtype=np.uint8) * 255
    centered_mask = np.zeros((max_dim, max_dim), dtype=bool)

    start_y = (max_dim - h_crop) // 2
    start_x = (max_dim - w_crop) // 2

    centered_gray[start_y:start_y + h_crop, start_x:start_x + w_crop] = cropped_gray
    centered_mask[start_y:start_y + h_crop, start_x:start_x + w_crop] = cropped_mask

    return centered_gray, centered_mask


def apply_enhancement_pipeline(gray: np.ndarray) -> np.ndarray:
    """Applies CLAHE adaptive contrast, Bilateral filtering, and Unsharp Masking."""
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    equalized = clahe.apply(gray)

    bilateral = cv2.bilateralFilter(equalized, d=7, sigmaColor=50, sigmaSpace=50)

    pil_img = Image.fromarray(bilateral)
    pil_unsharp = pil_img.filter(ImageFilter.UnsharpMask(radius=2, percent=200, threshold=2))
    return np.array(pil_unsharp)


def resize_centered_subject(img: np.ndarray, mask: np.ndarray, width: int = 130) -> tuple:
    """Resizes centered subject using Lanczos interpolation with aspect ratio adjustment (~1 : 0.52)."""
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
    """Generates centered ASCII portrait directly from input photo."""
    print(f"[1/4] Loading '{image_path}' and isolating/centering subject...")
    centered_gray, centered_mask = load_and_center_subject(image_path)

    print("[2/4] Applying CLAHE adaptive contrast, Bilateral filtering & Unsharp masking...")
    enhanced_gray = apply_enhancement_pipeline(centered_gray)

    # Composite subject onto white canvas
    composite = np.ones_like(enhanced_gray) * 255
    composite[centered_mask] = enhanced_gray[centered_mask]

    print(f"[3/4] Resizing centered subject to {width} columns...")
    img_resized, mask_resized, grid_w, grid_h = resize_centered_subject(composite, centered_mask, width=width)

    print("[4/4] Mapping pixels to 70-level high-density ASCII ramp...")
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

    print(f"Successfully generated Centered Direct ASCII SVG: '{output_path}' ({svg_width}x{svg_height}px)")


def main():
    parser = argparse.ArgumentParser(description="Direct & Centered ASCII Portrait Generator")
    parser.add_argument("--input", "-i", default="assets/input_photo.png", help="Path to direct input photo")
    parser.add_argument("--output", "-o", default="avi-ascii.svg", help="Path to output SVG card")
    parser.add_argument("--width", "-w", type=int, default=130, help="Character grid width (default: 130)")

    args = parser.parse_args()

    render_ascii_portrait(args.input, args.output, width=args.width)


if __name__ == "__main__":
    main()
