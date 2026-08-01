#!/usr/bin/env python3
"""
prep_photo.py — Gentle, detail-preserving photo preprocessor for ASCII art.

Pipeline:
  1. Load input photo, convert to grayscale
  2. Auto-detect foreground subject bounding box
  3. Crop to subject, then center on a padded canvas
  4. Gentle CLAHE (clip=2.0) to open shadows without blowing highlights
  5. Light bilateral filter to reduce noise but keep edges
  6. Gentle gamma correction to lift shadows slightly
  7. Save centered, clean prepped image
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

    # --- Step 1: Grayscale conversion & foreground mask ---
    if len(img_bgr.shape) == 3 and img_bgr.shape[2] == 4:
        alpha = img_bgr[:, :, 3]
        gray = cv2.cvtColor(img_bgr[:, :, :3], cv2.COLOR_BGR2GRAY)
        fg_mask = alpha > 20
    elif len(img_bgr.shape) == 3:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        fg_mask = gray < 230
    else:
        gray = img_bgr.copy()
        fg_mask = gray < 230

    # --- Step 2: Find subject bounding box ---
    ys, xs = np.where(fg_mask)
    if len(ys) == 0:
        print("Warning: No foreground detected, using full image.")
        cropped = gray
        cropped_mask = fg_mask
    else:
        min_y, max_y = ys.min(), ys.max()
        min_x, max_x = xs.min(), xs.max()

        # Tight crop with minimal padding
        pad = int(max(max_y - min_y, max_x - min_x) * 0.03)
        y0 = max(0, min_y - pad)
        y1 = min(gray.shape[0], max_y + pad)
        x0 = max(0, min_x - pad)
        x1 = min(gray.shape[1], max_x + pad)

        cropped = gray[y0:y1, x0:x1]
        cropped_mask = fg_mask[y0:y1, x0:x1]

    # --- Step 3: Center subject on a padded canvas ---
    # Add equal horizontal padding so the subject is centered
    h_crop, w_crop = cropped.shape
    # Add 8% padding on each side for breathing room
    h_pad = int(h_crop * 0.04)
    w_pad = int(w_crop * 0.08)
    
    canvas_h = h_crop + 2 * h_pad
    canvas_w = w_crop + 2 * w_pad
    
    centered = np.full((canvas_h, canvas_w), 255, dtype=np.uint8)
    centered_mask = np.zeros((canvas_h, canvas_w), dtype=bool)
    
    centered[h_pad:h_pad + h_crop, w_pad:w_pad + w_crop] = cropped
    centered_mask[h_pad:h_pad + h_crop, w_pad:w_pad + w_crop] = cropped_mask

    # --- Step 4: Gentle CLAHE ---
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    equalized = clahe.apply(centered)

    # --- Step 5: Light bilateral filter ---
    smooth = cv2.bilateralFilter(equalized, d=5, sigmaColor=40, sigmaSpace=40)

    # --- Step 6: Gentle gamma correction (0.9) ---
    gamma = 0.9
    table = np.array([((i / 255.0) ** (1.0 / gamma)) * 255
                       for i in range(256)]).astype("uint8")
    corrected = cv2.LUT(smooth, table)

    # --- Step 7: Composite & save ---
    result = np.full_like(corrected, 255)
    result[centered_mask] = corrected[centered_mask]

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    Image.fromarray(result).save(output_path)
    print(f"Saved centered prepped image: '{output_path}' ({result.shape[1]}x{result.shape[0]})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", default="assets/input_photo.png")
    parser.add_argument("--output", "-o", default="assets/source-prepped.png")
    args = parser.parse_args()
    process_image(args.input, args.output)


if __name__ == "__main__":
    main()
