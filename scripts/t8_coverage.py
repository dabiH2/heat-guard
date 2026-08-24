"""
t8_coverage.py — where does historical coverage ACTUALLY start?

Run:  python scripts/t8_coverage.py

CLAUDE.md says data runs from 2021-01-01. During the T8 screen, 2021-08-04 came back
`Completed` with `n_cells: 0` for PHX-CHASE — while 2025-07-15 on the same AOI returns
10 tiles. The request was accepted, ran to completion, reported success, and was billed
4,220 credits for nothing.

That is a FOURTH silent-and-billed failure mode, and unlike the other three it is about
DATE COVERAGE rather than location, units or the forecast edge. It matters directly: T8
picks the demo day, and a date with no data produces an empty demo that looks like a
working one.

One tcm call per year on the lead site. Slow (~230 s each at current API load) but cheap
in credits, and it decides which years the demo can even use.
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

OUT = ROOT / "data" / "fixtures" / "t8"
SITE = "PHX-CHASE"

# Mid-July every year: reliably hot, so an empty result means missing data rather than
# a legitimately unremarkable day.
#
# The first pass established 2021-07-15 EMPTY and 2022-07-15 with data, so the boundary
# lies between them and the extra dates bisect it. Worth the calls: shipping "data starts
# 2021-01-01" unverified is exactly the class of unchecked claim this project keeps
# finding, and the router's coverage refusal should state a date we actually measured.
# Cached probes cost nothing, so re-running is cheap.
PROBE_DATES = [
    "2021-07-15",   # measured EMPTY
    "2021-10-15",
    "2022-01-15",
    "2022-04-15",
    "2022-07-15",   # measured 10 tiles
    "2023-07-15", "2024-07-15", "2025-07-15",
]


def main() -> int:
    fc = json.loads((ROOT / "config" / "sites.geojson").read_text(encoding="utf-8"))
    feature = next(f for f in fc["features"] if f["properties"]["site_id"] == SITE)
    aoi = {"type": "FeatureCollection",
           "features": [{"type": "Feature", "properties": {},
                         "geometry": feature["geometry"]}]}

    start = tools.credits_remaining()
    print(f"credits: {start:,}   site: {SITE}")
    print(f"probing {len(PROBE_DATES)} dates, tcm only\n")
    print(f"{'date':<14}{'tiles':>7}{'peak °F':>10}{'mean °F':>10}  verdict")

    findings = []
    for date in PROBE_DATES:
        try:
            result = tools.heatmap(aoi, date, filter_type=3, analytic_type="tcm",
                                   label=f"t8-coverage:{date}")
        except tools.ToolsError as exc:
            print(f"{date:<14}{'-':>7}{'-':>10}{'-':>10}  ERROR: {str(exc)[:50]}")
            findings.append({"date": date, "error": str(exc)[:200]})
            continue

        summary = tools.site_summary_f(result)
        n = (result.get("stats_data") or {}).get("n_cells")
        if summary is None:
            print(f"{date:<14}{0:>7}{'-':>10}{'-':>10}  EMPTY — billed for nothing")
            findings.append({"date": date, "n_cells": n or 0, "has_data": False})
        else:
            print(f"{date:<14}{summary['n_tiles']:>7}{summary['max_f']:>10.1f}"
                  f"{summary['mean_f']:>10.1f}  ok")
            findings.append({
                "date": date, "n_cells": summary["n_tiles"], "has_data": True,
                "peak_f": round(summary["max_f"], 2),
                "mean_f": round(summary["mean_f"], 2),
                "min_f": round(summary["min_f"], 2),
            })

    end = tools.credits_remaining()
    have = [f["date"] for f in findings if f.get("has_data")]
    lack = [f["date"] for f in findings if f.get("has_data") is False]
    print(f"\nwith data   : {have}")
    print(f"empty       : {lack}")
    print(f"credits     : {start:,} -> {end:,} (spent {start - end:,})")
    if lack:
        print(f"\n>>> {len(lack)} date(s) returned Completed with zero cells and were "
              f"billed anyway.")
        print(">>> The router must refuse dates outside real coverage, not just before "
              "2021-01-01.")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "coverage.json").write_text(
        json.dumps({"site": SITE, "findings": findings,
                    "dates_with_data": have, "dates_empty": lack,
                    "credits_spent": start - end}, indent=2) + "\n", encoding="utf-8")
    print(f"written to {(OUT / 'coverage.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
