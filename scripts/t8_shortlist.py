"""
t8_shortlist.py — pick candidate demo days WITHOUT spending a FortyGuard credit.

Run:  python scripts/t8_shortlist.py

T8 needs one historical date where two sites invert: one with the higher peak, the other
far longer above the danger band. Confirming that costs 24 FortyGuard calls per date
(~5% of the remaining budget), so brute-forcing dates is not affordable — about 19 dates
would exhaust everything.

So: shortlist for free first, using Open-Meteo's historical reanalysis (no key, no cost)
for Phoenix, then spend credits only on the finalists.

Open-Meteo gives REGIONAL weather, not per-site. It cannot show an inversion — only
FortyGuard can. What it CAN do is rank days by how favourable they are to site-level
divergence in the first place, which is a physical question with a known answer:

  LOW WIND        the single strongest control. Wind mixes the boundary layer and erases
                  local differences; a calm night lets a street canyon hold heat while
                  open desert dumps it. High wind flattens every site to the same number.
  CLEAR SKY       cloud suppresses both daytime insolation and nocturnal radiative
                  cooling, compressing the spread at both ends.
  HOT ENOUGH      the day has to cross the threshold somewhere or there is no duration
                  to compare.
  HUMIDITY SPLIT  monsoon days keep the heat index elevated for long stretches at a
                  modest temperature peak; dry pre-monsoon days spike higher and fall
                  away faster. TASKS.md flags this as worth testing — so both kinds go
                  on the shortlist rather than assuming which wins.

The output is a ranked candidate list, not an answer. The answer needs FortyGuard.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from heatguard.bands import load_thresholds  # noqa: E402
from heatguard.tools import heat_index_f  # noqa: E402

OUT = ROOT / "data" / "fixtures" / "t8"
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"

# Central Phoenix — the regional signal, not any one site.
LAT, LON = 33.4484, -112.0740
YEARS = (2021, 2022, 2023, 2024, 2025)
SEASON = ("06-01", "09-30")     # pre-monsoon through monsoon

# Phoenix crews work early and late; these are the windows the roster actually uses.
DAY_SHIFT = range(5, 15)        # 05:00-14:59
NIGHT_SHIFT = list(range(19, 24)) + list(range(0, 6))


def fetch_year(year: int) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    cached = OUT / f"openmeteo_phoenix_{year}.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))

    resp = requests.get(ARCHIVE, params={
        "latitude": LAT, "longitude": LON,
        "start_date": f"{year}-{SEASON[0]}", "end_date": f"{year}-{SEASON[1]}",
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,cloud_cover",
        "temperature_unit": "fahrenheit", "wind_speed_unit": "mph",
        "timezone": "America/Phoenix",
    }, timeout=90)
    resp.raise_for_status()
    data = resp.json()
    cached.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def daily_metrics(threshold_f: float) -> list[dict]:
    rows: list[dict] = []
    for year in YEARS:
        data = fetch_year(year)
        hourly = data["hourly"]
        by_day: dict[str, list[dict]] = defaultdict(list)
        for stamp, temp, rh, wind, cloud in zip(
            hourly["time"], hourly["temperature_2m"], hourly["relative_humidity_2m"],
            hourly["wind_speed_10m"], hourly["cloud_cover"],
        ):
            if temp is None or rh is None:
                continue
            date, hour = stamp.split("T")
            by_day[date].append({
                "hour": int(hour[:2]), "temp_f": temp, "rh": rh,
                "wind": wind if wind is not None else 0.0,
                "cloud": cloud if cloud is not None else 0.0,
                "hi_f": heat_index_f(temp, rh),
            })

        for date, hours in by_day.items():
            if len(hours) < 24:
                continue
            his = [h["hi_f"] for h in hours]
            day = [h for h in hours if h["hour"] in DAY_SHIFT]
            night = [h for h in hours if h["hour"] in NIGHT_SHIFT]
            rows.append({
                "date": date,
                "peak_temp_f": max(h["temp_f"] for h in hours),
                "peak_hi_f": max(his),
                "min_temp_f": min(h["temp_f"] for h in hours),
                "hours_above": sum(1 for v in his if v >= threshold_f),
                "day_hours_above": sum(1 for h in day if h["hi_f"] >= threshold_f),
                "night_hours_above": sum(1 for h in night if h["hi_f"] >= threshold_f),
                "mean_wind": sum(h["wind"] for h in hours) / len(hours),
                "night_wind": sum(h["wind"] for h in night) / max(len(night), 1),
                "mean_cloud": sum(h["cloud"] for h in hours) / len(hours),
                "mean_rh": sum(h["rh"] for h in hours) / len(hours),
                "diurnal_range_f": max(h["temp_f"] for h in hours)
                                   - min(h["temp_f"] for h in hours),
            })
    return rows


def divergence_score(row: dict) -> float:
    """How favourable is this day to SITE-LEVEL divergence?

    Calm and clear is the whole story — wind mixes local differences away and cloud
    compresses the spread at both ends. A large diurnal range is corroborating evidence
    that radiative processes, not advection, ran the day. The day also has to be hot
    enough that there is duration to compare at all.
    """
    if row["hours_above"] < 4:
        return 0.0
    calm = max(0.0, 12.0 - row["night_wind"]) / 12.0        # calm nights matter most
    clear = max(0.0, 100.0 - row["mean_cloud"]) / 100.0
    swing = min(row["diurnal_range_f"] / 35.0, 1.0)
    heat = min(row["hours_above"] / 24.0, 1.0)
    return round(100 * (0.40 * calm + 0.25 * clear + 0.20 * swing + 0.15 * heat), 1)


def main() -> int:
    threshold_f = load_thresholds().unsafe_from_f
    print(f"Phoenix {YEARS[0]}-{YEARS[-1]}, {SEASON[0]} to {SEASON[1]}, "
          f"threshold {threshold_f:g} °F heat index")
    print("Open-Meteo historical reanalysis — free, no FortyGuard credits.\n")

    rows = daily_metrics(threshold_f)
    for row in rows:
        row["score"] = divergence_score(row)
    print(f"{len(rows)} days analysed\n")

    def table(title: str, subset: list[dict], note: str) -> None:
        print("=" * 108)
        print(title)
        print(f"  {note}")
        print("=" * 108)
        print(f"{'date':<12}{'peakT':>7}{'peakHI':>8}{'hrs>':>6}{'day':>5}{'night':>7}"
              f"{'wind':>7}{'nWind':>7}{'cloud':>7}{'RH%':>6}{'range':>7}{'score':>7}")
        for r in subset:
            print(f"{r['date']:<12}{r['peak_temp_f']:>7.0f}{r['peak_hi_f']:>8.0f}"
                  f"{r['hours_above']:>6}{r['day_hours_above']:>5}"
                  f"{r['night_hours_above']:>7}{r['mean_wind']:>7.1f}"
                  f"{r['night_wind']:>7.1f}{r['mean_cloud']:>7.0f}{r['mean_rh']:>6.0f}"
                  f"{r['diurnal_range_f']:>7.1f}{r['score']:>7.1f}")
        print()

    best = sorted(rows, key=lambda r: -r["score"])[:12]
    table("A. BEST CONDITIONS FOR SITE-LEVEL DIVERGENCE",
          best, "calm + clear + big diurnal swing = local effects survive")

    monsoon = [r for r in rows if r["mean_rh"] >= 45 and r["hours_above"] >= 12]
    table("B. MONSOON — humid, long duration at a modest peak",
          sorted(monsoon, key=lambda r: -r["hours_above"])[:8],
          "TASKS.md hypothesis: heat index stays elevated without a high temperature peak")

    dry = [r for r in rows if r["mean_rh"] < 25 and r["peak_temp_f"] >= 110]
    table("C. DRY PRE-MONSOON — high peak, fast fall-off",
          sorted(dry, key=lambda r: -r["peak_temp_f"])[:8],
          "the other half of the hypothesis: spikes higher, sheds faster")

    night_heavy = sorted(rows, key=lambda r: -r["night_hours_above"])[:8]
    table("D. WORST NIGHTS — the lead demo case",
          night_heavy,
          "a night crew's entire shift above threshold; a daytime forecast high shows none of it")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "shortlist.json").write_text(
        json.dumps({"threshold_f": threshold_f, "generated_from": "open-meteo archive",
                    "best_divergence": best, "monsoon": monsoon[:20], "dry": dry[:20],
                    "night_heavy": night_heavy}, indent=2) + "\n", encoding="utf-8")
    print(f"written to {(OUT / 'shortlist.json').relative_to(ROOT)}")
    print("\nNEXT: confirm the finalists with FortyGuard. 24 calls per date "
          "(12 sites x tcm + exceedance) ~ 5% of the remaining budget each.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
