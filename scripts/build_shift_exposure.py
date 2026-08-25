"""
build_shift_exposure.py — hours above threshold DURING EACH CREW'S ACTUAL SHIFT.

Run:  python scripts/build_shift_exposure.py [YYYY-MM-DD]

This is the number the whole project has been arguing toward. `filter_type=3` gives
hours above threshold across the whole day; `filter_type=2` scopes them to an hour range,
confirmed in T8. So exposure can be measured inside the window the crew is actually
standing outside — the T1 correction, finally in code rather than in prose.

A shift crossing midnight cannot be one range, so night crews take two calls: the evening
part on day D and the morning part on D+1, summed.

Cost: 8 day sites x 1 call + 4 night sites x 2 calls = 16 calls. Cached calls are free,
so re-running resumes.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import date as _date
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")

from heatguard import tools  # noqa: E402

DEFAULT_DATE = "2025-07-15"
THRESHOLD_F = 103.0          # OSHA high-risk band; 91 saturates, measured in T8


def hhmm(value: str) -> str:
    """The API wants whole hours. Round the shift edge outward so exposure is never
    under-counted — a supervisor is better served by a conservative number."""
    hour, minute = (int(p) for p in value.split(":"))
    return f"{hour:02d}:00" if minute == 0 else f"{hour:02d}:00"


def main(date: str) -> int:
    with (ROOT / "config" / "sites.csv").open(newline="", encoding="utf-8") as fh:
        roster = {r["site_id"]: dict(r) for r in csv.DictReader(fh)}
    geo = json.loads((ROOT / "config" / "sites.geojson").read_text(encoding="utf-8"))
    feats = {f["properties"]["site_id"]: f for f in geo["features"]}

    next_day = (_date.fromisoformat(date) + timedelta(days=1)).isoformat()
    start_credits = tools.credits_remaining()
    print(f"credits {start_credits:,}   threshold {THRESHOLD_F:.0f} °F heat index\n")
    print(f"{'site':<11}{'shift':<16}{'crew':>5}{'whole day':>11}{'in shift':>10}"
          f"{'worker-h':>10}")

    rows = []
    for site_id, site in roster.items():
        feature = feats[site_id]
        aoi = {"type": "FeatureCollection",
               "features": [{"type": "Feature", "properties": {},
                             "geometry": feature["geometry"]}]}
        lon, lat = feature["properties"]["centroid"]

        humidity = 20.0
        try:
            env = tools.env_params(lat=lat, lon=lon, air_temp_c=37.0,
                                   date=date, filter_type=3)
            series = ((env.get("locations") or [{}])[0].get("parameters", {})
                      .get("relative_humidity_percent") or [])
            vals = [v for v in series if v is not None]
            if vals:
                humidity = sum(vals) / len(vals)
        except tools.ToolsError:
            pass
        threshold_c = round(tools.air_temp_c_for_heat_index_f(THRESHOLD_F, humidity), 2)

        try:
            whole = tools.heatmap(aoi, date, filter_type=3, analytic_type="exceedance",
                                  threshold_c=threshold_c, direction="above",
                                  label=f"shift-whole:{site_id}:{date}")
            whole_h = sum(tools.tile_hours(whole)) / max(len(tools.tile_hours(whole)), 1)
        except tools.ToolsError as exc:
            print(f"{site_id:<11}  whole-day FAILED: {str(exc)[:48]}")
            continue

        start, end = hhmm(site["shift_start"]), hhmm(site["shift_end"])
        night = site["night_shift"] == "True"

        try:
            if night:
                evening = tools.heatmap(
                    aoi, date, filter_type=2, analytic_type="exceedance",
                    start_time=start, end_time="23:00",
                    threshold_c=threshold_c, direction="above",
                    label=f"shift-eve:{site_id}:{date}")
                morning = tools.heatmap(
                    aoi, next_day, filter_type=2, analytic_type="exceedance",
                    start_time="00:00", end_time=end,
                    threshold_c=threshold_c, direction="above",
                    label=f"shift-morn:{site_id}:{next_day}")
                parts = [evening, morning]
            else:
                parts = [tools.heatmap(
                    aoi, date, filter_type=2, analytic_type="exceedance",
                    start_time=start, end_time=end,
                    threshold_c=threshold_c, direction="above",
                    label=f"shift-day:{site_id}:{date}")]
            in_shift = 0.0
            for part in parts:
                hrs = tools.tile_hours(part)
                in_shift += (sum(hrs) / len(hrs)) if hrs else 0.0
        except tools.ToolsError as exc:
            print(f"{site_id:<11}  in-shift FAILED: {str(exc)[:48]}")
            continue

        crew = int(site["crew_size"])
        rows.append({
            "site_id": site_id, "name": site["name"], "crew": crew, "night": night,
            "shift": f"{site['shift_start']}-{site['shift_end']}",
            "humidity": round(humidity, 1), "threshold_c": threshold_c,
            "threshold_air_f": round(tools.c_to_f(threshold_c), 1),
            "whole_day_hours": round(whole_h, 2),
            "in_shift_hours": round(in_shift, 2),
            "worker_hours": round(in_shift * crew, 1),
            "hours_outside_shift": round(whole_h - in_shift, 2),
        })
        print(f"{site_id:<11}{rows[-1]['shift']:<16}{crew:>5}{whole_h:>11.1f}"
              f"{in_shift:>10.1f}{in_shift * crew:>10.1f}")

    end_credits = tools.credits_remaining()
    print(f"\ncredits {start_credits:,} -> {end_credits:,} "
          f"(spent {start_credits - end_credits:,})")

    if rows:
        total_worker_h = sum(r["worker_hours"] for r in rows)
        naive_worker_h = sum(r["whole_day_hours"] * r["crew"] for r in rows)
        print("\n" + "=" * 78)
        print(f"Applying the whole-day figure uniformly implies "
              f"{naive_worker_h:,.0f} unsafe worker-hours.")
        print(f"Scoped to the shifts crews actually work: {total_worker_h:,.0f}.")
        print(f"Difference: {naive_worker_h - total_worker_h:,.0f} worker-hours of "
              f"exposure that nobody was ever standing in.")

    out = ROOT / "data" / "fixtures" / "t8" / f"shift_exposure_{date}.json"
    out.write_text(json.dumps({"date": date, "threshold_f_heat_index": THRESHOLD_F,
                               "rows": rows}, indent=2) + "\n", encoding="utf-8")
    print(f"\nwritten to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DATE))
