"""Render the static README graphics into assets/ (light + dark variants).

Run from the repo root after changing copy, numbers or the screenshot:

    python scripts/build_assets.py

Only the stats card changes on its own; it lives in stats.py and is rebuilt
daily by the workflow.
"""

from __future__ import annotations

import base64
import math
import random
import re
from pathlib import Path

from theme import (MONO, REDUCED_MOTION, THEMES, Theme, card_frame, chip, mono_width,
                   svg_document, text)

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ICONS = Path(__file__).resolve().parent / "icons"
SCREENSHOT = ASSETS / "src" / "gig36-map.webp"
SCREENSHOT_SIZE = (1600, 767)

WIDTH = 1200
PAD = 48

GIG36_METRICS = (
    ("243", "ad surfaces"),
    ("31", "cities in 8 regions"),
    ("656", "backend tests"),
    ("55", "DB migrations"),
)
GIG36_STACK = ("Vue 3", "TypeScript", "FastAPI", "PostgreSQL + PostGIS", "SQLAlchemy",
               "Yandex Maps", "1C exchange", "Docker")

HIGHLIGHTS = (
    ("radius", "Radius search on PostGIS",
     ("ST_DWithin over geography: real metres,", "results sorted by actual distance.")),
    ("calendar", "Availability for any period",
     ("The map shows what is free for the client's", "dates, not just what is free today.")),
    ("document", "Documents generated server-side",
     ("Offers in PDF and XLSX, invoices in XLSX,", "DOCX and PDF, file name and format on demand.")),
    ("sync", "Exchange with 1C",
     ("Occupancy and inventory arrive from the", "operator's accounting via the XML exchange plan.")),
)

STACK = (
    ("Backend", "APIs, data, geo", (
        ("python", "Python"), ("fastapi", "FastAPI"), ("postgresql", "PostgreSQL"),
        ("postgis", "PostGIS"), ("sqlalchemy", "SQLAlchemy"))),
    ("Frontend", "apps and dashboards", (
        ("typescript", "TypeScript"), ("vuedotjs", "Vue 3"), ("vite", "Vite"),
        ("pinia", "Pinia"), ("react", "React"))),
    ("Infra & tools", "ship and automate", (
        ("docker", "Docker"), ("caddy", "Caddy"), ("githubactions", "GitHub Actions"),
        ("linux", "Linux"), ("git", "Git"), ("claude", "Claude Code"))),
)

# Line icons on a 24px grid, drawn for this profile (stroke-based).
LINE_ICONS = {
    "radius": '<circle cx="12" cy="12" r="9" stroke-dasharray="3 2.6"/>'
              '<path d="M12 12 19.5 7.5"/><circle cx="12" cy="12" r="1.8" fill="currentColor"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2.5"/>'
                '<path d="M3 10h18M8 3v4M16 3v4M9 15.5l2 2 4-4"/>',
    "document": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
    "sync": '<path d="M20 11a8 8 0 0 0-14.5-4.5L4 8"/><path d="M4 4v4h4"/>'
            '<path d="M4 13a8 8 0 0 0 14.5 4.5L20 16"/><path d="M20 20v-4h-4"/>',
    "postgis": '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/>'
               '<path d="M3.5 9h17M3.5 15h17"/>',
    "external": '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3.5 6.5 8.5 7 8.5-7"/>',
    "book": '<path d="M5 19V6a3 3 0 0 1 3-3h11v14H8a3 3 0 0 0-3 3 2 2 0 0 0 2 2h12v-5"/>'
            '<path d="M9 8h6"/>',
}


def line_icon(name: str, x: float, y: float, size: float, color: str, width: float = 1.8) -> str:
    scale = size / 24
    return (
        f'<g transform="translate({x} {y}) scale({scale:.4f})" fill="none" stroke="{color}" '
        f'color="{color}" stroke-width="{width / scale:.2f}" stroke-linecap="round" '
        f'stroke-linejoin="round">{LINE_ICONS[name]}</g>'
    )


