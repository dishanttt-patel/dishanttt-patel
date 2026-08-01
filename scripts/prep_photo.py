#!/usr/bin/env python3
"""
prep_photo.py
Preprocesses a profile photo for clean, highly recognizable ASCII art conversion:
1. Removes background (via rembg or fallback thresholding).
2. Applies CLAHE (Contrast Limited Adaptive Histogram Equalization) via OpenCV to enhance facial features.
3. Composites subject onto pure white background.
4. Auto-crops tightly around HEAD AND SHOULDERS (top ~50% of subject height) so facial details are max resolution.
5. Saves to source-prepped.png.
"""

import os
import sys
import argparse
import io
import numpy as np
from PIL import Image
import cv2

try:
    from rembg import remove
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False


def remove_background(image_bytes: bytes) -> Image.Image:
    """Removes image background using rembg if available, or returns transparent background PIL Image."""
    if REMBG_AVAILABLE:
        try:
            print("Removing background with rembg...")
            out_bytes = remove(image_bytes)
            return Image.open(io.BytesIO(out_bytes)).convert("RGBA")
        except Exception as e:
            print(f"Warning: rembg failed ({e}), falling back to standard image processing.")

    # Fallback if rembg fails or isn't installed
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    return img


def apply_clahe(gray_img: np.ndarray, clip_limit: float = 3.0, tile_grid_size: tuple = (8, 8)) -> np.ndarray:
    """Applies Contrast Limited Adaptive Histogram Equalization to grayscale numpy image."""
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    return clahe.apply(gray_img)


def process_image(input_path: str, output_path: str, clip_limit: float = 3.0):
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' does not exist.")
        sys.exit(1)

    print(f"Loading image from {input_path}...")
    with open(input_path, "rb") as f:
        img_bytes = f.read()

    # Step 1: Remove Background
    rgba_img = remove_background(img_bytes)
    np_rgba = np.array(rgba_img)

    rgb = np_rgba[:, :, :3]
    alpha = np_rgba[:, :, 3] if np_rgba.shape[2] == 4 else np.ones((np_rgba.shape[0], np_rgba.shape[1]), dtype=np.uint8) * 255

    # Step 2: Convert to Grayscale & Apply CLAHE Contrast Boost
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    clahe_gray = apply_clahe(gray, clip_limit=clip_limit)

    # Step 3: Composite onto pure white background
    white_bg = np.ones_like(clahe_gray) * 255
    alpha_factor = alpha.astype(float) / 255.0

    final_gray = (clahe_gray * alpha_factor + white_bg * (1.0 - alpha_factor)).astype(np.uint8)

    # Step 4: Auto-crop tightly around HEAD AND SHOULDERS (top ~50% of subject height)
    non_white_mask = final_gray < 245
    if np.any(non_white_mask):
        y_indices, x_indices = np.where(non_white_mask)
        ymin, ymax = y_indices.min(), y_indices.max()
        xmin, xmax = x_indices.min(), x_indices.max()

        # Target Head & Shoulders: top 50% of subject height
        subj_h = ymax - ymin
        crop_ymax = min(final_gray.shape[0], ymin + int(subj_h * 0.52))
        crop_ymin = max(0, ymin - int(subj_h * 0.02))

        # Horizontal padding
        pad_x = int((xmax - xmin) * 0.03)
        crop_xmin = max(0, xmin - pad_x)
        crop_xmax = min(final_gray.shape[1], xmax + pad_x)

        final_gray = final_gray[crop_ymin:crop_ymax, crop_xmin:crop_xmax]

    # Save processed result
    res_img = Image.fromarray(final_gray, mode="L")
    res_img.save(output_path)
    print(f"Successfully prepped and cropped head & shoulders image to '{output_path}'.")


def main():
    parser = argparse.ArgumentParser(description="Prep photo for ASCII conversion (Head & Shoulders crop + CLAHE)")
    parser.add_argument("--input", "-i", default="assets/input_photo.png", help="Path to input photo")
    parser.add_argument("--output", "-o", default="assets/source-prepped.png", help="Path to output prepped photo")
    parser.add_argument("--clip-limit", type=float, default=3.0, help="CLAHE contrast clip limit")

    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    process_image(args.input, args.output, args.clip_limit)


if __name__ == "__main__":
    main()
