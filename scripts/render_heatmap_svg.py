#!/usr/bin/env python3
"""
render_heatmap_svg.py
Renders data/contributions.json as an animated contribution heatmap SVG.
Width: 860px (perfectly aligns with the 370px + 490px top row elements).
Features diagonal slide-in animation, month labels, day labels, legend, and stats footer.
"""

import os
import sys
import json
import argparse
from datetime import datetime

HEATMAP_WIDTH = 860
HEATMAP_HEIGHT = 220

LEVEL_COLORS = {
    0: "#161b22",
    1: "#0e4429",
    2: "#006d32",
    3: "#26a641",
    4: "#39d353"
}

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAY_LABELS = ["", "Mon", "", "Wed", "", "Fri", ""]


def render_heatmap_svg(json_path: str, output_path: str):
    if not os.path.exists(json_path):
        print(f"Error: JSON dataset '{json_path}' not found.")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    days = data.get("days", [])
    stats = data.get("stats", {})
    username = data.get("username", "developer")

    total_cnt = stats.get("total_contributions", sum(d.get("count", 0) for d in days))
    curr_streak = stats.get("current_streak", 0)
    max_streak = stats.get("longest_streak", 0)

    # Grid sizing
    cell_size = 10.5
    cell_gap = 3.5
    step = cell_size + cell_gap

    start_x = 45
    start_y = 52

    # Group days into 53 weeks (columns) x 7 days (rows)
    # Build week columns
    weeks = []
    current_week = []

    for i, d in enumerate(days):
        current_week.append(d)
        if len(current_week) == 7 or i == len(days) - 1:
            weeks.append(current_week)
            current_week = []

    weeks = weeks[:53]  # Ensure max 53 weeks

    # Month Labels logic
    month_labels = []
    prev_month = -1
    for col_idx, week in enumerate(weeks):
        if week:
            first_day_date = datetime.strptime(week[0]["date"], "%Y-%m-%d")
            m = first_day_date.month
            if m != prev_month:
                x_pos = start_x + (col_idx * step)
                month_labels.append((x_pos, MONTH_NAMES[m - 1]))
                prev_month = m

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {HEATMAP_WIDTH} {HEATMAP_HEIGHT}" width="{HEATMAP_WIDTH}" height="{HEATMAP_HEIGHT}">',
        '  <style>',
        '    .bg { fill: #0d1117; rx: 8px; stroke: #30363d; stroke-width: 1px; }',
        '    .title-bar { fill: #161b22; rx: 8px 8px 0 0; }',
        '    .dot-red { fill: #ff5f56; }',
        '    .dot-yellow { fill: #ffbd2e; }',
        '    .dot-green { fill: #27c93f; }',
        '    .term-title { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; font-size: 12px; fill: #8b949e; font-weight: 600; }',
        '    .label-text { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; font-size: 10px; fill: #7d8590; }',
        '    .footer-text { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; font-size: 11.5px; fill: #c9d1d9; font-weight: 500; }',
        '    .highlight { fill: #39d353; font-weight: 700; }',
        '    .cell { stroke: rgba(255,255,255,0.05); stroke-width: 0.5px; rx: 2px; }',
        '    .cell-anim {',
        '      opacity: 0;',
        '      transform: translateY(-8px) scale(0.9);',
        '      animation: diagonalSlide 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;',
        '    }',
        '    @keyframes diagonalSlide {',
        '      to {',
        '        opacity: 1;',
        '        transform: translateY(0) scale(1);',
        '      }',
        '    }',
        '  </style>',
        f'  <rect width="{HEATMAP_WIDTH}" height="{HEATMAP_HEIGHT}" class="bg" />',
        f'  <rect width="{HEATMAP_WIDTH}" height="32" class="title-bar" />',
        '  <!-- Controls -->',
        '  <circle cx="16" cy="16" r="5.5" class="dot-red" />',
        '  <circle cx="32" cy="16" r="5.5" class="dot-yellow" />',
        '  <circle cx="48" cy="16" r="5.5" class="dot-green" />',
        f'  <text x="{HEATMAP_WIDTH / 2}" y="20" text-anchor="middle" class="term-title">{username}@github: ~ (gh stats --contributions)</text>',
        '  <g transform="translate(0, 10)">'
    ]

    # Month headers
    for x_pos, month_str in month_labels:
        svg_lines.append(f'    <text x="{x_pos}" y="{start_y - 8}" class="label-text">{month_str}</text>')

    # Day row labels (Mon, Wed, Fri)
    for row_idx, label in enumerate(DAY_LABELS):
        if label:
            y_pos = start_y + (row_idx * step) + 9
            svg_lines.append(f'    <text x="22" y="{y_pos}" class="label-text">{label}</text>')

    # Heatmap Grid Cells
    for col_idx, week in enumerate(weeks):
        for row_idx, day_data in enumerate(week):
            x_pos = start_x + (col_idx * step)
            y_pos = start_y + (row_idx * step)
            level = day_data.get("level", 0)
            color = LEVEL_COLORS.get(level, LEVEL_COLORS[0])
            count = day_data.get("count", 0)
            date_str = day_data.get("date", "")

            # Staggered diagonal animation delay
            delay = round((col_idx * 0.015) + (row_idx * 0.01), 3)

            svg_lines.append(
                f'    <rect class="cell cell-anim" x="{x_pos}" y="{y_pos}" width="{cell_size}" height="{cell_size}" '
                f'fill="{color}" style="animation-delay: {delay}s;">'
                f'<title>{count} contributions on {date_str}</title></rect>'
            )

    # Footer section (Stats & Legend)
    footer_y = start_y + (7 * step) + 22
    formatted_total = f"{total_cnt:,}"

    svg_lines.append(f'    <text x="{start_x}" y="{footer_y}" class="footer-text">')
    svg_lines.append(f'      <tspan class="highlight">{formatted_total}</tspan> contributions in the last year')
    svg_lines.append(f'      <tspan fill="#8b949e"> | Streak: </tspan><tspan fill="#7ee787">{curr_streak} days</tspan>')
    svg_lines.append(f'      <tspan fill="#8b949e"> (Max: {max_streak} days)</tspan>')
    svg_lines.append('    </text>')

    # Legend (Less -> More)
    legend_x = HEATMAP_WIDTH - 155
    svg_lines.append(f'    <g transform="translate({legend_x}, {footer_y - 10})">')
    svg_lines.append('      <text x="0" y="9" class="label-text">Less</text>')
    for lvl in range(5):
        lx = 28 + (lvl * 13)
        lcolor = LEVEL_COLORS[lvl]
        svg_lines.append(f'      <rect x="{lx}" y="0" width="10" height="10" fill="{lcolor}" rx="2" class="cell" />')
    svg_lines.append('      <text x="96" y="9" class="label-text">More</text>')
    svg_lines.append('    </g>')

    svg_lines.append('  </g>')
    svg_lines.append('</svg>')

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_lines))

    print(f"Successfully rendered animated contribution heatmap SVG to '{output_path}'.")


def main():
    parser = argparse.ArgumentParser(description="Render animated contribution heatmap SVG")
    parser.add_argument("--input", "-i", default="data/contributions.json", help="Path to contributions JSON")
    parser.add_argument("--output", "-o", default="contrib-heatmap.svg", help="Output SVG path")

    args = parser.parse_args()
    render_heatmap_svg(args.input, args.output)


if __name__ == "__main__":
    main()