def brand_icon(slug: str, x: float, y: float, size: float, color: str) -> str:
    """Simple Icons glyph (24px viewBox, single path) tinted to the theme."""
    if slug in LINE_ICONS:
        return line_icon(slug, x, y, size, color, width=1.6)
    source = (ICONS / f"{slug}.svg").read_text(encoding="utf-8")
    match = re.search(r'<path d="([^"]+)"', source)
    if match is None:
        raise ValueError(f"icon {slug}.svg has no path")
    return (f'<path transform="translate({x} {y}) scale({size / 24:.4f})" '
            f'fill="{color}" d="{match.group(1)}"/>')


# --------------------------------------------------------------------------- header

PINS_IN = ((1010, 180), (868, 296), (790, 150))
PINS_OUT = ((735, 262), (1120, 140), (1150, 290), (650, 110))
SEARCH_CENTER = (880, 214)
SEARCH_RADIUS = 140


def _sector(cx: float, cy: float, heading: float, spread: float, radius: float) -> str:
    a0, a1 = math.radians(heading - spread / 2), math.radians(heading + spread / 2)
    x0, y0 = cx + radius * math.cos(a0), cy + radius * math.sin(a0)
    x1, y1 = cx + radius * math.cos(a1), cy + radius * math.sin(a1)
    return f"M{cx} {cy} L{x0:.1f} {y0:.1f} A{radius} {radius} 0 0 1 {x1:.1f} {y1:.1f} Z"


def _city_blocks(t: Theme) -> str:
    rng = random.Random(36)
    blocks = []
    for gx in range(560, 1200, 34):
        for gy in range(10, 340, 28):
            if rng.random() < 0.45:
                continue
            w, h = rng.randint(14, 26), rng.randint(10, 18)
            blocks.append(f'<rect x="{gx + rng.randint(0, 6)}" y="{gy + rng.randint(0, 6)}" '
                          f'width="{w}" height="{h}" rx="3"/>')
    return f'<g fill="{t.block}">{"".join(blocks)}</g>'


def _map_motif(t: Theme) -> str:
    roads = (
        ("M540 330 C 740 262, 900 214, 1215 118", 16),
        ("M915 -10 C 896 100, 874 220, 846 350", 13),
        ("M690 -10 L 770 350", 6),
        ("M975 -10 C 1000 120, 1040 240, 1066 350", 6),
        ("M600 125 L 1215 262", 6),
        ("M760 55 L 1215 32", 5),
    )
    road_markup = "".join(
        f'<path d="{d}" stroke="{t.road}" stroke-width="{w}" fill="none" stroke-linecap="round"/>'
        for d, w in roads
    )
    headings = (200, 250, 300, 160, 20, 110, 330)
    sectors = []
    for i, (x, y) in enumerate(PINS_IN + PINS_OUT):
        inside = i < len(PINS_IN)
        color = t.green_soft if inside else t.purple_soft
        sectors.append(f'<path class="sector s{i % 3}" d="{_sector(x, y, headings[i], 54, 74)}" '
                       f'fill="{color}" opacity="{0.30 if inside else 0.18}"/>')
    cx, cy = SEARCH_CENTER
    search = (
        f'<circle cx="{cx}" cy="{cy}" r="{SEARCH_RADIUS}" fill="{t.green_soft}" fill-opacity="0.05"/>'
        f'<circle class="orbit" cx="{cx}" cy="{cy}" r="{SEARCH_RADIUS}" fill="none" '
        f'stroke="{t.green}" stroke-width="2" stroke-dasharray="6 8" opacity="0.8"/>'
        f'<path d="M{cx} {cy} L{cx + SEARCH_RADIUS * 0.82:.0f} {cy + SEARCH_RADIUS * 0.57:.0f}" '
        f'stroke="{t.green}" stroke-width="1.5" stroke-dasharray="2 5" stroke-linecap="round"/>'
        f'<rect x="{cx - 44}" y="{cy - SEARCH_RADIUS - 13}" width="88" height="26" rx="13" '
        f'fill="{t.card}" stroke="{t.green}" stroke-opacity="0.5"/>'
        + text(cx, cy - SEARCH_RADIUS + 5, "r = 5 km", size=14, fill=t.green, family=MONO,
               weight=600, anchor="middle")
        + f'<circle cx="{cx}" cy="{cy}" r="9" fill="none" stroke="{t.green}" stroke-width="2"/>'
        f'<circle cx="{cx}" cy="{cy}" r="3.5" fill="{t.green}"/>'
    )
    pins = []
    for i, (x, y) in enumerate(PINS_IN):
        pins.append(f'<circle class="pulse p{i}" cx="{x}" cy="{y}" r="8" fill="none" '
                    f'stroke="{t.green}" stroke-width="2"/>'
                    f'<circle cx="{x}" cy="{y}" r="7" fill="{t.green}" stroke="{t.card}" stroke-width="3"/>')
    for x, y in PINS_OUT:
        pins.append(f'<circle cx="{x}" cy="{y}" r="6" fill="{t.purple}" stroke="{t.card}" '
                    f'stroke-width="3" opacity="0.85"/>')
    return _city_blocks(t) + road_markup + "".join(sectors) + search + "".join(pins)


