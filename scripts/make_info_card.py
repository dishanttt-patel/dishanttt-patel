#!/usr/bin/env python3
"""
make_info_card.py
Generates a neofetch-style info card SVG with animated line-by-line printing/fade-in.
Supports STATIC=1 environment variable to output a static SVG for previews.
Width: 490px (designed to align next to 370px ASCII art in an 860px terminal layout).
"""

import os
import sys
import argparse
import html

CARD_WIDTH = 490
CARD_HEIGHT = 500


def generate_info_card_svg(output_path: str, static_mode: bool = False, username: str = "DISHANT"):
    user_title = f"{username.lower()}@github"

    # Info card rows
    info_rows = [
        ("OS", "macOS Sonoma / Arch Linux x86_64", "#79c0ff"),
        ("Host", "GitHub Profile Terminal v2.4", "#79c0ff"),
        ("Role", "Software Engineer & AI Builder", "#a5d6ff"),
        ("Now", "Developing AI tools & web apps", "#7ee787"),
        ("Prev", "Full Stack Developer", "#d2a8ff"),
        ("Stack", "Python, TypeScript, React, Node.js, PyTorch", "#ffa657"),
        ("Highlights", "Open Source, System Architecture, Web Dev", "#ff7b72"),
        ("Uptime", "24/7 Automation via GitHub Actions", "#a5d6ff"),
    ]

    color_palette = [
        "#484f58", "#ff7b72", "#7ee787", "#ffa657",
        "#79c0ff", "#d2a8ff", "#a5d6ff", "#f0f6fc"
    ]

    anim_style = ""
    if not static_mode:
        anim_style = """
    .animate-row {
      opacity: 0;
      transform: translateY(6px);
      animation: fadeInRow 0.4s ease-out forwards;
    }
    @keyframes fadeInRow {
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
    """

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}" width="{CARD_WIDTH}" height="{CARD_HEIGHT}">',
        '  <style>',
        '    .card-bg { fill: #0d1117; rx: 8px; stroke: #30363d; stroke-width: 1px; }',
        '    .title-bar { fill: #161b22; rx: 8px 8px 0 0; }',
        '    .dot-red { fill: #ff5f56; }',
        '    .dot-yellow { fill: #ffbd2e; }',
        '    .dot-green { fill: #27c93f; }',
        '    .term-title { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; font-size: 12px; fill: #8b949e; font-weight: 600; }',
        '    .text-base { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; font-size: 12.5px; }',
        '    .user-header { fill: #58a6ff; font-weight: 700; font-size: 14px; }',
        '    .separator { stroke: #30363d; stroke-width: 1px; stroke-dasharray: 4; }',
        '    .key { fill: #79c0ff; font-weight: 600; }',
        '    .val { fill: #c9d1d9; }',
        anim_style,
        '  </style>',
        f'  <rect width="{CARD_WIDTH}" height="{CARD_HEIGHT}" class="card-bg" />',
        f'  <rect width="{CARD_WIDTH}" height="32" class="title-bar" />',
        '  <!-- Window Control Dots -->',
        '  <circle cx="16" cy="16" r="5.5" class="dot-red" />',
        '  <circle cx="32" cy="16" r="5.5" class="dot-yellow" />',
        '  <circle cx="48" cy="16" r="5.5" class="dot-green" />',
        f'  <text x="{CARD_WIDTH / 2}" y="20" text-anchor="middle" class="term-title">{user_title}: ~ (neofetch)</text>',
        '  <g transform="translate(20, 45)">'
    ]

    # User Header
    delay = 0.1
    cls_attr = f' class="animate-row" style="animation-delay: {delay:.2f}s;"' if not static_mode else ''
    svg_parts.append(f'    <g{cls_attr}>')
    svg_parts.append(f'      <text x="0" y="20" class="text-base user-header">{username.lower()}<tspan fill="#8b949e">@</tspan>github-profile</text>')
    svg_parts.append('      <line x1="0" y1="28" x2="450" y2="28" class="separator" />')
    svg_parts.append('    </g>')

    # Render Info Rows
    start_y = 52
    line_spacing = 38
    for i, (key, val, key_color) in enumerate(info_rows):
        y_pos = start_y + (i * line_spacing)
        delay += 0.08
        cls_attr = f' class="animate-row" style="animation-delay: {delay:.2f}s;"' if not static_mode else ''

        key_esc = html.escape(key)
        val_esc = html.escape(val)

        svg_parts.append(f'    <g{cls_attr}>')
        svg_parts.append(f'      <text x="0" y="{y_pos}" class="text-base">')
        svg_parts.append(f'        <tspan fill="{key_color}" font-weight="700">{key_esc}:</tspan>')
        # Calculate padding
        pad_x = max(110, len(key) * 10 + 20)
        svg_parts.append(f'        <tspan x="{pad_x}" class="val">{val_esc}</tspan>')
        svg_parts.append('      </text>')
        svg_parts.append('    </g>')

    # Color Palette Footer
    palette_y = start_y + (len(info_rows) * line_spacing) + 12
    delay += 0.1
    cls_attr = f' class="animate-row" style="animation-delay: {delay:.2f}s;"' if not static_mode else ''

    svg_parts.append(f'    <g{cls_attr}>')
    svg_parts.append(f'      <g transform="translate(0, {palette_y})">')
    for i, color in enumerate(color_palette):
        x_pos = i * 22
        svg_parts.append(f'        <rect x="{x_pos}" y="0" width="18" height="14" rx="3" fill="{color}" />')
    svg_parts.append('      </g>')
    svg_parts.append('    </g>')

    svg_parts.append('  </g>')
    svg_parts.append('</svg>')

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_parts))

    mode_str = "static" if static_mode else "animated"
    print(f"Successfully generated {mode_str} info card SVG at '{output_path}'.")


def main():
    parser = argparse.ArgumentParser(description="Generate neofetch-style info card SVG")
    parser.add_argument("--output", "-o", default="info-card.svg", help="Output path for SVG")
    parser.add_argument("--username", "-u", default="DISHANT", help="GitHub Username")
    parser.add_argument("--static", action="store_true", help="Force static output without animation")

    args = parser.parse_args()

    static_env = os.environ.get("STATIC", "0") == "1" or args.static
    generate_info_card_svg(args.output, static_mode=static_env, username=args.username)


if __name__ == "__main__":
    main()
