#!/usr/bin/env python3
"""
High-accuracy ASCII portrait generator.

Strategy: Use a moderate font-size and add letter-spacing CSS so that
(char_advance + letter_spacing) * cols = card_usable_width.

This works even if we don't know the exact font metrics, because
letter-spacing adds uniform extra space per character.

Also: aspect ratio 0.55 for correct face proportions.
"""

import os, sys, argparse, html
import cv2
import numpy as np
from PIL import Image

RAMP = "@%#WMohd=:. "
NUM_LEVELS = len(RAMP) - 1


def pixel_to_color(px):
    if px < 50:   return "#e6edf3"
    if px < 100:  return "#79c0ff"
    if px < 150:  return "#58a6ff"
    if px < 200:  return "#8b949e"
    return "#484f58"


def load_and_resize(path, width):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        img = np.array(Image.open(path))

    if len(img.shape) == 3 and img.shape[2] == 4:
        gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
        fg = img[:, :, 3] > 20
    elif len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        fg = gray < 240
    else:
        gray, fg = img, img < 240

    h0, w0 = gray.shape
    # 0.55 aspect correction: balances vertical stretch for monospace cells
    height = int(width * (h0 / w0) * 0.55)

    gr = np.array(Image.fromarray(gray).resize((width, height), Image.Resampling.LANCZOS))
    mr = np.array(Image.fromarray((fg * 255).astype(np.uint8)).resize(
        (width, height), Image.Resampling.NEAREST)) > 128
    return gr, mr, width, height


def to_ascii(gray, mask):
    h, w = gray.shape
    chars, colors = [], []
    for y in range(h):
        cr, clr = [], []
        for x in range(w):
            if not mask[y, x] or gray[y, x] >= 248:
                cr.append(" "); clr.append("#0d1117")
            else:
                px = gray[y, x]
                idx = max(0, min(NUM_LEVELS, int(round((px / 255.0) * NUM_LEVELS))))
                cr.append(RAMP[idx]); clr.append(pixel_to_color(px))
        chars.append(cr); colors.append(clr)
    return chars, colors


def render_svg(chars, colors, out_path, cols):
    rows = len(chars)
    
    W = 370
    PAD = 4
    TW = W - 2 * PAD  # 362px

    # Target: each character cell = TW / cols pixels wide
    target_cell_w = TW / cols  # e.g. 362/80 = 4.525px per char

    # We pick a font-size. The natural advance width of monospace is
    # approximately 0.6 * font_size (varies by font).
    # We then add letter-spacing to make up the difference.
    font_size = 5.0  # readable but compact
    natural_advance = font_size * 0.6  # ~3.0px
    letter_spacing = target_cell_w - natural_advance  # extra space per char

    # Line height: tight, no gaps. Use 1.0 * target_cell_w * 2 for proper aspect
    line_h = font_size * 1.15  # slightly more than 1em to prevent clipping

    H = int(rows * line_h) + int(font_size) + 10
    y0 = font_size + 4

    L = []
    L.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
             f'viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
    L.append('<style>')
    L.append(f'rect.bg{{fill:#0d1117;rx:6;stroke:#30363d;stroke-width:.5}}')
    L.append(f'text{{font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;'
             f'font-size:{font_size:.2f}px;white-space:pre;font-weight:600;'
             f'letter-spacing:{letter_spacing:.3f}px}}')
    L.append('</style>')
    L.append(f'<rect width="{W}" height="{H}" class="bg"/>')

    # Animation
    L.append('<defs>')
    for i in range(rows):
        cy = y0 + i * line_h - font_size - 1
        d = round(i * 0.015, 3)
        L.append(f'<clipPath id="r{i}"><rect x="0" y="{cy:.1f}" width="0" height="{line_h + 3:.1f}">'
                 f'<animate attributeName="width" from="0" to="{W}" begin="{d}s" dur="0.03s" fill="freeze"/>'
                 f'</rect></clipPath>')
    L.append('</defs>')

    L.append('<g>')
    for i in range(rows):
        yp = y0 + i * line_h
        rc, rl = chars[i], colors[i]
        
        spans = []
        cc, ct = None, ""
        for ch, col in zip(rc, rl):
            e = html.escape(ch)
            if col == cc: ct += e
            else:
                if ct: spans.append(f'<tspan fill="{cc}">{ct}</tspan>')
                cc, ct = col, e
        if ct: spans.append(f'<tspan fill="{cc}">{ct}</tspan>')

        L.append(f'<text x="{PAD}" y="{yp:.1f}" clip-path="url(#r{i})">'
                 f'{"".join(spans)}</text>')
    L.append('</g>')
    L.append('</svg>')

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"OK: '{out_path}' ({W}x{H}px, {rows}x{cols})")
    print(f"   font={font_size}px, letter-spacing={letter_spacing:.3f}px, cell={target_cell_w:.2f}px")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-i", "--input", default="assets/source-prepped.png")
    p.add_argument("-o", "--output", default="avi-ascii.svg")
    p.add_argument("-w", "--width", type=int, default=80)
    a = p.parse_args()
    if not os.path.exists(a.input):
        print(f"Error: '{a.input}' not found."); sys.exit(1)

    g, m, gw, gh = load_and_resize(a.input, a.width)
    ch, co = to_ascii(g, m)
    render_svg(ch, co, a.output, gw)

if __name__ == "__main__":
    main()