def header(t: Theme) -> str:
    w, h = WIDTH, 340
    style = (
        ".pulse{transform-box:fill-box;transform-origin:center;animation:pulse 2.8s ease-out infinite}"
        ".p1{animation-delay:.9s}.p2{animation-delay:1.8s}"
        "@keyframes pulse{0%{transform:scale(1);opacity:.9}100%{transform:scale(3.2);opacity:0}}"
        ".sector{animation:breathe 5s ease-in-out infinite}.s1{animation-delay:1.6s}.s2{animation-delay:3.2s}"
        "@keyframes breathe{50%{opacity:.08}}"
        f".orbit{{animation:orbit 18s linear infinite}}@keyframes orbit{{to{{stroke-dashoffset:-280}}}}"
        + REDUCED_MOTION
    )
    defs = (
        f'<defs><clipPath id="clip"><rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="19"/></clipPath>'
        f'<linearGradient id="fade" x1="540" y1="0" x2="860" y2="0" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff"/>'
        f'</linearGradient><mask id="mask"><rect width="{w}" height="{h}" fill="url(#fade)"/></mask>'
        f'<linearGradient id="rule" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{t.green_soft}"/><stop offset="1" stop-color="{t.purple_soft}"/>'
        f"</linearGradient></defs>"
    )
    body = (
        card_frame(w, h, t)
        + defs
        + f'<g clip-path="url(#clip)"><g mask="url(#mask)">{_map_motif(t)}</g></g>'
        + text(PAD + 16, 100, "BACKEND · FULLSTACK", size=15, fill=t.green, family=MONO,
               weight=600, spacing=3)
        + text(PAD + 14, 168, "Artem Nizgirev", size=60, fill=t.text, weight=700, spacing=-1)
        + f'<rect x="{PAD + 16}" y="190" width="72" height="4" rx="2" fill="url(#rule)"/>'
        + text(PAD + 16, 236, "I build web products end to end:", size=24, fill=t.muted)
        + text(PAD + 16, 268, "from PostGIS queries to the UI on top.", size=24, fill=t.muted)
        + text(PAD + 16, 300, "FastAPI · PostgreSQL · Vue 3 · TypeScript", size=15,
               fill=t.faint, family=MONO)
    )
    return svg_document(w, h, body, title="Artem Nizgirev — backend and fullstack developer",
                        style=style)


# --------------------------------------------------------------------------- GIG36 card

def _screenshot_data_uri() -> str:
    encoded = base64.b64encode(SCREENSHOT.read_bytes()).decode("ascii")
    return f"data:image/webp;base64,{encoded}"


