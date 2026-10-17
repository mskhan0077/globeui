"""Static SVG charts for the PDF report (WeasyPrint can't run Plotly).

Light print theme, same technology colours as the planner (theme.js); the
palette is validated for a white surface. Values in the charts also appear in
the report's tables, so identity never relies on colour alone.
"""
from __future__ import annotations

import math
from html import escape

# Technology order and colours, matching the planner.
TECHS = [
    {"key": "wind", "name": "Wind", "score_key": "Wind", "cap": "wind_kW", "color": "#3987e5"},
    {"key": "fpv", "name": "Floating solar", "score_key": "Floating Solar PV", "cap": "solar_kWp", "color": "#d95926"},
    {"key": "otec", "name": "OTEC", "score_key": "OTEC", "cap": "otec_kW", "color": "#199e70"},
    {"key": "wave", "name": "Wave", "score_key": "Wave", "cap": "wave_kW", "color": "#c98500"},
]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

INK = "#1c2733"
MUTED = "#6b7a8c"
GRID = "#e3e9ef"
SURFACE = "#ffffff"


def nice_ticks(vmax: float, target: int = 5) -> list[float]:
    """0..top in 1/2/2.5/5 × 10^k steps, about `target` intervals."""
    if vmax <= 0:
        return [0.0, 1.0]
    raw = vmax / target
    mag = 10 ** math.floor(math.log10(raw))
    step = next(s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw)
    top = math.ceil(vmax / step - 1e-9) * step
    return [round(i * step, 10) for i in range(int(round(top / step)) + 1)]


def _fmt_tick(v: float) -> str:
    return f"{v:,.0f}" if v >= 10 or v == int(v) else f"{v:g}"


def _rounded_top(x: float, y: float, w: float, h: float, r: float) -> str:
    """Path of a bar segment with rounded top corners (the stack's data end)."""
    r = min(r, w / 2, h)
    return (f"M{x:.2f},{y + h:.2f} V{y + r:.2f} Q{x:.2f},{y:.2f} {x + r:.2f},{y:.2f} "
            f"H{x + w - r:.2f} Q{x + w:.2f},{y:.2f} {x + w:.2f},{y + r:.2f} V{y + h:.2f} Z")


def monthly_balance_svg(monthly: list[dict], width: int = 680, height: int = 250) -> str:
    """Stacked monthly generation by technology (MWh) with the demand as a dashed step line."""
    left, right, top, bottom = 52, 14, 34, 24
    pw, ph = width - left - right, height - top - bottom

    rows = sorted(monthly, key=lambda m: m["month_num"])[:12]
    gen = [[m.get(f"gen_{t['key']}_kWh", 0.0) / 1000 for t in TECHS] for m in rows]
    load = [m["load_kWh"] / 1000 for m in rows]
    ticks = nice_ticks(max([sum(g) for g in gen] + load + [1e-9]))
    ymax = ticks[-1]

    def y(v: float) -> float:
        return top + ph * (1 - v / ymax)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
           f'width="{width}" height="{height}" font-family="Inter, Helvetica, Arial, sans-serif">']

    # Legend (top-left): technologies, then the dashed demand line.
    lx = left
    for t in TECHS:
        out.append(f'<rect x="{lx}" y="8" width="10" height="10" rx="2" fill="{t["color"]}"/>'
                   f'<text x="{lx + 15}" y="17" font-size="10" fill="{INK}">{escape(t["name"])}</text>')
        lx += 15 + 5.6 * len(t["name"]) + 14
    out.append(f'<line x1="{lx}" y1="13" x2="{lx + 18}" y2="13" stroke="{INK}" stroke-width="2" stroke-dasharray="4 3"/>'
               f'<text x="{lx + 23}" y="17" font-size="10" fill="{INK}">Demand</text>')

    # Recessive grid + y axis labels.
    for v in ticks:
        out.append(f'<line x1="{left}" y1="{y(v):.2f}" x2="{width - right}" y2="{y(v):.2f}" '
                   f'stroke="{GRID}" stroke-width="{1.2 if v == 0 else 0.8}"/>'
                   f'<text x="{left - 6}" y="{y(v) + 3:.2f}" font-size="9" fill="{MUTED}" text-anchor="end">{_fmt_tick(v)}</text>')
    out.append(f'<text x="12" y="{top + ph / 2:.2f}" font-size="9" fill="{MUTED}" text-anchor="middle" '
               f'transform="rotate(-90 12 {top + ph / 2:.2f})">MWh</text>')

    # Bars: 2 px surface gap between stacked segments, rounded top on the stack.
    slot = pw / max(len(rows), 1)
    bw = slot * 0.58
    for i, g in enumerate(gen):
        x = left + i * slot + (slot - bw) / 2
        segs = [(v, t["color"]) for v, t in zip(g, TECHS) if v > 0]
        base = 0.0
        for j, (v, color) in enumerate(segs):
            y0, y1 = y(base + v), y(base)
            h = max(y1 - y0 - (2 if j else 0), 0.3)  # gap above the segment below
            if j == len(segs) - 1:
                out.append(f'<path d="{_rounded_top(x, y0, bw, h, 3)}" fill="{color}"/>')
            else:
                out.append(f'<rect x="{x:.2f}" y="{y0:.2f}" width="{bw:.2f}" height="{h:.2f}" fill="{color}"/>')
            base += v
        out.append(f'<text x="{x + bw / 2:.2f}" y="{height - 8}" font-size="9" fill="{MUTED}" '
                   f'text-anchor="middle">{MONTHS[int(rows[i]["month_num"]) - 1]}</text>')

    # Demand: a step line across each month's slot (hours differ by month), with a halo.
    d = " ".join(f"{'M' if i == 0 else 'L'}{left + i * slot:.2f},{y(v):.2f} H{left + (i + 1) * slot:.2f}"
                 for i, v in enumerate(load))
    out.append(f'<path d="{d}" fill="none" stroke="{SURFACE}" stroke-width="4" stroke-linejoin="round"/>'
               f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="2" stroke-dasharray="5 3" stroke-linejoin="round"/>')

    out.append("</svg>")
    return "".join(out)
