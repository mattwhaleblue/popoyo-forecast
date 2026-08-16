#!/usr/bin/env python3
"""Build static Popoyo forecast pages from data/days/*.json."""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "days"

SPOTS = (
    ("Beachies", 205),
    ("Astillero", 210),
    ("Chacocente", 215),
)

# Tide graph: 4am–10pm in a 320×150 viewBox, not stretched.
T_START = 240
T_END = 1320
X0, X1 = 10.0, 310.0
Y_TOP, Y_BOT, Y_FILL, Y_LABEL = 18.0, 113.0, 122.0, 142.0
HOUR_MARKS = (540, 720, 960)  # 9am, noon, 4pm


def round5(deg: float) -> int:
    return int(round(deg / 5.0) * 5) % 360


def signed_rel(deg: float, facing: int) -> int:
    return (round5(deg) - facing + 180) % 360 - 180


def fmt_rel(rel: int) -> str:
    if rel > 0:
        return f"+{rel}°"
    if rel < 0:
        return f"−{abs(rel)}°"
    return "+0°"


def period_bucket(seconds: int) -> str:
    if seconds < 12:
        return "short"
    if seconds <= 14:
        return "mid"
    if seconds <= 16:
        return "long"
    return "xl"


def swell_bucket(rel: int) -> str:
    if rel < -15:
        return "south"
    if rel > 15:
        return "north"
    return "straight"


def wind_bucket(rel: int) -> str:
    a = abs(rel)
    if a <= 30:
        return "on"
    if a <= 60:
        return "cross-on"
    if a <= 120:
        return "cross"
    if a < 150:
        return "cross-off"
    return "off"


def tide_at(t: float, extrema: list[dict]) -> float:
    if t <= extrema[0]["min"]:
        return float(extrema[0]["ft"])
    if t >= extrema[-1]["min"]:
        return float(extrema[-1]["ft"])
    for a, b in zip(extrema, extrema[1:]):
        if a["min"] <= t <= b["min"]:
            span = b["min"] - a["min"]
            if span == 0:
                return float(a["ft"])
            phase = (t - a["min"]) / span
            return a["ft"] + (b["ft"] - a["ft"]) * (1 - math.cos(math.pi * phase)) / 2
    return float(extrema[-1]["ft"])


def x_at(t: float) -> float:
    return X0 + (t - T_START) / (T_END - T_START) * (X1 - X0)


def y_at(h: float, h_min: float, h_max: float) -> float:
    if h_max <= h_min:
        return (Y_TOP + Y_BOT) / 2
    return Y_TOP + (h_max - h) / (h_max - h_min) * (Y_BOT - Y_TOP)


def clock_label(minutes: int) -> str:
    m = minutes % 1440
    h, mi = divmod(m, 60)
    return f"{h}:{mi:02d}"


def short_nav(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.strftime('%a')} {d.day}"


def title_for(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.strftime('%A')} {d.day} {d.strftime('%b')}"


def tide_graph(extrema: list[dict]) -> str:
    extrema = sorted(extrema, key=lambda e: e["min"])
    visible = [e for e in extrema if T_START <= e["min"] <= T_END]
    if visible:
        h_min = min(e["ft"] for e in visible)
        h_max = max(e["ft"] for e in visible)
    else:
        h_min = min(e["ft"] for e in extrema)
        h_max = max(e["ft"] for e in extrema)

    steps = 136
    pts = []
    for i in range(steps + 1):
        t = T_START + (T_END - T_START) * i / steps
        h = tide_at(t, extrema)
        pts.append((x_at(t), y_at(h, h_min, h_max)))

    d = " ".join(
        f"{'M' if i == 0 else 'L'} {x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts)
    )
    fill = f"{d} L {X1:.1f},{Y_FILL:.1f} L {X0:.1f},{Y_FILL:.1f} Z"

    parts = [
        '<svg class="tide" viewBox="0 0 320 150" preserveAspectRatio="xMidYMid meet" height="150" aria-label="Tide curve">',
        f'<path d="{fill}" fill="#6ec6ff18"/>',
        f'<path d="{d}" fill="none" stroke="#6ec6ff" stroke-width="2" stroke-linecap="round"/>',
    ]

    for e in visible:
        cx, cy = x_at(e["min"]), y_at(e["ft"], h_min, h_max)
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3" fill="#6ec6ff"/>')
        parts.append(
            f'<text x="{cx:.1f}" y="{Y_LABEL:.0f}" text-anchor="middle" class="tick">{clock_label(int(e["min"]))}</text>'
        )

    for t in HOUR_MARKS:
        cx = x_at(t)
        cy = y_at(tide_at(t, extrema), h_min, h_max)
        parts.append(
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{cx:.1f}" y2="{Y_FILL:.1f}" stroke="#8b9aab" stroke-dasharray="2 3" stroke-width="1"/>'
        )
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.2" fill="#e8eef4"/>')

    parts.append("</svg>")
    return "\n".join(parts)


