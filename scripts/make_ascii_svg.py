#!/usr/bin/env python3
"""
High-accuracy ASCII portrait generator.
Uses textLength with spacingAndGlyphs to fill the card width perfectly.
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
    height = int(width * (h0 / w0) * 0.45)

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
    PAD = 8
    TW = W - 2 * PAD  # text area width = 354px

    # Font size: we want each character to be TW/cols wide
    # With spacingAndGlyphs, the browser stretches glyphs to fit textLength
    char_w = TW / cols
    font_size = char_w / 0.6  # monospace char is ~0.6em wide
    line_h = font_size * 1.0  # tight — no gaps between rows

    H = int(rows * line_h) + 20
    y0 = font_size + 6

    L = []
    L.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
    L.append('<style>')
    L.append('.bg{fill:#0d1117;rx:6;stroke:#30363d;stroke-width:.5}')
    L.append(f'text{{font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;'
             f'font-size:{font_size:.2f}px;white-space:pre;font-weight:700}}')
    L.append('</style>')
    L.append(f'<rect width="{W}" height="{H}" class="bg"/>')

    # Animation clip paths
    L.append('<defs>')
    for i in range(rows):
        cy = y0 + i * line_h - font_size
        d = round(i * 0.012, 3)
        L.append(f'<clipPath id="r{i}"><rect x="0" y="{cy:.1f}" width="0" height="{line_h + 2:.1f}">'
                 f'<animate attributeName="width" from="0" to="{W}" begin="{d}s" dur="0.025s" fill="freeze"/>'
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

        L.append(f'<text x="{PAD}" y="{yp:.1f}" textLength="{TW}" '
                 f'lengthAdjust="spacingAndGlyphs" clip-path="url(#r{i})">'
                 f'{"".join(spans)}</text>')
    L.append('</g>')
    L.append('</svg>')

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"Generated: '{out_path}' ({W}x{H}px, {rows}x{cols}, font={font_size:.1f}px)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-i", "--input", default="assets/source-prepped.png")
    p.add_argument("-o", "--output", default="avi-ascii.svg")
    p.add_argument("-w", "--width", type=int, default=100)
    a = p.parse_args()
    if not os.path.exists(a.input):
        print(f"Error: '{a.input}' not found."); sys.exit(1)

    print(f"[1/3] Loading, resizing to {a.width} cols...")
    g, m, gw, gh = load_and_resize(a.input, a.width)
    print(f"[2/3] Mapping {gw}x{gh} -> {NUM_LEVELS+1}-level ramp...")
    ch, co = to_ascii(g, m)
    print("[3/3] Rendering SVG...")
    render_svg(ch, co, a.output, gw)

if __name__ == "__main__":
    main()
