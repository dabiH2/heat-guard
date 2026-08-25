"""
t8_shift_window.py — can exceedance be scoped to a crew's actual shift?

Run:  python scripts/t8_shift_window.py

`filter_type=3` + `exceedance` gives hours above threshold across the WHOLE DAY. That is
not the number a supervisor needs. They need hours above threshold DURING THE SHIFT — the
T1 correction in code form: hours nobody was standing in are not exposure.

`filter_type=2` is a range of HOURS (`start_time` + `end_time`). If it composes with
`analytic_type=exceedance`, then exposure can be scoped to the shift window directly by
the API, and the night-crew case — the strongest in the project — becomes measurable
rather than argued.

A night shift crossing midnight cannot be one range, so it takes two calls: the evening
part on day D and the morning part on day D+1. That is a real cost (2x) and worth knowing
before the demo depends on it.

Tests, on PHX-CHASE (6 crew, 21:00-05:30) for 2025-07-15:
  A. whole day                 filter_type=3            -> baseline, already cached
  B. the day shift window      filter_type=2, 05:00-14:00
  C. the night shift, evening  filter_type=2, 21:00-23:00 on 2025-07-15
  D. the night shift, morning  filter_type=2, 00:00-05:00 on 2025-07-16
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")

from heatguard import tools  # noqa: E402

SITE = "PHX-CHASE"
DATE = "2025-07-15"
NEXT_DAY = "2025-07-16"
THRESHOLD_F = 103.0
HUMIDITY = 25.4          # measured at this site on this date


def main() -> int:
    geo = json.loads((ROOT / "config" / "sites.geojson").read_text(encoding="utf-8"))
    feature = next(f for f in geo["features"] if f["properties"]["site_id"] == SITE)
    aoi = {"type": "FeatureCollection",
           "features": [{"type": "Feature", "properties": {},
                         "geometry": feature["geometry"]}]}

    threshold_c = tools.air_temp_c_for_heat_index_f(THRESHOLD_F, HUMIDITY)
    start = tools.credits_remaining()
    print(f"credits {start:,}   site {SITE}   {THRESHOLD_F:.0f} °F HI = "
          f"{tools.c_to_f(threshold_c):.1f} °F air = {threshold_c:.2f} °C\n")

    cases = [
        ("whole day (filter_type=3)", dict(date=DATE, filter_type=3)),
        ("day shift 05:00-14:00", dict(date=DATE, filter_type=2,
                                       start_time="05:00", end_time="14:00")),
        ("night shift evening 21:00-23:00", dict(date=DATE, filter_type=2,
                                                 start_time="21:00", end_time="23:00")),
        ("night shift morning 00:00-05:00", dict(date=NEXT_DAY, filter_type=2,
                                                 start_time="00:00", end_time="05:00")),
    ]

    findings = {"site": SITE, "threshold_f_heat_index": THRESHOLD_F,
                "threshold_c_air": round(threshold_c, 2), "cases": {}}

    for label, kwargs in cases:
        print(f"--- {label}")
        try:
            result = tools.heatmap(
                aoi, analytic_type="exceedance",
                threshold_c=round(threshold_c, 2), direction="above",
                label=f"t8-shift:{label}", **kwargs)
        except tools.ToolsError as exc:
            print(f"    FAILED: {str(exc)[:110]}\n")
            findings["cases"][label] = {"error": str(exc)[:200]}
            continue

        hours = tools.tile_hours(result)
        stats = result.get("stats_data") or {}
        mean = sum(hours) / len(hours) if hours else None
        print(f"    n_cells={stats.get('n_cells')}  units={stats.get('units')}  "
              f"mean={mean}  min={stats.get('min')}  max={stats.get('max')}\n")
        findings["cases"][label] = {
            "n_cells": stats.get("n_cells"), "units": stats.get("units"),
            "mean_hours": mean, "kwargs": {k: str(v) for k, v in kwargs.items()},
        }

    end = tools.credits_remaining()
    print(f"credits {start:,} -> {end:,} (spent {start - end:,})")

    day = findings["cases"].get("day shift 05:00-14:00", {}).get("mean_hours")
    evening = findings["cases"].get("night shift evening 21:00-23:00", {}).get("mean_hours")
    morning = findings["cases"].get("night shift morning 00:00-05:00", {}).get("mean_hours")
    whole = findings["cases"].get("whole day (filter_type=3)", {}).get("mean_hours")

    print("\n" + "=" * 78)
    if day is not None and whole is not None and day < whole:
        print("filter_type=2 DOES scope exceedance to an hour range.")
        print(f"  whole day        {whole:.1f} h")
        print(f"  day shift        {day:.1f} h")
        if evening is not None and morning is not None:
            print(f"  night shift      {evening:.1f} + {morning:.1f} = "
                  f"{evening + morning:.1f} h  (two calls, wraps midnight)")
        print("\n>>> Exposure can be scoped to the crew's actual shift. The night-crew")
        print(">>> case becomes measurable rather than argued.")
        findings["verdict"] = "filter_type=2 scopes exceedance to the hour range"
    elif day is not None and whole is not None and day == whole:
        print("filter_type=2 returns the SAME number as the whole day.")
        print(">>> The hour range is being ignored for exceedance. Shift-window exposure")
        print(">>> must be computed client-side instead, and this is a silent no-op —")
        print(">>> worth recording as another 'accepted but not answered' case.")
        findings["verdict"] = "filter_type=2 ignored for exceedance — silent no-op"
    else:
        findings["verdict"] = "inconclusive"
        print("inconclusive — see the per-case output above")

    out = ROOT / "data" / "fixtures" / "t8" / "shift_window.json"
    out.write_text(json.dumps(findings, indent=2) + "\n", encoding="utf-8")
    print(f"\nwritten to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