def hour_block(hour: dict) -> str:
    period = f"{hour['period']}s {period_bucket(hour['period'])}"
    rows = []
    for name, facing in SPOTS:
        swell_rel = signed_rel(hour["swell"], facing)
        wind_rel = signed_rel(hour["wind_dir"], facing)
        swell = f"{fmt_rel(swell_rel)} {swell_bucket(swell_rel)}"
        wind = f"{hour['wind_mph']}mph model · {fmt_rel(wind_rel)} {wind_bucket(wind_rel)}"
        rows.append(
            f'<div class="row"><div><div class="spot">{name}</div>'
            f'<div class="kv">{period} · tide <b>{hour["tide"]}</b></div></div>'
            f'<div class="kv">swell <b>{swell}</b><br>wind <b>{wind}</b></div></div>'
        )
    return (
        f'<div class="block">\n<h2>{hour["label"]}</h2>\n'
        + "\n".join(rows)
        + "\n</div>"
    )


def nav_html(iso: str, dates: list[str]) -> str:
    i = dates.index(iso)
    prev_d = dates[i - 1] if i > 0 else None
    next_d = dates[i + 1] if i + 1 < len(dates) else None
    if prev_d:
        prev = f'<a href="/{prev_d}/">← {short_nav(prev_d)}</a>'
    else:
        prev = '<span>← Prev</span>'
    if next_d:
        nxt = f'<a href="/{next_d}/">{short_nav(next_d)} →</a>'
    else:
        nxt = '<span>Next →</span>'
    return f'<nav class="nav">{prev}{nxt}</nav>'


def page_html(day: dict, dates: list[str]) -> str:
    iso = day["date"]
    title = title_for(iso)
    blocks = "\n".join(hour_block(h) for h in day["hours"])
    graph = tide_graph(day["extrema"])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <link rel="stylesheet" href="/style.css" />
</head>
<body>
  <div class="top">
    <div class="brand">Popoyo</div>
    {nav_html(iso, dates)}
  </div>
  <h1>{title}</h1>
  <p class="meta">{day["highs"]}</p>
  <p class="meta">{day["lows"]}</p>
  <p class="meta">{day["sun"]}</p>
  <div class="tide-wrap">{graph}</div>
  {blocks}
</body>
</html>
"""


def index_html(dates: list[str]) -> str:
    links = "\n".join(
        f'    <li><a href="/{d}/">{title_for(d)}</a></li>' for d in reversed(dates)
    )
    dates_js = json.dumps(dates)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Popoyo</title>
  <link rel="stylesheet" href="/style.css" />
  <script>
    (function () {{
      var days = {dates_js};
      var today = new Date().toLocaleDateString("en-CA", {{ timeZone: "America/Managua" }});
      var target = days.indexOf(today) !== -1 ? today : days[days.length - 1];
      location.replace("/" + target + "/");
    }})();
  </script>
</head>
<body>
  <div class="brand">Popoyo</div>
  <h1>Forecasts</h1>
  <ul>
{links}
  </ul>
</body>
</html>
"""


def load_days() -> list[dict]:
    files = sorted(DATA.glob("*.json"))
    days = []
    for path in files:
        day = json.loads(path.read_text())
        if "date" not in day:
            day["date"] = path.stem
        days.append(day)
    days.sort(key=lambda d: d["date"])
    return days


def main() -> None:
    days = load_days()
    if not days:
        raise SystemExit(f"no day json in {DATA}")
    dates = [d["date"] for d in days]

    (ROOT / "days.json").write_text(json.dumps(dates) + "\n")
    (ROOT / "index.html").write_text(index_html(dates))

    for day in days:
        out = ROOT / day["date"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page_html(day, dates))
        print("wrote", out.relative_to(ROOT))

    print("wrote days.json")
    print("wrote index.html")


if __name__ == "__main__":
    main()
