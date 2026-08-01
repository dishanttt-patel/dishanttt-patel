#!/usr/bin/env python3
"""
prep_photo.py
Preprocesses input photo into a high-sharpness, edge-enhanced, perfectly centered prepped image:
1. Isolates foreground subject & centers subject on a padded canvas.
2. Applies high-contrast CLAHE adaptive histogram equalization.
3. Applies Bilateral filtering + Laplacian edge amplification to define crisp facial edges.
4. Applies Unsharp Masking & Sharpness boosting.
5. Composites onto pure white background and saves to assets/source-prepped.png.
"""

import os
import sys
import argparse
import numpy as np
import cv2
from PIL import Image, ImageFilter, ImageEnhance


def process_image(input_path: str, output_path: str):
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' does not exist.")
        sys.exit(1)

    print(f"Loading image from '{input_path}'...")
    img_bgr = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)
    if img_bgr is None:
        pil_img = Image.open(input_path)
        img_bgr = np.array(pil_img)

    # 1. Grayscale & Foreground Mask
    if len(img_bgr.shape) == 3 and img_bgr.shape[2] == 4:
        alpha = img_bgr[:, :, 3]
        gray = cv2.cvtColor(img_bgr[:, :, :3], cv2.COLOR_BGR2GRAY)
        fg_mask = alpha > 30
    elif len(img_bgr.shape) == 3:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        fg_mask = gray < 225
    else:
        gray = img_bgr.copy()
        fg_mask = gray < 225

    # 2. Compute Subject Bounding Box for Centering
    y_indices, x_indices = np.where(fg_mask)
    if len(y_indices) > 0 and len(x_indices) > 0:
        min_y, max_y = np.min(y_indices), np.max(y_indices)
        min_x, max_x = np.min(x_indices), np.max(x_indices)

        cropped_gray = gray[min_y:max_y, min_x:max_x]
        cropped_mask = fg_mask[min_y:max_y, min_x:max_x]

        # Create padded square canvas to center subject
        h_crop, w_crop = cropped_gray.shape
        max_dim = max(h_crop, w_crop)

        centered_gray = np.ones((max_dim, max_dim), dtype=np.uint8) * 255
        centered_mask = np.zeros((max_dim, max_dim), dtype=bool)

        start_y = (max_dim - h_crop) // 2
        start_x = (max_dim - w_crop) // 2

        centered_gray[start_y:start_y + h_crop, start_x:start_x + w_crop] = cropped_gray
        centered_mask[start_y:start_y + h_crop, start_x:start_x + w_crop] = cropped_mask
    else:
        centered_gray = gray
        centered_mask = fg_mask

    # 3. High-Contrast CLAHE + Bilateral Filtering
    print("Applying CLAHE contrast equalization & bilateral filtering...")
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
    equalized = clahe.apply(centered_gray)
    bilateral = cv2.bilateralFilter(equalized, d=7, sigmaColor=50, sigmaSpace=50)

    # 4. Laplacian Edge Amplification (Sharpen structural boundaries)
    print("Amplifying structural edge contours (glasses, eyes, mustache, beard, chin, shirt)...")
    laplacian = cv2.Laplacian(bilateral, cv2.CV_64F)
    laplacian_abs = np.uint8(np.absolute(laplacian))
    edge_enhanced = cv2.subtract(bilateral, np.uint8(laplacian_abs * 0.45))

    # 5. Unsharp Masking & Sharpness Boosting
    pil_img = Image.fromarray(edge_enhanced)
    pil_unsharp = pil_img.filter(ImageFilter.UnsharpMask(radius=3, percent=250, threshold=1))
    pil_sharp = ImageEnhance.Sharpness(pil_unsharp).enhance(2.0)
    final_np = np.array(pil_sharp)

    # Composite subject onto pure white background
    composite = np.ones_like(final_np) * 255
    composite[centered_mask] = final_np[centered_mask]

    # Save to assets/source-prepped.png
    out_img = Image.fromarray(composite)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    out_img.save(output_path)
    print(f"Successfully saved sharp, edge-enhanced prepped image to '{output_path}'.")


def main():
    parser = argparse.ArgumentParser(description="Preprocess photo into high-sharpness edge-enhanced prepped image")
    parser.add_argument("--input", "-i", default="assets/input_photo.png", help="Path to input photo")
    parser.add_argument("--output", "-o", default="assets/source-prepped.png", help="Path to output image")

    args = parser.parse_args()
    process_image(args.input, args.output)


if __name__ == "__main__":
    main()
