"""Generate compact, responsive GitHub-green activity SVGs."""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "generated"
PRIMARY = "#f0f6fc"
SECONDARY = "#8b949e"
MUTED = "#6e7681"
EMPTY = "#21262d"
GREEN_1 = "#0e4429"
GREEN_2 = "#006d32"
GREEN_3 = "#26a641"
GREEN_4 = "#39d353"
FONT = "Consolas,DejaVu Sans Mono,monospace"


def get_json(url: str, token: str, payload: dict | None = None):
    request = urllib.request.Request(url, data=json.dumps(payload).encode() if payload else None)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("User-Agent", "irohankumars-profile")
    if payload:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def calendar(token: str, username: str, year: int, end: dt.date) -> dict:
    query = """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){contributionsCollection(from:$from,to:$to){contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""
    variables = {
        "login": username,
        "from": dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc).isoformat(),
        "to": dt.datetime.combine(end, dt.time.max, tzinfo=dt.timezone.utc).isoformat(),
    }
    result = get_json("https://api.github.com/graphql", token, {"query": query, "variables": variables})
    if result.get("errors"):
        raise RuntimeError(result["errors"][0]["message"])
    return result["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def activity(token: str, username: str) -> tuple[list[dict], int]:
    profile = get_json(f"https://api.github.com/users/{username}", token)
    today = dt.datetime.now(dt.timezone.utc).date()
    first = dt.date.fromisoformat(profile["created_at"][:10]).year
    days, total = [], 0
    for year in range(first, today.year + 1):
        data = calendar(token, username, year, today if year == today.year else dt.date(year, 12, 31))
        total += data["totalContributions"]
        days += [day for week in data["weeks"] for day in week["contributionDays"]]
    return days, total


def languages(token: str, username: str) -> Counter:
    totals, page = Counter(), 1
    while True:
        repos = get_json(
            f"https://api.github.com/users/{username}/repos?type=owner&sort=pushed&per_page=100&page={page}", token
        )
        for repo in repos:
            if not repo["fork"] and not repo.get("archived"):
                totals.update(get_json(repo["languages_url"], token))
        if len(repos) < 100:
            return totals
        page += 1


def streaks(days: list[dict]) -> tuple[int, int]:
    counts = {dt.date.fromisoformat(day["date"]): day["contributionCount"] for day in days}
    today = dt.datetime.now(dt.timezone.utc).date()
    cursor = today if counts.get(today, 0) else today - dt.timedelta(days=1)
    current = 0
    while counts.get(cursor, 0):
        current, cursor = current + 1, cursor - dt.timedelta(days=1)
    longest = run = 0
    for day in sorted(counts):
        run = run + 1 if counts[day] else 0
        longest = max(longest, run)
    return current, longest


def text(x, y, value, size=18, color=PRIMARY, anchor="start", weight=None) -> str:
    weight_attr = f' font-weight="{weight}"' if weight else ""
    return (
        f'<text x="{x}" y="{y}" fill="{color}" text-anchor="{anchor}" '
        f'font-family="{FONT}" font-size="{size}"{weight_attr}>{html.escape(str(value))}</text>'
    )


def svg(title: str, body: list[str], width: int, height: int) -> str:
    safe_title = html.escape(title.upper())
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{safe_title}" viewBox="0 0 {width} {height}">',
        text(24, 29, safe_title, 16, MUTED, weight="600"),
        *body,
        "</svg>",
    ]
    return "\n".join(parts) + "\n"


def weekly_color(ratio: float, empty: bool = False) -> str:
    if empty:
        return EMPTY
    if ratio < 0.34:
        return GREEN_1
    if ratio < 0.72:
        return GREEN_3
    return GREEN_4


def write_stats(total, recent, ratios: list[float], empty: list[bool] | None = None) -> None:
    empty = empty or [False] * len(ratios)
    body = [
        text(32, 92, total, 54, PRIMARY, weight="600"),
        text(34, 121, "lifetime public", 18, SECONDARY),
        text(34, 143, "contributions", 18, SECONDARY),
        text(368, 92, recent, 54, GREEN_4, weight="600"),
        text(370, 121, "last 7 days", 18, SECONDARY),
    ]
    base_y, max_height = 230, 66
    for index, ratio in enumerate(ratios):
        height = 3 if empty[index] else max(7, round(max_height * ratio))
        body.append(
            f'<rect x="{27 + index * 54}" y="{base_y - height}" width="36" height="{height}" '
            f'rx="3" fill="{weekly_color(ratio, empty[index])}"/>'
        )
    (OUT / "stats.svg").write_bytes(svg("Contribution record / 12-week pulse", body, 680, 245).encode("utf-8"))


def write_streak(current, longest) -> None:
    body = [
        text(34, 96, current, 56, GREEN_4, weight="600"),
        text(36, 128, "current days", 19, SECONDARY),
        '<line x1="36" y1="145" x2="184" y2="145" stroke="#26a641" stroke-width="3"/>',
        text(370, 96, longest, 56, GREEN_4, weight="600"),
        text(372, 128, "longest days", 19, SECONDARY),
        '<line x1="372" y1="145" x2="520" y2="145" stroke="#26a641" stroke-width="3"/>',
    ]
    (OUT / "streak.svg").write_bytes(svg("Working rhythm", body, 680, 165).encode("utf-8"))


def write_languages(items: list[tuple[str, float]]) -> None:
    colors = (GREEN_3, GREEN_2, GREEN_1, GREEN_1, GREEN_1, GREEN_1)
    body = []
    for index, (name, percent) in enumerate(items[:6]):
        y = 67 + index * 30
        body.extend(
            [
                text(24, y, name, 18),
                text(276, y, f"{percent:4.1f}%", 17, SECONDARY, "end"),
                f'<rect x="300" y="{y - 14}" width="{max(5, round(340 * percent / 100))}" '
                f'height="13" rx="3" fill="{colors[index]}"/>',
            ]
        )
    (OUT / "languages.svg").write_bytes(svg("Repository language mix", body, 680, 240).encode("utf-8"))


def write_year(cells: list[tuple[int, str, bool]], footer: str) -> None:
    weeks = max(1, (len(cells) + 6) // 7)
    width = max(360, 40 + weeks * 15)
    body = []
    for index, (weekday, color, is_empty) in enumerate(cells):
        week = index // 7
        opacity = ' fill-opacity="0.45"' if is_empty else ""
        body.append(
            f'<rect x="{22 + week * 15}" y="{48 + weekday * 15}" width="11" height="11" '
            f'rx="2" fill="{color}"{opacity}/>'
        )
    body.append(text(24, 178, footer, 18, SECONDARY))
    (OUT / "year.svg").write_bytes(svg("Year / daily trace", body, width, 192).encode("utf-8"))


def placeholders() -> None:
    body = [
        text(24, 82, "activity will appear after the first workflow run", 18),
        text(24, 112, "run locally with GITHUB_TOKEN to populate", 16, SECONDARY),
    ]
    for name, title in (
        ("stats.svg", "GitHub activity"),
        ("streak.svg", "Streaks"),
        ("languages.svg", "Languages"),
        ("year.svg", "Year in commits"),
    ):
        (OUT / name).write_bytes(svg(title, body, 680, 150).encode("utf-8"))


def render(days: list[dict], total: int, langs: Counter) -> None:
    today = dt.datetime.now(dt.timezone.utc).date()
    recent = sum(
        day["contributionCount"]
        for day in days
        if dt.date.fromisoformat(day["date"]) > today - dt.timedelta(days=7)
    )
    weeks = []
    for offset in range(11, -1, -1):
        end = today - dt.timedelta(days=offset * 7)
        start = end - dt.timedelta(days=6)
        weeks.append(
            sum(
                day["contributionCount"]
                for day in days
                if start <= dt.date.fromisoformat(day["date"]) <= end
            )
        )
    scale = max(weeks) or 1
    write_stats(f"{total:,}", recent, [value / scale for value in weeks], [value == 0 for value in weeks])

    current, longest = streaks(days)
    write_streak(current, longest)

    total_bytes = sum(langs.values()) or 1
    write_languages([(name, amount / total_bytes * 100) for name, amount in langs.most_common(6)])

    current_year = [day for day in days if day["date"].startswith(str(today.year))]
    cells = []
    for day in current_year:
        count = day["contributionCount"]
        color = EMPTY if count == 0 else GREEN_1 if count < 2 else GREEN_2 if count < 4 else GREEN_3 if count < 7 else GREEN_4
        cells.append((dt.date.fromisoformat(day["date"]).weekday(), color, count == 0))
    year_total = sum(day["contributionCount"] for day in current_year)
    write_year(cells, f"{year_total:,} contributions in {today.year}")


def restyle_existing() -> None:
    """Reflow current SVG data without recalculating values from GitHub."""
    namespace = {"svg": "http://www.w3.org/2000/svg"}

    stats_root = ET.parse(OUT / "stats.svg").getroot()
    stats_text = [node.text or "" for node in stats_root.findall("svg:text", namespace)]
    stats_rects = stats_root.findall("svg:rect", namespace)
    heights = [float(node.get("height", "0")) for node in stats_rects]
    scale = max(heights) or 1
    write_stats(stats_text[1], stats_text[3], [height / scale for height in heights], [height <= 3 for height in heights])

    streak_root = ET.parse(OUT / "streak.svg").getroot()
    streak_text = [node.text or "" for node in streak_root.findall("svg:text", namespace)]
    write_streak(streak_text[1], streak_text[3])

    language_root = ET.parse(OUT / "languages.svg").getroot()
    language_text = [node.text or "" for node in language_root.findall("svg:text", namespace)][1:]
    items = []
    for index in range(0, len(language_text), 2):
        items.append((language_text[index], float(language_text[index + 1].strip().rstrip("%"))))
    write_languages(items)

    year_root = ET.parse(OUT / "year.svg").getroot()
    year_rects = year_root.findall("svg:rect", namespace)
    y_values = sorted({float(node.get("y", "0")) for node in year_rects})
    y_to_weekday = {value: index for index, value in enumerate(y_values)}
    cells = [
        (
            y_to_weekday[float(node.get("y", "0"))],
            node.get("fill", EMPTY),
            node.get("fill") == EMPTY or node.get("fill-opacity") is not None,
        )
        for node in year_rects
    ]
    footer = [node.text or "" for node in year_root.findall("svg:text", namespace)][-1]
    write_year(cells, footer)
    print("Reflowed existing activity graphics without changing their displayed data.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default=os.getenv("GITHUB_REPOSITORY_OWNER", "irohankumars"))
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--restyle-existing", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.restyle_existing:
        restyle_existing()
        return
    if not args.token:
        print("GITHUB_TOKEN not set; writing first-run placeholders.")
        placeholders()
        return
    try:
        days, total = activity(args.token, args.username)
        render(days, total, languages(args.token, args.username))
    except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError, KeyError) as error:
        raise SystemExit(f"GitHub data generation failed: {error}") from error
    print(f"Updated activity graphics for {args.username}.")


if __name__ == "__main__":
    main()
