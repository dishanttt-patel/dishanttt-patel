#!/usr/bin/env python3
"""
prep_photo.py — Photo preprocessor for ASCII art.

Creates a high-contrast, well-centered grayscale image optimized for
character density mapping.
"""

import os
import sys
import argparse
import numpy as np
import cv2
from PIL import Image


def process_image(input_path: str, output_path: str):
    if not os.path.exists(input_path):
        print(f"Error: '{input_path}' not found.")
        sys.exit(1)

    print(f"Loading '{input_path}'...")
    img_bgr = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)
    if img_bgr is None:
        img_bgr = np.array(Image.open(input_path))

    # Grayscale + foreground mask
    if len(img_bgr.shape) == 3 and img_bgr.shape[2] == 4:
        gray = cv2.cvtColor(img_bgr[:, :, :3], cv2.COLOR_BGR2GRAY)
        fg_mask = img_bgr[:, :, 3] > 20
    elif len(img_bgr.shape) == 3:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        fg_mask = gray < 230
    else:
        gray = img_bgr.copy()
        fg_mask = gray < 230

    # Find subject bounding box and crop
    ys, xs = np.where(fg_mask)
    if len(ys) == 0:
        cropped = gray
        cropped_mask = fg_mask
    else:
        min_y, max_y = ys.min(), ys.max()
        min_x, max_x = xs.min(), xs.max()
        pad = int(max(max_y - min_y, max_x - min_x) * 0.03)
        y0, y1 = max(0, min_y - pad), min(gray.shape[0], max_y + pad)
        x0, x1 = max(0, min_x - pad), min(gray.shape[1], max_x + pad)
        cropped = gray[y0:y1, x0:x1]
        cropped_mask = fg_mask[y0:y1, x0:x1]

    # CLAHE with moderate contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    equalized = clahe.apply(cropped)

    # Light bilateral filter
    smooth = cv2.bilateralFilter(equalized, d=5, sigmaColor=40, sigmaSpace=40)

    # Histogram stretch to use full 0-255 range on foreground pixels
    fg_pixels = smooth[cropped_mask]
    if len(fg_pixels) > 0:
        p_low, p_high = np.percentile(fg_pixels, [1, 99])
        stretched = np.clip((smooth.astype(float) - p_low) / (p_high - p_low) * 255, 0, 255).astype(np.uint8)
    else:
        stretched = smooth

    # Composite onto white background
    result = np.full_like(stretched, 255)
    result[cropped_mask] = stretched[cropped_mask]

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    Image.fromarray(result).save(output_path)
    print(f"Saved prepped image: '{output_path}' ({result.shape[1]}x{result.shape[0]})")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", "-i", default="assets/input_photo.png")
    p.add_argument("--output", "-o", default="assets/source-prepped.png")
    process_image(p.parse_args().input, p.parse_args().output)


if __name__ == "__main__":
    main()
