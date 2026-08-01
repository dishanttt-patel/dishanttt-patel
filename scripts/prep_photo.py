#!/usr/bin/env python3
"""
prep_photo.py
Preprocesses profile photo into a high-contrast Black & White prepped image:
1. Removes background with rembg (or alpha fallback).
2. Converts to high-contrast grayscale with CLAHE + Adaptive contrast enhancement.
3. Composites subject onto a pure white (#ffffff) canvas.
4. Saves to assets/source-prepped.png.
"""

import os
import sys
import argparse
import io
import numpy as np
from PIL import Image, ImageEnhance
import cv2

try:
    from rembg import remove
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False


def remove_background(image_bytes: bytes) -> Image.Image:
    """Removes image background using rembg if available."""
    if REMBG_AVAILABLE:
        try:
            print("Removing background with rembg...")
            out_bytes = remove(image_bytes)
            return Image.open(io.BytesIO(out_bytes)).convert("RGBA")
        except Exception as e:
            print(f"Warning: rembg failed ({e}), falling back to standard image processing.")

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    return img


def enhance_black_and_white(gray_np: np.ndarray, clip_limit: float = 3.5) -> np.ndarray:
    """Applies CLAHE + high-contrast Black & White feature separation."""
    # Adaptive histogram equalization
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    equalized = clahe.apply(gray_np)

    # Edge-preserving bilateral smoothing to keep glasses/eyes/mustache crisp
    filtered = cv2.bilateralFilter(equalized, d=7, sigmaColor=50, sigmaSpace=50)
    return filtered


def process_image(input_path: str, output_path: str):
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' does not exist.")
        sys.exit(1)

    print(f"Loading image from {input_path}...")
    with open(input_path, "rb") as f:
        img_bytes = f.read()

    # Step 1: Remove background
    rgba_img = remove_background(img_bytes)

    # Step 2: Separate RGB and Alpha mask
    np_rgba = np.array(rgba_img)
    rgb = np_rgba[:, :, :3]
    alpha = np_rgba[:, :, 3]

    # Convert RGB to Grayscale
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    # Step 3: Apply B&W enhancement
    bw_enhanced = enhance_black_and_white(gray)

    # Boost contrast on PIL image
    pil_bw = Image.fromarray(bw_enhanced)
    pil_bw = ImageEnhance.Contrast(pil_bw).enhance(1.5)
    pil_bw = ImageEnhance.Sharpness(pil_bw).enhance(1.6)
    bw_enhanced = np.array(pil_bw)

    # Step 4: Composite subject onto pure white (#ffffff / 255) background using Alpha mask
    output_np = np.ones_like(bw_enhanced) * 255
    mask = alpha > 30
    output_np[mask] = bw_enhanced[mask]

    # Step 5: Save prepped photo
    out_img = Image.fromarray(output_np)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    out_img.save(output_path)
    print(f"Successfully saved high-contrast prepped image to '{output_path}'.")


def main():
    parser = argparse.ArgumentParser(description="Preprocess photo into high-contrast B&W prepped image")
    parser.add_argument("--input", "-i", default="assets/input_photo.png", help="Path to input photo")
    parser.add_argument("--output", "-o", default="assets/source-prepped.png", help="Path to output image")

    args = parser.parse_args()
    process_image(args.input, args.output)


if __name__ == "__main__":
    main()
