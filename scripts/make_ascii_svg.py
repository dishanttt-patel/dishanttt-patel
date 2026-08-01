#!/usr/bin/env python3
"""
===============================================================================
     ADVANCED COMPUTER VISION ASCII PORTRAIT GENERATOR (PRODUCTION ENGINE)
===============================================================================
Description:
    A high-precision, edge-aware ASCII portrait renderer that transforms input photos
    into photorealistic animated SVG vector artwork for GitHub profile READMEs.

    Combines:
    1. CLAHE + Bilateral Filtering + Gamma Correction + Unsharp Masking
    2. Sobel Gradient Magnitude & Direction Analysis (Horizontal, Vertical, Diagonals, Curves, Corners)
    3. Floyd-Steinberg Error Diffusion Dithering
    4. 70+ Level High-Density ASCII Ramp with Edge-Aware Structure Matching
    5. Monospaced SMIL Animated SVG Output with GitHub Dark Theme Palette

Usage:
    python scripts/make_ascii_svg.py --input assets/source-prepped.png --output avi-ascii.svg --width 140
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

# Directional edge character sets
EDGE_CHARS_HORIZONTAL = ["-", "_", "=", "~"]
EDGE_CHARS_VERTICAL = ["|", "I", "l", "!"]
EDGE_CHARS_DIAG_UP = ["/"]
EDGE_CHARS_DIAG_DOWN = ["\\"]
EDGE_CHARS_CORNERS = ["+"]
EDGE_CHARS_CURVES = ["(", ")", "{", "}", "[", "]"]
HAIR_DARK_CHARS = ["M", "W", "B", "8", "#", "@", "$", "%"]
SKIN_SMOOTH_CHARS = [".", ",", ":", ";", "i", "'", "`"]


def detect_and_remove_background(img_bgr: np.ndarray, threshold: int = 240) -> tuple:
    """
    Step 1 & 2: Detects white/light background and converts image to grayscale + foreground mask.
    """
    if len(img_bgr.shape) == 3 and img_bgr.shape[2] == 4:
        # RGBA Image: Use Alpha channel as mask
        alpha = img_bgr[:, :, 3]
        gray = cv2.cvtColor(img_bgr[:, :, :3], cv2.COLOR_BGR2GRAY)
        fg_mask = alpha > 30
    elif len(img_bgr.shape) == 3:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        fg_mask = gray < threshold
    else:
        gray = img_bgr.copy()
        fg_mask = gray < threshold

    return gray, fg_mask


def apply_preprocessing_pipeline(gray: np.ndarray) -> np.ndarray:
    """
    Steps 4-7: Applies CLAHE, Bilateral filtering, Gamma Correction, and Unsharp Masking.
    """
    # Step 4: CLAHE Adaptive Histogram Equalization
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    equalized = clahe.apply(gray)

    # Step 5: Bilateral Filtering (Edge-preserving smoothing)
    bilateral = cv2.bilateralFilter(equalized, d=7, sigmaColor=50, sigmaSpace=50)

    # Step 6: Gamma Correction (gamma = 0.85 to enhance shadow details)
    gamma = 0.85
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    gamma_corrected = cv2.LUT(bilateral, table)

    # Step 7: Unsharp Masking (Enhances crisp facial features like eyes & glasses)
    pil_img = Image.fromarray(gamma_corrected)
    unsharp_pil = pil_img.filter(ImageFilter.UnsharpMask(radius=2, percent=200, threshold=2))
    return np.array(unsharp_pil)


def resize_image(img: np.ndarray, fg_mask: np.ndarray, width: int = 140) -> tuple:
    """
    Step 8: Resizes grayscale image and mask using Lanczos interpolation with aspect ratio adjustment (~1 : 0.52).
    """
    h_orig, w_orig = img.shape[:2]
    aspect_ratio = h_orig / float(w_orig)
    height = int(width * aspect_ratio * 0.52)

    pil_img = Image.fromarray(img)
    pil_resized = pil_img.resize((width, height), Image.Resampling.LANCZOS)
    img_resized = np.array(pil_resized)

    pil_mask = Image.fromarray(fg_mask.astype(np.uint8) * 255)
    pil_mask_resized = pil_mask.resize((width, height), Image.Resampling.NEAREST)
    mask_resized = np.array(pil_mask_resized) > 128

    return img_resized, mask_resized, width, height


def compute_gradient_field(img: np.ndarray) -> tuple:
    """
    Steps 9-12: Computes Sobel X, Sobel Y, Gradient Magnitude, and Gradient Direction (0..180 degrees).
    """
    sobelx = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3)

    magnitude = np.sqrt(sobelx**2 + sobely**2)
    # Normalize magnitude 0..255
    max_mag = np.max(magnitude)
    if max_mag > 0:
        magnitude_norm = (magnitude / max_mag) * 255.0
    else:
        magnitude_norm = magnitude

    angle = (np.arctan2(sobely, sobelx) * (180.0 / np.pi)) % 180.0
    return sobelx, sobely, magnitude_norm, angle


def apply_adaptive_local_contrast(img: np.ndarray) -> np.ndarray:
    """
    Step 13: Computes adaptive local contrast to enhance eyes, glasses, lips, and facial contours.
    """
    blur = cv2.GaussianBlur(img.astype(float), (5, 5), 0)
    diff = img.astype(float) - blur
    contrast_boosted = img.astype(float) + diff * 0.5
    return np.clip(contrast_boosted, 0, 255).astype(np.uint8)


def apply_floyd_steinberg_dithering(img_float: np.ndarray) -> np.ndarray:
    """
    Step 14: Applies Floyd-Steinberg error diffusion dithering across grayscale pixels.
    """
    h, w = img_float.shape
    dither_arr = img_float.copy()

    for y in range(h):
        for x in range(w):
            old_val = dither_arr[y, x]
            # Quantize
            quant_idx = int(round((old_val / 255.0) * NUM_DENSITY_LEVELS))
            quant_idx = max(0, min(NUM_DENSITY_LEVELS, quant_idx))
            new_val = (quant_idx / float(NUM_DENSITY_LEVELS)) * 255.0

            err = old_val - new_val
            dither_arr[y, x] = new_val

            # Distribute error to 4 neighbors
            if x + 1 < w:
                dither_arr[y, x + 1] += err * (7.0 / 16.0)
            if y + 1 < h:
                if x - 1 >= 0:
                    dither_arr[y + 1, x - 1] += err * (3.0 / 16.0)
                dither_arr[y + 1, x] += err * (5.0 / 16.0)
                if x + 1 < w:
                    dither_arr[y + 1, x + 1] += err * (1.0 / 16.0)

    return np.clip(dither_arr, 0, 255)


def select_adaptive_character(px: float, mag: float, ang: float, is_fg: bool) -> str:
    """
    Step 15: Edge-Aware Character Selection combining brightness, local contrast, edge orientation, and gradient magnitude.
    """
    if not is_fg or px >= 242:
        return " "  # Clean background space

    # High gradient edge (> 65 magnitude): Select character based on orientation & structure
    if mag > 65:
        if (0 <= ang < 22.5) or (157.5 <= ang <= 180):
            # Vertical edge (glasses sides, nose bridge, jawline)
            return "|" if px > 100 else "I"
        elif 22.5 <= ang < 67.5:
            # 45 degree diagonal edge
            return "/"
        elif 67.5 <= ang < 112.5:
            # Horizontal edge (glasses rims, eyebrows, lips)
            return "-" if px > 100 else "="
        elif 112.5 <= ang < 157.5:
            # 135 degree diagonal edge
            return "\\"

    # Dense dark features (hair, beard, dark shirt, pupils)
    if px < 45:
        return HAIR_DARK_CHARS[min(int((px / 45.0) * len(HAIR_DARK_CHARS)), len(HAIR_DARK_CHARS) - 1)]

    # Smooth skin & mid-tones: Select from 70-level density ramp
    ramp_idx = int(round((px / 255.0) * NUM_DENSITY_LEVELS))
    ramp_idx = max(0, min(NUM_DENSITY_LEVELS, ramp_idx))
    return DENSITY_RAMP[ramp_idx]


def get_github_dark_color(luminance: float) -> str:
    """
    Maps pixel luminance to GitHub Dark Theme color palette:
    Very dark  (< 40)   : #79c0ff (Bright cyan)
    Dark       (40..80) : #58a6ff (Primary blue)
    Medium     (80..130): #8ab4f8 (Soft blue)
    Light     (130..180): #8b949e (Slate gray)
    Very light (> 180)  : #484f58 (Dim gray)
    """
    if luminance < 40:
        return "#79c0ff"
    elif luminance < 80:
        return "#58a6ff"
    elif luminance < 130:
        return "#8ab4f8"
    elif luminance < 180:
        return "#8b949e"
    return "#484f58"


def generate_animated_svg(ascii_grid: list, luminance_grid: list, output_path: str,
                           font_size: float = 4.0, line_height: float = 5.2):
    """
    Steps 16-17: Renders SVG with monospaced text and left-to-right SMIL row reveal animation.
    """
    num_rows = len(ascii_grid)
    svg_width = 370  # Standard card container width
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

    # Step 17: Row-by-row left-to-right SMIL reveal animation
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

    # Step 16: SVG Generation with grouped <tspan> elements
    for i in range(num_rows):
        clip_id = f"clip-row-{i}"
        y_pos = start_y + (i * line_height)
        row_chars = ascii_grid[i]
        row_lum = luminance_grid[i]

        spans = []
        curr_color, curr_text = None, ""

        for char, lum in zip(row_chars, row_lum):
            color = get_github_dark_color(lum)
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

    print(f"Successfully generated Advanced Computer Vision ASCII SVG: '{output_path}' ({svg_width}x{svg_height}px)")


def render_ascii_portrait(image_path: str, output_path: str, width: int = 140):
    """
    Executes the exact 17-step processing pipeline.
    """
    if not os.path.exists(image_path):
        print(f"Error: Input file '{image_path}' not found.")
        sys.exit(1)

    print(f"[1/5] Loading image and isolating background from '{image_path}'...")
    img_bgr = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img_bgr is None:
        pil_img = Image.open(image_path)
        img_bgr = np.array(pil_img)

    # Step 1 & 2: Background detection & grayscale conversion
    gray, fg_mask = detect_and_remove_background(img_bgr)

    print("[2/5] Applying CLAHE, Bilateral filtering, Gamma correction & Unsharp masking...")
    # Steps 4-7: Pre-processing pipeline
    preprocessed = apply_preprocessing_pipeline(gray)

    print(f"[3/5] Resizing to {width} columns and computing Sobel gradient field & local contrast...")
    # Step 8: Resizing with Lanczos interpolation
    img_resized, mask_resized, grid_w, grid_h = resize_image(preprocessed, fg_mask, width=width)

    # Steps 9-12: Sobel X, Y, Magnitude, Angle
    sobelx, sobely, magnitude, angle = compute_gradient_field(img_resized)

    # Step 13: Adaptive local contrast
    contrast_img = apply_adaptive_local_contrast(img_resized)

    print("[4/5] Applying Floyd-Steinberg error diffusion dithering & edge-aware character selection...")
    # Step 14: Floyd-Steinberg dithering
    dithered_img = apply_floyd_steinberg_dithering(contrast_img.astype(float))

    # Step 15: Adaptive character selection
    ascii_grid = []
    luminance_grid = []

    for y in range(grid_h):
        ascii_row = []
        lum_row = []
        for x in range(grid_w):
            px_val = dithered_img[y, x]
            mag_val = magnitude[y, x]
            ang_val = angle[y, x]
            is_fg = mask_resized[y, x]

            char = select_adaptive_character(px_val, mag_val, ang_val, is_fg)
            ascii_row.append(char)
            lum_row.append(px_val)
        ascii_grid.append(ascii_row)
        luminance_grid.append(lum_row)

    print(f"[5/5] Rendering animated SMIL SVG to '{output_path}'...")
    # Steps 16-17: SVG generation & SMIL animation
    generate_animated_svg(ascii_grid, luminance_grid, output_path, font_size=3.8, line_height=5.0)


def main():
    parser = argparse.ArgumentParser(description="Advanced Computer Vision Edge-Aware ASCII Portrait Generator")
    parser.add_argument("--input", "-i", default="assets/source-prepped.png", help="Path to input prepped photo")
    parser.add_argument("--output", "-o", default="avi-ascii.svg", help="Path to output SVG card")
    parser.add_argument("--width", "-w", type=int, default=140, help="Character grid width (120-200, default: 140)")

    args = parser.parse_args()

    render_ascii_portrait(args.input, args.output, width=args.width)


if __name__ == "__main__":
    main()
