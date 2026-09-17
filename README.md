# ISS Tracker

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

- **Captured:** 2026-09-17 00:43:06 UTC
- **Position:** -50.3765, 124.6253 ([view on a map](https://www.google.com/maps?q=-50.3765,124.6253))
- **Total observations logged:** 4

## Currently in space (12)

- Oleg Kononenko (ISS)
- Nikolai Chub (ISS)
- Tracy Caldwell Dyson (ISS)
- Matthew Dominick (ISS)
- Michael Barratt (ISS)
- Jeanette Epps (ISS)
- Alexander Grebenkin (ISS)
- Butch Wilmore (ISS)
- Sunita Williams (ISS)
- Li Guangsu (Tiangong)
- Li Cong (Tiangong)
- Ye Guangfu (Tiangong)

_Crew list from Open Notify; refreshed each run, may lag real crew changes
by up to one workflow cycle._
