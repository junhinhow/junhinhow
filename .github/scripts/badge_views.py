#!/usr/bin/env python3
"""Render media/badge-views.svg so the profile views badge stops depending on
GitHub's camo proxy being able to reach komarev.com.

Why: camo caches komarev's intermittent 503s as a permanent 404, which is what
left the profile showing a broken image. Images served from
raw.githubusercontent.com for this same account skip camo entirely, so hosting
the badge in media/ makes it fail-proof.

The count is still read from komarev (the authoritative profile-views counter)
and refreshed by .github/workflows/badges.yml. If komarev is unreachable we
keep the last known value instead of writing a broken badge.

Usage:
    python3 .github/scripts/badges.py
"""

from __future__ import annotations

import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

VIEWS_URL = (
    "https://komarev.com/ghpvc/?username=junhinhow"
    "&label=Profile%20Views&color=16A34A&style=for-the-badge"
)
LABEL_BG = "#555555"
VALUE_BG = "#16A34A"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "media" / "badge-views.svg"


def fetch(url: str, retries: int = 4) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as error:  # noqa: PERF203
            last = error
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"komarev unreachable: {last}")


def count_from(svg: str) -> str | None:
    match = re.search(r"PROFILE VIEWS:\s*(\d+)", svg)
    if not match:
        match = re.search(r">\s*(\d+)\s*</text>", svg)
    return match.group(1) if match else None


def previous() -> str | None:
    if not OUT.exists():
        return None
    match = re.search(r">\s*(\d+)\s*</text>", OUT.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def badge(count: str) -> str:
    label, value = "PROFILE VIEWS", count
    left = round(len(label) * 7.2 + 21, 2)
    right = round(len(value) * 7.2 + 21, 2)
    width = round(left + right, 2)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="28" '
        f'role="img" aria-label="PROFILE VIEWS: {count}">\n'
        f"  <title>PROFILE VIEWS: {count}</title>\n"
        '  <g shape-rendering="crispEdges">\n'
        f'    <rect width="{left}" height="28" fill="{LABEL_BG}"/>\n'
        f'    <rect x="{left}" width="{right}" height="28" fill="{VALUE_BG}"/>\n'
        "  </g>\n"
        '  <g fill="#ffffff" text-anchor="middle" '
        'font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="10" '
        'font-weight="bold" letter-spacing="1.1" text-rendering="geometricPrecision">\n'
        f'    <text x="{round(left / 2, 2)}" y="18">{label}</text>\n'
        f'    <text x="{round(left + right / 2, 2)}" y="18">{value}</text>\n'
        "  </g>\n"
        "</svg>\n"
    )


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cached = previous()
    try:
        count = count_from(fetch(VIEWS_URL).decode("utf-8", "replace")) or cached
    except RuntimeError as error:
        print(error, file=sys.stderr)
        count = cached
    if not count:
        print("no count available and no previous badge to keep", file=sys.stderr)
        return 1

    badge_svg = badge(count)
    if OUT.exists() and OUT.read_text(encoding="utf-8") == badge_svg:
        print(f"badge unchanged: {count} views")
        return 0
    OUT.write_text(badge_svg, encoding="utf-8")
    print(f"badge updated: {count} views")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