def _browser_frame(t: Theme, x: float, y: float, w: float) -> tuple[str, float]:
    bar = 40
    img_w, img_h = SCREENSHOT_SIZE
    shot_h = w * img_h / img_w
    total = bar + shot_h
    dots = "".join(f'<circle cx="{x + 22 + i * 18}" cy="{y + bar / 2}" r="5" fill="{t.border}"/>'
                   for i in range(3))
    url_w = 220
    url_x = x + (w - url_w) / 2
    markup = (
        f'<defs><clipPath id="shot"><rect x="{x}" y="{y}" width="{w}" height="{total:.1f}" rx="14"/>'
        f"</clipPath></defs>"
        f'<g clip-path="url(#shot)">'
        f'<rect x="{x}" y="{y}" width="{w}" height="{bar}" fill="{t.raised}"/>{dots}'
        f'<rect x="{url_x}" y="{y + 9}" width="{url_w}" height="22" rx="11" fill="{t.card}" stroke="{t.border}"/>'
        + text(url_x + url_w / 2, y + 25, "gig36.ru", size=13, fill=t.muted, family=MONO, anchor="middle")
        + f'<image x="{x}" y="{y + bar}" width="{w}" height="{shot_h:.1f}" '
        f'preserveAspectRatio="xMidYMid slice" href="{_screenshot_data_uri()}"/>'
        f"</g>"
        f'<rect x="{x + 0.5}" y="{y + 0.5}" width="{w - 1}" height="{total - 1:.1f}" rx="14" '
        f'fill="none" stroke="{t.border}"/>'
    )
    return markup, total


def _status_pill(t: Theme, right: float, y: float) -> str:
    label = "LIVE IN PRODUCTION"
    w = mono_width(label, 13) + 52
    x = right - w
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="32" rx="16" fill="{t.green_soft}" '
        f'fill-opacity="0.12" stroke="{t.green_soft}" stroke-opacity="0.45"/>'
        f'<circle class="live" cx="{x + 20}" cy="{y + 16}" r="5" fill="{t.green}"/>'
        f'<circle cx="{x + 20}" cy="{y + 16}" r="5" fill="{t.green}"/>'
        + text(x + 34, y + 21, label, size=13, fill=t.green, family=MONO, weight=600, spacing=1)
    )


def gig36_card(t: Theme) -> str:
    w = WIDTH
    inner = w - 2 * PAD
    frame, frame_h = _browser_frame(t, PAD, 188, inner)
    metrics_y = 188 + frame_h + 44
    metrics = []
    col = inner / len(GIG36_METRICS)
    for i, (value, label) in enumerate(GIG36_METRICS):
        x = PAD + i * col
        accent = t.green_soft if i < 2 else t.purple_soft
        metrics.append(
            f'<rect x="{x}" y="{metrics_y:.1f}" width="28" height="4" rx="2" fill="{accent}"/>'
            + text(x, metrics_y + 54, value, size=44, fill=t.text, weight=700, spacing=-1)
            + text(x, metrics_y + 86, label, size=17, fill=t.muted)
        )
    chips_y = metrics_y + 124
    chips, cx = [], PAD
    for label in GIG36_STACK:
        markup, cw = chip(cx, chips_y, label, t)
        chips.append(markup)
        cx += cw + 10
    h = int(chips_y + 33 + PAD)
    style = (".live{transform-box:fill-box;transform-origin:center;animation:live 2.2s ease-out infinite}"
             "@keyframes live{0%{transform:scale(1);opacity:.8}100%{transform:scale(3);opacity:0}}"
             + REDUCED_MOTION)
    body = (
        card_frame(w, h, t)
        + text(PAD, 72, "FEATURED PROJECT", size=14, fill=t.green, family=MONO, weight=600, spacing=3)
        + _status_pill(t, w - PAD, 50)
        + text(PAD - 2, 128, "GIG36", size=46, fill=t.text, weight=700, spacing=-1)
        + text(PAD, 160, "Booking platform for an outdoor advertising operator — "
               "map, online booking, client and staff dashboards.", size=19, fill=t.muted)
        + frame
        + "".join(metrics)
        + "".join(chips)
    )
    return svg_document(w, h, body, title="GIG36 — outdoor advertising booking platform", style=style)


# --------------------------------------------------------------------------- highlights

