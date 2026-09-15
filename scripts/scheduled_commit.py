#!/usr/bin/env python3
"""Decide whether this run should log an observation, and if so, do it.

GitHub Actions cron cannot randomize either its firing time or how often it
fires, so this script layers a per-day plan on top of a fixed
every-2-hours trigger:

  * a deterministic RNG seeded from today's UTC date picks an observation
    count between 2 and 7, then that many distinct 2-hour windows -- every
    run of the day computes the same plan
  * a run whose window is not in today's plan exits without committing
  * a run whose window IS in the plan waits a random 0-85 minutes (so the
    push lands at an unpredictable minute), logs one ISS observation,
    commits, and pushes

A manual `workflow_dispatch` run always logs immediately, ignoring the
plan (handy for testing). If the Open Notify API is unreachable, the run
exits cleanly without committing rather than failing the workflow.
"""

from __future__ import annotations

import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import log_position as lp  # noqa: E402

WINDOW_HOURS = list(range(0, 24, 2))  # 0,2,...,22 -- matches cron "0 */2 * * *"
MAX_JITTER_SECONDS = 85 * 60
EVENT_NAME = os.environ.get("GITHUB_EVENT_NAME", "")
IN_CI = os.environ.get("GITHUB_ACTIONS") == "true"
MANUAL = EVENT_NAME == "workflow_dispatch"

GIT_NAME = os.environ.get("DIGEST_GIT_NAME", "nbyrd9")
GIT_EMAIL = os.environ.get(
    "DIGEST_GIT_EMAIL", "50628304+nbyrd9@users.noreply.github.com"
)

COMMIT_PHRASINGS = [
    "Log an ISS observation",
    "Record the station's position",
    "Track the ISS ground pass",
    "Sample ISS telemetry",
    "Append an orbit fix",
    "Capture the station's coordinates",
    "Note where the ISS is now",
    "Update the ISS position log",
    "Add a fresh orbit sample",
    "Pin the station's current location",
]


def sh(*args: str, check: bool = True) -> str:
    return subprocess.run(
        args, check=check, capture_output=True, text=True
    ).stdout.strip()


def todays_plan(day: str) -> list[int]:
    rng = random.Random(f"iss-tracker::{day}")
    count = rng.randint(2, 7)
    return sorted(rng.sample(WINDOW_HOURS, count))


def current_window(now: datetime) -> int:
    return (now.hour // 2) * 2


def already_committed_this_window(day: str, window: int) -> bool:
    subjects = sh(
        "git", "log", f"--since={day}T00:00:00Z", "--pretty=%s", check=False
    )
    return f"[w{window:02d}]" in subjects


def publish(window: int) -> int:
    rc = lp.main()
    if rc != 0:
        print("log_position.py reported failure; not committing.", file=sys.stderr)
        return rc

    if not IN_CI:
        print("[local] logged observation; skipping git commit/push.")
        return 0

    sh("git", "config", "user.name", GIT_NAME)
    sh("git", "config", "user.email", GIT_EMAIL)
    sh("git", "add", "-A")
    if not sh("git", "status", "--porcelain"):
        print("Nothing changed; nothing to commit.")
        return 0

    now = datetime.now(timezone.utc)
    tag = "" if MANUAL else f" [w{window:02d}]"
    phrasing = random.choice(COMMIT_PHRASINGS)
    msg = f"{phrasing} ({now:%Y-%m-%d %H:%M UTC}){tag}"
    sh("git", "commit", "-m", msg)

    for attempt in range(1, 5):
        sh("git", "pull", "--rebase", "--autostash", "origin", "main", check=False)
        push = subprocess.run(
            ["git", "push", "origin", "HEAD:main"],
            capture_output=True, text=True,
        )
        if push.returncode == 0:
            print(f"Pushed: {msg}")
            return 0
        print(f"push attempt {attempt} failed: {push.stderr.strip()}", file=sys.stderr)
        time.sleep(5)
    return 1


def main() -> int:
    now = datetime.now(timezone.utc)
    day = f"{now:%Y-%m-%d}"

    if MANUAL:
        print("Manual dispatch: logging immediately.")
        return publish(current_window(now))

    window = current_window(now)
    plan = todays_plan(day)
    print(f"{day} plan: observation windows {plan} (UTC hours); this run is window {window:02d}.")

    if window not in plan:
        print("Window not in today's plan; exiting without commit.")
        return 0
    if already_committed_this_window(day, window):
        print("Window already produced a commit today; exiting.")
        return 0

    jitter = random.randint(0, MAX_JITTER_SECONDS)
    print(f"Sleeping {jitter // 60}m{jitter % 60:02d}s before logging (time randomization).")
    time.sleep(jitter)

    return publish(window)


if __name__ == "__main__":
    raise SystemExit(main())
