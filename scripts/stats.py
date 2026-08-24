"""Generate monochrome GitHub activity SVGs without third-party services."""
from __future__ import annotations
import argparse, datetime as dt, html, json, os, urllib.error, urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "generated"

def get_json(url: str, token: str, payload: dict | None = None):
    request = urllib.request.Request(url, data=json.dumps(payload).encode() if payload else None)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("User-Agent", "irohankumars-profile")
    if payload: request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)

def calendar(token: str, username: str, year: int, end: dt.date) -> dict:
    query = """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){contributionsCollection(from:$from,to:$to){contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""
    variables = {"login": username, "from": dt.datetime(year,1,1,tzinfo=dt.timezone.utc).isoformat(), "to": dt.datetime.combine(end,dt.time.max,tzinfo=dt.timezone.utc).isoformat()}
    result = get_json("https://api.github.com/graphql", token, {"query": query, "variables": variables})
    if result.get("errors"): raise RuntimeError(result["errors"][0]["message"])
    return result["data"]["user"]["contributionsCollection"]["contributionCalendar"]

def activity(token: str, username: str) -> tuple[list[dict], int]:
    profile = get_json(f"https://api.github.com/users/{username}", token)
    today = dt.datetime.now(dt.timezone.utc).date()
    first = dt.date.fromisoformat(profile["created_at"][:10]).year
    days, total = [], 0
    for year in range(first, today.year + 1):
        data = calendar(token, username, year, today if year == today.year else dt.date(year,12,31))
        total += data["totalContributions"]
        days += [day for week in data["weeks"] for day in week["contributionDays"]]
    return days, total

def languages(token: str, username: str) -> Counter:
    totals, page = Counter(), 1
    while True:
        repos = get_json(f"https://api.github.com/users/{username}/repos?type=owner&sort=pushed&per_page=100&page={page}", token)
        for repo in repos:
            if not repo["fork"] and not repo.get("archived"):
                totals.update(get_json(repo["languages_url"], token))
        if len(repos) < 100: return totals
        page += 1

def streaks(days: list[dict]) -> tuple[int, int]:
    counts = {dt.date.fromisoformat(d["date"]): d["contributionCount"] for d in days}
    today = dt.datetime.now(dt.timezone.utc).date()
    cursor = today if counts.get(today,0) else today-dt.timedelta(days=1)
    current = 0
    while counts.get(cursor,0): current, cursor = current+1, cursor-dt.timedelta(days=1)
    longest = run = 0
    for day in sorted(counts):
        run = run+1 if counts[day] else 0; longest = max(longest,run)
    return current,longest

def text(x, y, value, size=14, color="#161616", anchor="start") -> str:
    return f'<text x="{x}" y="{y}" fill="{color}" text-anchor="{anchor}" font-family="Consolas,DejaVu Sans Mono,monospace" font-size="{size}">{html.escape(str(value))}</text>'

def svg(title: str, body: list[str], height=180) -> str:
    title = html.escape(title.upper())
    return "\n".join([f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{title}" viewBox="0 0 760 {height}">','<rect width="100%" height="100%" fill="#fff"/>',f'<text x="24" y="31" fill="#6b6b6b" font-family="Consolas,DejaVu Sans Mono,monospace" font-size="12" letter-spacing="1.4">{title}</text>',*body,'</svg>'])+"\n"

def placeholders() -> None:
    body=[text(24,82,"activity will appear after the first workflow run",16),text(24,112,"run locally with GITHUB_TOKEN to populate",12,"#6b6b6b")]
    for name,title in (("stats.svg","GitHub activity"),("streak.svg","Streaks"),("languages.svg","Languages"),("year.svg","Year in commits")):
        (OUT/name).write_text(svg(title,body),encoding="utf-8")

def render(days: list[dict], total: int, langs: Counter) -> None:
    today=dt.datetime.now(dt.timezone.utc).date()
    recent=sum(d["contributionCount"] for d in days if dt.date.fromisoformat(d["date"])>today-dt.timedelta(days=7))
    weeks=[]
    for offset in range(11,-1,-1):
        end=today-dt.timedelta(days=offset*7); start=end-dt.timedelta(days=6)
        weeks.append(sum(d["contributionCount"] for d in days if start<=dt.date.fromisoformat(d["date"])<=end))
    scale=max(weeks) or 1
    bars=[f'<rect x="{390+i*27}" y="{135-round(76*v/scale)}" width="11" height="{max(2,round(76*v/scale))}" fill="#202020"/>' for i,v in enumerate(weeks)]
    body=[text(24,85,f"{total:,}",34),text(25,110,"lifetime public contributions",12,"#6b6b6b"),text(250,85,recent,34),text(251,110,"last 7 days",12,"#6b6b6b"),*bars]
    (OUT/"stats.svg").write_text(svg("Contribution record / 12-week pulse",body),encoding="utf-8")
    current,longest=streaks(days)
    body=[text(24,92,current,40),text(25,119,"current days",12,"#6b6b6b"),text(280,92,longest,40),text(281,119,"longest days",12,"#6b6b6b")]
    (OUT/"streak.svg").write_text(svg("Working rhythm",body),encoding="utf-8")
    total_bytes=sum(langs.values()) or 1; body=[]
    for i,(name,amount) in enumerate(langs.most_common(6)):
        y=67+i*20; percent=amount/total_bytes*100
        body += [text(24,y,name,13),text(190,y,f"{percent:4.1f}%",12,"#6b6b6b","end"),f'<rect x="215" y="{y-10}" width="{round(500*percent/100)}" height="7" fill="#202020"/>']
    (OUT/"languages.svg").write_text(svg("Repository language mix",body,210),encoding="utf-8")
    current_year=[d for d in days if d["date"].startswith(str(today.year))]; counts={d["date"]:d["contributionCount"] for d in current_year}; first=dt.date(today.year,1,1); cells=[]
    for offset in range((today-first).days+1):
        day=first+dt.timedelta(days=offset); count=counts.get(day.isoformat(),0); x=25+(day-first).days//7*13; y=61+day.weekday()*13
        shade="#e8e8e8" if count==0 else "#a5a5a5" if count<3 else "#555" if count<7 else "#161616"
        cells.append(f'<rect x="{x}" y="{y}" width="9" height="9" rx="1" fill="{shade}"/>')
    cells.append(text(25,171,f'{sum(d["contributionCount"] for d in current_year):,} contributions in {today.year}',12,"#6b6b6b"))
    (OUT/"year.svg").write_text(svg("Year / daily trace",cells,190),encoding="utf-8")

def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--username",default=os.getenv("GITHUB_REPOSITORY_OWNER","irohankumars")); parser.add_argument("--token",default=os.getenv("GITHUB_TOKEN")); args=parser.parse_args(); OUT.mkdir(parents=True,exist_ok=True)
    if not args.token: print("GITHUB_TOKEN not set; writing first-run placeholders."); placeholders(); return
    try: days,total=activity(args.token,args.username); render(days,total,languages(args.token,args.username))
    except (urllib.error.HTTPError,urllib.error.URLError,RuntimeError,KeyError) as error: raise SystemExit(f"GitHub data generation failed: {error}") from error
    print(f"Updated activity graphics for {args.username}.")

if __name__ == "__main__": main()