def highlights(t: Theme) -> str:
    w = WIDTH
    tile_w, tile_h, gap = (w - 2 * PAD - 24) / 2, 132, 24
    top = 96
    tiles = []
    for i, (icon, title, lines) in enumerate(HIGHLIGHTS):
        x = PAD + (i % 2) * (tile_w + gap)
        y = top + (i // 2) * (tile_h + gap)
        accent = t.green if i in (0, 3) else t.purple
        tiles.append(
            f'<rect x="{x}" y="{y}" width="{tile_w}" height="{tile_h}" rx="14" fill="{t.raised}" stroke="{t.border}"/>'
            f'<rect x="{x + 24}" y="{y + 24}" width="48" height="48" rx="12" fill="{accent}" fill-opacity="0.12"/>'
            + line_icon(icon, x + 34, y + 34, 28, accent)
            + text(x + 92, y + 48, title, size=21, fill=t.text, weight=600)
            + "".join(text(x + 92, y + 80 + j * 25, line, size=17, fill=t.muted)
                      for j, line in enumerate(lines))
        )
    h = int(top + 2 * tile_h + gap + PAD)
    body = (
        card_frame(w, h, t)
        + text(PAD, 62, "UNDER THE HOOD", size=14, fill=t.green, family=MONO, weight=600, spacing=3)
        + "".join(tiles)
    )
    return svg_document(w, h, body, title="GIG36 engineering highlights")


# --------------------------------------------------------------------------- stack

def stack(t: Theme) -> str:
    w = WIDTH
    top, row_h = 92, 134
    rows = []
    for r, (title, caption, items) in enumerate(STACK):
        y = top + r * row_h
        if r:
            rows.append(f'<path d="M{PAD} {y - 14} H{w - PAD}" stroke="{t.border}"/>')
        rows.append(text(PAD, y + 42, title, size=21, fill=t.text, weight=600)
                    + text(PAD, y + 70, caption, size=15, fill=t.faint, family=MONO))
        for i, (slug, label) in enumerate(items):
            x = 290 + i * 146
            rows.append(
                f'<rect x="{x}" y="{y + 4}" width="64" height="64" rx="16" fill="{t.raised}" stroke="{t.border}"/>'
                + brand_icon(slug, x + 17, y + 21, 30, t.text)
                + text(x + 32, y + 98, label, size=16, fill=t.muted, anchor="middle")
            )
    h = int(top + len(STACK) * row_h + 8)
    body = (card_frame(w, h, t)
            + text(PAD, 58, "TOOLBOX", size=14, fill=t.green, family=MONO, weight=600, spacing=3)
            + "".join(rows))
    return svg_document(w, h, body, title="Tech stack")


# --------------------------------------------------------------------------- buttons

# Buttons sit inside links, and GitHub's sanitizer detaches <picture> sources from
# linked images — so each button is a single file that reads on both themes.
BUTTONS = (
    ("live", "gig36.ru", "external", "#16a34a"),
    ("case", "Case study", "book", "#7c3aed"),
    ("email", "Email", "mail", "#2f353d"),
)


def button(label: str, icon: str, fill: str) -> str:
    size, h = 15, 44
    w = int(len(label) * size * 0.62 + 74)
    body = (
        f'<rect width="{w}" height="{h}" rx="{h / 2}" fill="{fill}"/>'
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="{h / 2 - 0.5}" fill="none" '
        f'stroke="#ffffff" stroke-opacity="0.14"/>'
        + line_icon(icon, 20, 13, 18, "#ffffff", width=2)
        + text(46, 27.5, label, size=size, fill="#ffffff", weight=600)
    )
    return svg_document(w, h, body, title=label)


# --------------------------------------------------------------------------- main

def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    builders = {"header": header, "gig36": gig36_card, "highlights": highlights, "stack": stack}
    for t in THEMES:
        for name, build in builders.items():
            (ASSETS / f"{name}-{t.name}.svg").write_text(build(t), encoding="utf-8")
    for key, label, icon, fill in BUTTONS:
        (ASSETS / f"btn-{key}.svg").write_text(button(label, icon, fill), encoding="utf-8")
    for path in sorted(ASSETS.glob("*.svg")):
        print(f"{path.name:28} {path.stat().st_size / 1024:7.1f} KB")


if __name__ == "__main__":
    main()
