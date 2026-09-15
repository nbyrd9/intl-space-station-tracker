#!/usr/bin/env python3
"""Log one real-time ISS observation.

Fetches the International Space Station's current latitude/longitude and
the list of everyone currently in space from the free Open Notify API
(http://open-notify.org, no key required), appends a row to
data/positions.csv, refreshes data/crew.json, and rewrites README.md with
the latest snapshot.

Every call returns a different position (the ISS moves at ~7.66 km/s), so
every run this script is invoked adds a genuinely new data point rather
than a possibly-unchanged snapshot. Standard library only.
"""

from __future__ import annotations

import csv
import json
import pathlib
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

ISS_URLS = [
    "https://api.open-notify.org/iss-now.json",
    "http://api.open-notify.org/iss-now.json",
]
ASTROS_URLS = [
    "https://api.open-notify.org/astros.json",
    "http://api.open-notify.org/astros.json",
]
USER_AGENT = "iss-tracker (https://github.com/nbyrd9/iss-tracker)"

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSITIONS_CSV = ROOT / "data" / "positions.csv"
CREW_JSON = ROOT / "data" / "crew.json"
README = ROOT / "README.md"

README_TEMPLATE = """# ISS Tracker

A growing, public dataset of the International Space Station's real-time
position, logged by a scheduled GitHub Actions workflow that samples it a
few times a day at randomized moments. Every observation is a genuinely
new data point, since the station moves at roughly 7.66 km/s (~27,600 km/h)
-- there's no such thing as an unchanged snapshot here.

- **How it works:** [`.github/workflows/log-iss.yml`](./.github/workflows/log-iss.yml)
  runs [`scripts/log_position.py`](./scripts/log_position.py) on a randomized
  schedule (2-7 times a day); each run appends one row to
  [`data/positions.csv`](./data/positions.csv).
- **Data source:** the free [Open Notify](http://open-notify.org/Open-Notify-API/ISS-Location-Now/)
  API (no authentication).
- **Raw data:** [`data/positions.csv`](./data/positions.csv) --
  `timestamp_utc,latitude,longitude`, one row per observation, oldest first.
  Plot it yourself to trace the station's ground track.

---

## Latest observation

- **Captured:** {captured} UTC
- **Position:** {lat}, {lon} ([view on a map](https://www.google.com/maps?q={lat},{lon}))
- **Total observations logged:** {total}

## Currently in space ({crew_count})

{crew_lines}

_Crew list from Open Notify; refreshed each run, may lag real crew changes
by up to one workflow cycle._
"""


def fetch_json(urls: list[str]) -> dict | None:
    req_headers = {"User-Agent": USER_AGENT}
    last_error: Exception | None = None
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=req_headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.load(resp)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            continue
    print(f"All endpoints failed for {urls}: {last_error}", file=sys.stderr)
    return None


def append_position(lat: str, lon: str, captured: datetime) -> int:
    POSITIONS_CSV.parent.mkdir(exist_ok=True)
    is_new = not POSITIONS_CSV.exists()
    with POSITIONS_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["timestamp_utc", "latitude", "longitude"])
        writer.writerow([captured.strftime("%Y-%m-%dT%H:%M:%SZ"), lat, lon])

    with POSITIONS_CSV.open(encoding="utf-8") as f:
        total = sum(1 for _ in f) - 1  # minus header
    return total


def write_crew(people: list[dict]) -> None:
    CREW_JSON.write_text(
        json.dumps({"people": people, "count": len(people)}, indent=2) + "\n",
        encoding="utf-8",
    )


def update_readme(lat: str, lon: str, captured: datetime, total: int, people: list[dict]) -> None:
    crew_lines = "\n".join(
        f"- {p['name']} ({p['craft']})" for p in sorted(people, key=lambda p: p["craft"])
    ) or "_No crew data available._"
    README.write_text(
        README_TEMPLATE.format(
            captured=captured.strftime("%Y-%m-%d %H:%M:%S"),
            lat=lat,
            lon=lon,
            total=total,
            crew_count=len(people),
            crew_lines=crew_lines,
        ),
        encoding="utf-8",
    )


def main() -> int:
    position = fetch_json(ISS_URLS)
    if position is None or position.get("message") != "success":
        print("Could not fetch ISS position; skipping this observation.", file=sys.stderr)
        return 1

    astros = fetch_json(ASTROS_URLS)
    people = astros.get("people", []) if astros else []

    captured = datetime.now(timezone.utc)
    lat = position["iss_position"]["latitude"]
    lon = position["iss_position"]["longitude"]

    total = append_position(lat, lon, captured)
    write_crew(people)
    update_readme(lat, lon, captured, total, people)

    print(f"Logged observation #{total}: {lat}, {lon} at {captured:%Y-%m-%d %H:%M:%S} UTC")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
