"""Shared palette and SVG helpers for the profile README graphics.

Every asset is rendered twice — once per GitHub colour scheme — and the README
picks the right one with <picture> + prefers-color-scheme.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"


@dataclass(frozen=True)
class Theme:
    name: str
    card: str
    card_edge: str
    raised: str
    border: str
    text: str
    muted: str
    faint: str
    green: str
    green_soft: str
    purple: str
    purple_soft: str
    road: str
    block: str
    heat: tuple[str, str, str, str, str]


DARK = Theme(
    name="dark",
    card="#0f141b",
    card_edge="#151b24",
    raised="#161d27",
    border="#262d38",
    text="#e6edf3",
    muted="#9198a1",
    faint="#5d6571",
    green="#4ade80",
    green_soft="#22c55e",
    purple="#a78bfa",
    purple_soft="#8b5cf6",
    road="#222a35",
    block="#1a212b",
    heat=("#1a212b", "#14532d", "#15803d", "#22c55e", "#86efac"),
)

LIGHT = Theme(
    name="light",
    card="#ffffff",
    card_edge="#f6f8fa",
    raised="#f6f8fa",
    border="#d1d9e0",
    text="#1f2328",
    muted="#59636e",
    faint="#8c959f",
    green="#15803d",
    green_soft="#16a34a",
    purple="#7c3aed",
    purple_soft="#8b5cf6",
    road="#e6eaef",
    block="#eef1f4",
    heat=("#eef1f4", "#bbf7d0", "#4ade80", "#16a34a", "#166534"),
)

THEMES = (DARK, LIGHT)


def text(x: float, y: float, content: str, *, size: int, fill: str, weight: int = 400,
         family: str = SANS, anchor: str = "start", spacing: float = 0, extra: str = "") -> str:
    """A single <text> element; content is escaped."""
    letter = f' letter-spacing="{spacing}"' if spacing else ""
    return (
        f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}"{letter}{extra}>{escape(content)}</text>'
    )


def mono_width(content: str, size: int) -> float:
    """Monospace glyphs are ~0.6em wide in every stack we fall back to."""
    return len(content) * size * 0.6


def chip(x: float, y: float, label: str, t: Theme, *, size: int = 15) -> tuple[str, float]:
    """A pill-shaped tag; returns the markup and its width so callers can flow them."""
    width = mono_width(label, size) + 28
    height = size + 18
    markup = (
        f'<rect x="{x}" y="{y}" width="{width:.1f}" height="{height}" rx="{height / 2}" '
        f'fill="{t.raised}" stroke="{t.border}"/>'
        + text(x + width / 2, y + height / 2 + size * 0.35, label, size=size, fill=t.muted,
               family=MONO, anchor="middle")
    )
    return markup, width


def svg_document(width: int, height: int, body: str, *, title: str, style: str = "") -> str:
    css = f"<style>{style}</style>" if style else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">'
        f"<title>{escape(title)}</title>{css}{body}</svg>\n"
    )


def card_frame(width: int, height: int, t: Theme, *, radius: int = 20) -> str:
    """Rounded card with a soft top-down fill and a hairline border."""
    gid = f"card-{t.name}"
    return (
        f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{t.card}"/><stop offset="1" stop-color="{t.card_edge}"/>'
        f"</linearGradient></defs>"
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="{radius}" '
        f'fill="url(#{gid})" stroke="{t.border}"/>'
    )


REDUCED_MOTION = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
