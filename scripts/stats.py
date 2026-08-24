"""Generate transparent, GitHub-green activity SVGs without third-party services."""
from __future__ import annotations
import argparse, datetime as dt, html, json, os, urllib.error, urllib.request
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

def text(x, y, value, size=14, color=PRIMARY, anchor="start") -> str:
    return f'<text x="{x}" y="{y}" fill="{color}" text-anchor="{anchor}" font-family="Consolas,DejaVu Sans Mono,monospace" font-size="{size}">{html.escape(str(value))}</text>'

def svg(title: str, body: list[str], height=180) -> str:
    title = html.escape(title.upper())
    return "\n".join([f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{title}" viewBox="0 0 760 {height}">',f'<text x="24" y="31" fill="{MUTED}" font-family="Consolas,DejaVu Sans Mono,monospace" font-size="12" letter-spacing="1.4">{title}</text>',*body,'</svg>'])+"\n"

def placeholders() -> None:
    body=[text(24,82,"activity will appear after the first workflow run",16),text(24,112,"run locally with GITHUB_TOKEN to populate",12,SECONDARY)]
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
    def weekly_color(value: int) -> str:
        ratio=value/scale
        return EMPTY if value==0 else GREEN_1 if ratio<.34 else GREEN_3 if ratio<.72 else GREEN_4
    bars=[f'<rect x="{390+i*27}" y="{135-round(76*v/scale)}" width="11" height="{max(2,round(76*v/scale))}" rx="1" fill="{weekly_color(v)}"/>' for i,v in enumerate(weeks)]
    body=[text(24,85,f"{total:,}",34),text(25,110,"lifetime public contributions",12,SECONDARY),text(250,85,recent,34,GREEN_4),text(251,110,"last 7 days",12,SECONDARY),*bars]
    (OUT/"stats.svg").write_text(svg("Contribution record / 12-week pulse",body),encoding="utf-8")
    current,longest=streaks(days)
    body=[text(24,92,current,40,GREEN_4),text(25,119,"current days",12,SECONDARY),'<line x1="24" y1="132" x2="128" y2="132" stroke="#26a641" stroke-width="2"/>',text(280,92,longest,40,GREEN_4),text(281,119,"longest days",12,SECONDARY),'<line x1="280" y1="132" x2="384" y2="132" stroke="#26a641" stroke-width="2"/>']
    (OUT/"streak.svg").write_text(svg("Working rhythm",body),encoding="utf-8")
    total_bytes=sum(langs.values()) or 1; body=[]
    language_colors=(GREEN_3,GREEN_2,GREEN_1,GREEN_1,GREEN_1,GREEN_1)
    for i,(name,amount) in enumerate(langs.most_common(6)):
        y=67+i*20; percent=amount/total_bytes*100
        body += [text(24,y,name,13),text(190,y,f"{percent:4.1f}%",12,SECONDARY,"end"),f'<rect x="215" y="{y-10}" width="{round(500*percent/100)}" height="7" rx="1" fill="{language_colors[i]}"/>']
    (OUT/"languages.svg").write_text(svg("Repository language mix",body,210),encoding="utf-8")
    current_year=[d for d in days if d["date"].startswith(str(today.year))]; counts={d["date"]:d["contributionCount"] for d in current_year}; first=dt.date(today.year,1,1); cells=[]
    for offset in range((today-first).days+1):
        day=first+dt.timedelta(days=offset); count=counts.get(day.isoformat(),0); x=25+(day-first).days//7*13; y=61+day.weekday()*13
        shade=EMPTY if count==0 else GREEN_1 if count<2 else GREEN_2 if count<4 else GREEN_3 if count<7 else GREEN_4
        opacity=' fill-opacity="0.45"' if count==0 else ""
        cells.append(f'<rect x="{x}" y="{y}" width="9" height="9" rx="1" fill="{shade}"{opacity}/>')
    cells.append(text(25,171,f'{sum(d["contributionCount"] for d in current_year):,} contributions in {today.year}',12,SECONDARY))
    (OUT/"year.svg").write_text(svg("Year / daily trace",cells,190),encoding="utf-8")

def restyle_existing() -> None:
    """Apply the current visual system without recalculating already-generated data."""
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    namespace="{http://www.w3.org/2000/svg}"
    for name in ("stats.svg","streak.svg","languages.svg","year.svg"):
        path=OUT/name; tree=ET.parse(path); root=tree.getroot()
        for child in list(root):
            if child.tag==namespace+"rect" and child.get("width")=="100%" and child.get("height")=="100%":
                root.remove(child)
        texts=root.findall(namespace+"text")
        for item in texts:
            if item.get("y")=="31": item.set("fill",MUTED)
            elif item.get("font-size") in ("12","13"): item.set("fill",SECONDARY if item.get("font-size")=="12" else PRIMARY)
            else: item.set("fill",PRIMARY)
        rects=root.findall(namespace+"rect")
        if name=="stats.svg":
            numbers=[item for item in texts if item.get("font-size")=="34"]
            if len(numbers)>1: numbers[1].set("fill",GREEN_4)
            bars=[item for item in rects if int(float(item.get("x","0")))>=390]
            scale=max((float(item.get("height","0")) for item in bars),default=1)
            for bar in bars:
                height=float(bar.get("height","0")); ratio=height/scale
                bar.set("fill",EMPTY if height<=2 else GREEN_1 if ratio<.34 else GREEN_3 if ratio<.72 else GREEN_4)
                bar.set("rx","1")
        elif name=="streak.svg":
            for item in texts:
                if item.get("font-size")=="40": item.set("fill",GREEN_4)
            if not root.findall(namespace+"line"):
                for x in (24,280):
                    ET.SubElement(root,namespace+"line",{"x1":str(x),"y1":"132","x2":str(x+104),"y2":"132","stroke":GREEN_3,"stroke-width":"2"})
        elif name=="languages.svg":
            colors=(GREEN_3,GREEN_2,GREEN_1,GREEN_1,GREEN_1,GREEN_1)
            for index,bar in enumerate(rects):
                bar.set("fill",colors[min(index,len(colors)-1)]); bar.set("rx","1")
        else:
            mapping={"#e8e8e8":EMPTY,"#a5a5a5":GREEN_1,"#555":GREEN_2,"#161616":GREEN_4}
            for cell in rects:
                old=cell.get("fill",""); cell.set("fill",mapping.get(old,old))
                if old=="#e8e8e8": cell.set("fill-opacity","0.45")
        serialized=ET.tostring(root,encoding="unicode").rstrip()+"\n"
        path.write_bytes(serialized.encode("utf-8"))
    print("Restyled existing activity graphics without changing their data.")

def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--username",default=os.getenv("GITHUB_REPOSITORY_OWNER","irohankumars")); parser.add_argument("--token",default=os.getenv("GITHUB_TOKEN")); parser.add_argument("--restyle-existing",action="store_true"); args=parser.parse_args(); OUT.mkdir(parents=True,exist_ok=True)
    if args.restyle_existing: restyle_existing(); return
    if not args.token: print("GITHUB_TOKEN not set; writing first-run placeholders."); placeholders(); return
    try: days,total=activity(args.token,args.username); render(days,total,languages(args.token,args.username))
    except (urllib.error.HTTPError,urllib.error.URLError,RuntimeError,KeyError) as error: raise SystemExit(f"GitHub data generation failed: {error}") from error
    print(f"Updated activity graphics for {args.username}.")

if __name__ == "__main__": main()
