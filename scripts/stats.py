"""Render the activity card (contribution heatmap + streaks) for the profile README.

Runs daily in .github/workflows/stats.yml:

    GITHUB_TOKEN=... python scripts/stats.py --user kolbas92 --out dist

For local work without a token, feed it a saved calendar instead:

    python scripts/stats.py --fixture calendar.json --out dist
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta
from html import escape
from pathlib import Path

from theme import MONO, SANS, THEMES, Theme, card_frame, svg_document, text

GRAPHQL_URL = "https://api.github.com/graphql"
QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3,
          "FOURTH_QUARTILE": 4}
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

WIDTH, PAD = 1200, 48
CELL, STEP = 16, 20


@dataclass(frozen=True)
class Day:
    day: date
    count: int
    level: int


@dataclass(frozen=True)
class Summary:
    total: int
    active_days: int
    longest_streak: int
    busiest: Day | None


def parse_calendar(payload: dict) -> list[Day]:
    """Flatten the GraphQL calendar into days, oldest first."""
    try:
        weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    except (KeyError, TypeError) as exc:
        errors = payload.get("errors") if isinstance(payload, dict) else None
        raise ValueError(f"unexpected GraphQL response: {errors or exc!r}") from exc
    days = [
        Day(date.fromisoformat(d["date"]), int(d["contributionCount"]),
            LEVELS.get(d.get("contributionLevel", ""), 0))
        for week in weeks for d in week["contributionDays"]
    ]
    return sorted(days, key=lambda d: d.day)


def fetch_calendar(login: str, token: str) -> list[Day]:
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    request = urllib.request.Request(
        GRAPHQL_URL, data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": f"{login}-profile-stats"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return parse_calendar(json.load(response))


def summarize(days: list[Day]) -> Summary:
    """Totals, the longest run of active days and the busiest day in the calendar window."""
    counts = [d.count for d in days]
    longest = run = 0
    for count in counts:
        run = run + 1 if count > 0 else 0
        longest = max(longest, run)
    return Summary(
        total=sum(counts),
        active_days=sum(1 for c in counts if c > 0),
        longest_streak=longest,
        busiest=max((d for d in days if d.count > 0), key=lambda d: d.count, default=None),
    )


def plural(value: int, word: str) -> str:
    return word if value == 1 else f"{word}s"


def _stat_value(x: float, y: float, value: int, unit: str, t: Theme) -> str:
    """Big number with a small unit trailing it (e.g. "12 days")."""
    suffix = (f'<tspan font-size="20" font-weight="500" fill="{t.muted}"> {escape(unit)}</tspan>'
              if unit else "")
    return (f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="40" font-weight="700" '
            f'letter-spacing="-1" fill="{t.text}">{value}{suffix}</text>')


def _busiest_stat(day: Day | None) -> tuple[int, str, str]:
    if day is None:
        return 0, "", "busiest day"
    return day.count, "", f"busiest day · {MONTHS[day.day.month - 1]} {day.day.day}"


def _weeks(days: list[Day]) -> list[list[Day]]:
    """Group into Sunday-first columns, like GitHub's own calendar."""
    columns: list[list[Day]] = []
    for d in days:
        if not columns or (d.day.weekday() == 6 and columns[-1]):
            columns.append([])
        columns[-1].append(d)
    return columns


def _row(d: date) -> int:
    return (d.weekday() + 1) % 7  # Sunday = 0


def render(days: list[Day], summary: Summary, t: Theme, updated: date) -> str:
    stats = (
        (summary.total, "", "contributions"),
        (summary.active_days, "", "active days"),
        (summary.longest_streak, plural(summary.longest_streak, "day"), "longest streak"),
        _busiest_stat(summary.busiest),
    )
    parts = [
        text(PAD, 62, "ACTIVITY · LAST 12 MONTHS", size=14, fill=t.green, family=MONO,
             weight=600, spacing=3),
        text(WIDTH - PAD, 62, f"updated {updated.isoformat()}", size=14, fill=t.faint,
             family=MONO, anchor="end"),
    ]
    col_w = (WIDTH - 2 * PAD) / len(stats)
    for i, (value, unit, label) in enumerate(stats):
        x = PAD + i * col_w
        accent = t.green_soft if i < 2 else t.purple_soft
        parts.append(f'<rect x="{x}" y="92" width="28" height="4" rx="2" fill="{accent}"/>'
                     + _stat_value(x, 142, value, unit, t)
                     + text(x, 172, label, size=17, fill=t.muted))

    weeks = _weeks(days)
    grid_w = len(weeks) * STEP - (STEP - CELL)
    x0 = WIDTH - PAD - grid_w
    y0 = 240
    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        parts.append(text(x0 - 12, y0 + row * STEP + 12, label, size=13, fill=t.faint,
                          family=MONO, anchor="end"))
    last_label_col = -10
    for c, week in enumerate(weeks):
        first = week[0].day
        month_starts = first.day <= 7 and (c > 0 or first.day == 1)
        if month_starts and c - last_label_col >= 3:
            parts.append(text(x0 + c * STEP, y0 - 12, MONTHS[first.month - 1], size=13,
                              fill=t.faint, family=MONO))
            last_label_col = c
        for d in week:
            parts.append(f'<rect x="{x0 + c * STEP}" y="{y0 + _row(d.day) * STEP}" '
                         f'width="{CELL}" height="{CELL}" rx="4" fill="{t.heat[d.level]}">'
                         f"<title>{d.count} on {d.day.isoformat()}</title></rect>")

    legend_y = y0 + 7 * STEP + 22
    legend_x = WIDTH - PAD - 5 * STEP + (STEP - CELL)
    parts.append(text(legend_x - 12, legend_y + 12, "Less", size=13, fill=t.faint, family=MONO,
                      anchor="end"))
    for i, color in enumerate(t.heat):
        parts.append(f'<rect x="{legend_x + i * STEP}" y="{legend_y}" width="{CELL}" '
                     f'height="{CELL}" rx="4" fill="{color}"/>')
    parts.append(text(legend_x + 5 * STEP + 8, legend_y + 12, "More", size=13, fill=t.faint,
                      family=MONO))

    height = legend_y + CELL + PAD
    return svg_document(WIDTH, height, card_frame(WIDTH, height, t) + "".join(parts),
                        title=f"{summary.total} contributions in the last year")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--user", default="kolbas92")
    parser.add_argument("--out", type=Path, default=Path("dist"))
    parser.add_argument("--fixture", type=Path, help="saved GraphQL response instead of the API")
    args = parser.parse_args(argv)

    if args.fixture:
        days = parse_calendar(json.loads(args.fixture.read_text(encoding="utf-8")))
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print("GITHUB_TOKEN is not set (or pass --fixture)", file=sys.stderr)
            return 2
        days = fetch_calendar(args.user, token)
    if not days:
        print("calendar is empty", file=sys.stderr)
        return 1

    summary = summarize(days)
    args.out.mkdir(parents=True, exist_ok=True)
    updated = days[-1].day
    for t in THEMES:
        (args.out / f"stats-{t.name}.svg").write_text(render(days, summary, t, updated),
                                                      encoding="utf-8")
    print(f"{summary} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
