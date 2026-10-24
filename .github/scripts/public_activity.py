#!/usr/bin/env python3
"""Render a public GitHub activity card for the profile README.

This deliberately reports public GitHub activity, not coding time. GitHub's
public REST events API does not expose the amount of time spent coding.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

OWNER = "junhinhow"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "media" / "public-activity.svg"
GREEN = "#16A34A"
DARK_GREEN = "#15803D"
TEXT = "#C9D1D9"
MUTED = "#8B949E"
PANEL = "#161B22"
GRID = "#30363D"


def fetch_events(token: str) -> list[dict]:
    events: list[dict] = []
    for page in range(1, 11):
        query = urllib.parse.urlencode({"per_page": 100, "page": page})
        request = urllib.request.Request(
            f"https://api.github.com/users/{OWNER}/events/public?{query}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "junhinhow-profile-activity",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            batch = json.load(response)
        if not batch:
            break
        events.extend(batch)
        if len(batch) < 100:
            break
    return events


def count_activity(events: list[dict], now: datetime) -> dict[str, int]:
    since = now - timedelta(days=30)
    days: set[str] = set()
    repositories: set[str] = set()
    commits = pull_requests = issues = interactions = 0

    for event in events:
        created = event.get("created_at")
        if not created:
            continue
        timestamp = datetime.fromisoformat(created.replace("Z", "+00:00"))
        if timestamp < since:
            continue

        days.add(timestamp.date().isoformat())
        repo = event.get("repo", {}).get("name")
        if repo:
            repositories.add(repo)

        event_type = event.get("type")
        payload = event.get("payload", {})
        if event_type == "PushEvent":
            commits += len(payload.get("commits", []))
        elif event_type == "PullRequestEvent":
            pull_requests += 1
        elif event_type == "IssuesEvent":
            issues += 1
        elif event_type in {"IssueCommentEvent", "PullRequestReviewEvent"}:
            interactions += 1

    return {
        "commits": commits,
        "pull_requests": pull_requests,
        "issues": issues,
        "interactions": interactions,
        "repositories": len(repositories),
        "active_days": len(days),
    }


def esc(value: object) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(stats: dict[str, int]) -> str:
    rows = [
        ("Commits públicos", stats["commits"]),
        ("Pull requests", stats["pull_requests"]),
        ("Issues", stats["issues"]),
        ("Interações", stats["interactions"]),
        ("Repositórios ativos", stats["repositories"]),
        ("Dias ativos", stats["active_days"]),
    ]
    max_value = max((value for _, value in rows), default=1) or 1
    width = 760
    bar_x = 220
    bar_width = 410
    row_height = 35
    height = 92 + len(rows) * row_height

    body = []
    for index, (label, value) in enumerate(rows):
        y = 91 + index * row_height
        fill = round(bar_width * value / max_value) if value else 0
        body.append(
            f'  <text x="28" y="{y}" fill="{TEXT}" font-size="14">{esc(label)}</text>\n'
            f'  <rect x="{bar_x}" y="{y - 14}" width="{bar_width}" height="16" rx="8" fill="{GRID}"/>\n'
            f'  <rect x="{bar_x}" y="{y - 14}" width="{fill}" height="16" rx="8" fill="{GREEN}"/>\n'
            f'  <text x="{bar_x + bar_width + 18}" y="{y}" fill="{TEXT}" font-size="14" font-weight="bold">{value}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Atividade pública no GitHub nos últimos 30 dias">
  <title>Atividade pública no GitHub — últimos 30 dias</title>
  <rect width="100%" height="100%" rx="12" fill="{PANEL}" stroke="{GRID}"/>
  <text x="28" y="35" fill="{TEXT}" font-family="Verdana, sans-serif" font-size="19" font-weight="bold">📊 Atividade pública no GitHub</text>
  <text x="28" y="60" fill="{MUTED}" font-family="Verdana, sans-serif" font-size="12">Últimos 30 dias · dados públicos · atualizado diariamente</text>
{chr(10).join(body)}
  <text x="28" y="{height - 12}" fill="{MUTED}" font-family="Verdana, sans-serif" font-size="11">Não representa horas de programação; mede atividade pública registrada pelo GitHub.</text>
</svg>
'''


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("GITHUB_TOKEN é obrigatório", file=sys.stderr)
        return 1

    try:
        stats = count_activity(fetch_events(token), datetime.now(timezone.utc))
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
        print(f"não foi possível ler os eventos públicos: {error}", file=sys.stderr)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(stats), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
