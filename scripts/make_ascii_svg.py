#!/usr/bin/env python3
"""
===============================================================================
               MASTERCLASS HIGH-FIDELITY ASCII PORTRAIT GENERATOR
===============================================================================
Description:
    A complete, clean, end-to-end Python engine that converts profile photos
    into photorealistic animated ASCII SVG vector artwork for GitHub profile READMEs.

Features:
    - Adaptive Edge-Preserving Contrast Equalization (OpenCV CLAHE + Bilateral)
    - High-Density Monospaced Character Mapping
    - Multi-Tone Cyberpunk / Terminal Color Styling
    - Row-by-Row SMIL Reveal Animation

Usage:
    python make_ascii_svg.py --input assets/source-prepped.png --output avi-ascii.svg --width 120
===============================================================================
"""

import os
import sys
import argparse
import html
import cv2
import numpy as np
from PIL import Image

# Master 20-level character density ramp ordered from high-density to low-density
DEFAULT_RAMP = ["@", "#", "$", "%", "8", "&", "W", "M", "0", "Q", "P", "o", "a", "+", "=", ":", "-", ".", "'", " "]


class ASCIIPortraitGenerator:
    """Core engine for converting images to animated monospaced ASCII SVG cards."""

    def __init__(self, char_ramp: list = None):
        self.ramp = char_ramp or DEFAULT_RAMP
        self.num_levels = len(self.ramp) - 1

    def get_color(self, char: str) -> str:
        """Maps individual ASCII characters to multi-tone terminal colors."""
        if char in ["@", "#", "$", "%"]:
            return "#ffffff"  # Bright white for glasses, pupils, dark hair & clothing
        elif char in ["8", "&", "W", "M", "0"]:
            return "#79c0ff"  # Vibrant cyan for facial contours, mustache & beard
        elif char in ["Q", "P", "o", "a"]:
            return "#58a6ff"  # Primary blue for mid-tone skin shading
        elif char in ["+", "=", ":", "-", ".", "'"]:
            return "#8b949e"  # Slate gray for skin highlights
        return "#30363d"     # Canvas background space

    def process_image(self, image_path: str, width: int = 120) -> list:
        """
        Loads, filters, downsamples, and maps an image into a 2D ASCII character grid.
        
        Args:
            image_path (str): Path to input image file.
            width (int): Grid column count.
            
        Returns:
            list of list of str: 2D array of ASCII characters.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Input image file '{image_path}' not found.")

        # Read image in Grayscale
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            pil_img = Image.open(image_path).convert("L")
            img = np.array(pil_img)

        # 1. Edge-preserving bilateral filter + local CLAHE contrast enhancement
        filt = cv2.bilateralFilter(img, d=7, sigmaColor=50, sigmaSpace=50)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(filt)

        # 2. Monospaced aspect ratio downsampling (~1 : 0.52 character width-to-height ratio)
        pil_img = Image.fromarray(enhanced)
        aspect_ratio = pil_img.height / pil_img.width
        height = int(width * aspect_ratio * 0.52)

        img_resized = pil_img.resize((width, height), Image.Resampling.LANCZOS)
        np_img = np.array(img_resized)

        # 3. Map pixel values (0..255) to character density ramp
        ascii_grid = []
        for y in range(height):
            row = []
            for x in range(width):
                px = np_img[y, x]
                if px >= 242:
                    row.append(" ")
                else:
                    idx = min(int((px / 241.0) * self.num_levels), self.num_levels)
                    row.append(self.ramp[idx])
            ascii_grid.append(row)

        return ascii_grid

    def render_svg(self, ascii_grid: list, output_path: str, font_size: float = 4.4, line_height: float = 5.6):
        """
        Renders a 2D ASCII grid into a responsive, animated SMIL vector SVG card.
        
        Args:
            ascii_grid (list): 2D array of ASCII characters.
            output_path (str): File path for generated SVG file.
            font_size (float): Character font size in pixels.
            line_height (float): Vertical line height in pixels.
        """
        num_rows = len(ascii_grid)
        svg_width = 370  # Standard card width matching GitHub README sidebars
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

        # Generate SMIL row-by-row reveal animation clipPaths
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

        # Group contiguous same-colored characters into optimized <tspan> tags
        for i, row_chars in enumerate(ascii_grid):
            clip_id = f"clip-row-{i}"
            y_pos = start_y + (i * line_height)
            spans = []
            curr_color, curr_text = None, ""

            for char in row_chars:
                color = self.get_color(char)
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

        print(f"Successfully generated Masterclass ASCII SVG: '{output_path}' ({svg_width}x{svg_height}px)")


def main():
    parser = argparse.ArgumentParser(description="Masterclass High-Fidelity ASCII Portrait Generator")
    parser.add_argument("--input", "-i", default="assets/source-prepped.png", help="Path to prepped photo")
    parser.add_argument("--output", "-o", default="avi-ascii.svg", help="Path to output SVG card")
    parser.add_argument("--width", "-w", type=int, default=120, help="Grid column width (default: 120)")

    args = parser.parse_args()

    generator = ASCIIPortraitGenerator()
    grid = generator.process_image(args.input, width=args.width)
    generator.render_svg(grid, args.output)


if __name__ == "__main__":
    main()
