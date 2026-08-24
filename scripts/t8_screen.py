"""
t8_screen.py — test the shortlisted dates against FortyGuard, cheaply.

Run:  python scripts/t8_screen.py

Four sites, one per archetype, across three candidate dates. 4 x 3 x 2 analytic types =
24 calls ~ 101,280 credits, about 5% of the remaining budget. The full 12-site run
happens only on whichever date wins.

WHAT WE ARE LOOKING FOR — the inversion:

    site A has the HIGHER PEAK        (tcm max_temperature)
    site B has MORE HOURS ABOVE       (exceedance)

If that exists on any date, the demo has its money shot: two sites, same day, opposite
conclusions depending on which analysis layer you asked for.

THRESHOLD. `exceedance` thresholds AIR TEMPERATURE; OSHA bands are HEAT INDEX. So the
OSHA number is converted per date using that date's humidity, which is what
air_temp_c_for_heat_index_f exists for. The screen runs at the OSHA HIGH-RISK band
(103 °F heat index) rather than the 91 °F policy threshold, for a reason worth stating
plainly: the free shortlist showed that at 91 °F many Phoenix summer days sit above
threshold for all 24 hours at every site. A saturated metric cannot discriminate. That
is exactly the tension recorded in config/thresholds.yaml, now confirmed with data, and
it is why the final report carries both thresholds.
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

# One site per archetype. PHX-SKY doubles as the metric baseline (KPHX).
SCREEN_SITES = ["PHX-CHASE", "PHX-SMTN", "PHX-SKY", "PHX-ENCA"]

# From t8_shortlist.py. Chosen for calm nights and clear skies — the conditions under
# which local site differences survive instead of being mixed away by wind.
CANDIDATES = [
    ("2021-08-04", 25.0, "highest divergence score; dry, 0% cloud, 30 °F diurnal range"),
    ("2024-07-26", 34.0, "22 h above threshold, 11 of them at night; calm and clear"),
    ("2025-09-20", 39.0, "calmest night on record here (1.3 mph); cooler peak"),
]

TARGET_HEAT_INDEX_F = 103.0     # OSHA high-risk band; see the module docstring


def load_sites() -> dict[str, dict]:
    fc = json.loads((ROOT / "config" / "sites.geojson").read_text(encoding="utf-8"))
    return {f["properties"]["site_id"]: f for f in fc["features"]}


def aoi_of(feature: dict) -> dict:
    return {"type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {},
                          "geometry": feature["geometry"]}]}


def main() -> int:
    sites = load_sites()
    start_credits = tools.credits_remaining()
    print(f"credits remaining: {start_credits:,}")
    print(f"planned: {len(SCREEN_SITES) * len(CANDIDATES) * 2} calls "
          f"(~{len(SCREEN_SITES) * len(CANDIDATES) * 2 * tools.CREDITS_PER_HEATMAP_CALL:,} "
          f"credits, cached calls are free)\n")

    findings: dict = {"target_heat_index_f": TARGET_HEAT_INDEX_F, "dates": {}}

    for date, mean_rh, why in CANDIDATES:
        threshold_c = tools.air_temp_c_for_heat_index_f(TARGET_HEAT_INDEX_F, mean_rh)
        print("=" * 96)
        print(f"{date}  —  {why}")
        print(f"  mean RH {mean_rh:.0f}%  ->  {TARGET_HEAT_INDEX_F:g} °F heat index "
              f"= {tools.c_to_f(threshold_c):.1f} °F air temp = {threshold_c:.2f} °C")
        print("=" * 96)
        print(f"{'site':<12}{'archetype':<24}{'peak °F':>9}{'mean °F':>9}"
              f"{'hours>':>9}{'tiles':>7}")

        rows = []
        for site_id in SCREEN_SITES:
            feature = sites[site_id]
            aoi = aoi_of(feature)
            try:
                tcm = tools.heatmap(aoi, date, filter_type=3, analytic_type="tcm",
                                    label=f"t8-screen-tcm:{site_id}:{date}")
                exc = tools.heatmap(aoi, date, filter_type=3, analytic_type="exceedance",
                                    threshold_c=round(threshold_c, 2), direction="above",
                                    label=f"t8-screen-exc:{site_id}:{date}")
            except tools.ToolsError as exc_err:
                print(f"{site_id:<12}{'':<24}  FAILED: {str(exc_err)[:60]}")
                continue

            summary = tools.site_summary_f(tcm)
            hours = tools.tile_hours(exc)
            if summary is None or not hours:
                print(f"{site_id:<12}  EMPTY RESULT — investigate")
                continue

            mean_hours = sum(hours) / len(hours)
            row = {
                "site_id": site_id,
                "archetype": feature["properties"]["archetype"],
                "expected_profile": feature["properties"]["expected_profile"],
                "peak_f": round(summary["max_f"], 2),
                "mean_f": round(summary["mean_f"], 2),
                "min_f": round(summary["min_f"], 2),
                "hours_above": round(mean_hours, 2),
                "n_tiles": summary["n_tiles"],
            }
            rows.append(row)
            print(f"{site_id:<12}{row['archetype']:<24}{row['peak_f']:>9.1f}"
                  f"{row['mean_f']:>9.1f}{row['hours_above']:>9.1f}{row['n_tiles']:>7}")

        if len(rows) >= 2:
            by_peak = sorted(rows, key=lambda r: -r["peak_f"])
            by_hours = sorted(rows, key=lambda r: -r["hours_above"])
            peak_spread = by_peak[0]["peak_f"] - by_peak[-1]["peak_f"]
            hour_spread = by_hours[0]["hours_above"] - by_hours[-1]["hours_above"]

            print(f"\n  ranked by PEAK    : "
                  f"{' > '.join(r['site_id'] for r in by_peak)}   "
                  f"(spread {peak_spread:.1f} °F)")
            print(f"  ranked by HOURS   : "
                  f"{' > '.join(r['site_id'] for r in by_hours)}   "
                  f"(spread {hour_spread:.1f} h)")

            inversions = [
                (a["site_id"], b["site_id"],
                 round(a["peak_f"] - b["peak_f"], 2),
                 round(b["hours_above"] - a["hours_above"], 2))
                for a in rows for b in rows
                if a["peak_f"] > b["peak_f"] and b["hours_above"] > a["hours_above"]
            ]
            if inversions:
                print("\n  *** INVERSION FOUND ***")
                for hi_peak, hi_hours, dpeak, dhours in sorted(
                        inversions, key=lambda x: -x[3]):
                    print(f"    {hi_peak} peaks {dpeak:+.1f} °F higher, but {hi_hours} "
                          f"spends {dhours:+.1f} h longer above threshold")
            else:
                print("\n  no inversion on this date — peak order matches hours order")

            findings["dates"][date] = {
                "why": why, "mean_rh": mean_rh,
                "threshold_c": round(threshold_c, 2),
                "threshold_air_f": round(tools.c_to_f(threshold_c), 2),
                "rows": rows,
                "peak_spread_f": round(peak_spread, 2),
                "hour_spread": round(hour_spread, 2),
                "inversions": inversions,
            }
        print()

    end_credits = tools.credits_remaining()
    print("=" * 96)
    print(f"credits: {start_credits:,} -> {end_credits:,} "
          f"(spent {start_credits - end_credits:,})")
    findings["credits_spent"] = start_credits - end_credits

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "screen.json").write_text(json.dumps(findings, indent=2) + "\n",
                                     encoding="utf-8")
    print(f"written to {(OUT / 'screen.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
