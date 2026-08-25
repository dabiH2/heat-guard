"""
t8_analyse.py — what the demo-day data actually says. Offline, no credits.

Run:  python scripts/t8_analyse.py [YYYY-MM-DD]

Answers three questions, in descending order of how much the project depends on them:

  1. Does peak converge while duration separates? (the thesis)
  2. Does any pair INVERT — higher peak, fewer hours? (the money shot)
  3. Did the per-site predictions written in T1 come true? (honesty)

Question 3 exists because docs/site_selection.md committed to reporting failures:
"Sites whose prediction fails are kept and reported. A roster where all twelve came true
would be evidence of tuning, not of a working instrument." This is where that promise
gets kept.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from heatguard import tools  # noqa: E402

DEFAULT_DATE = "2025-07-15"
THRESHOLDS_F = (91.0, 103.0)


def load_roster() -> dict[str, dict]:
    with (ROOT / "config" / "sites.csv").open(newline="", encoding="utf-8") as fh:
        rows = {r["site_id"]: dict(r) for r in csv.DictReader(fh)}
    geo = json.loads((ROOT / "config" / "sites.geojson").read_text(encoding="utf-8"))
    for f in geo["features"]:
        rows[f["properties"]["site_id"]]["aoi"] = {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {}, "geometry": f["geometry"]}],
        }
        rows[f["properties"]["site_id"]]["centroid"] = f["properties"]["centroid"]
    return rows


def gather(date: str) -> list[dict]:
    """Read every site's cached numbers. Offline — CacheMiss means it was never fetched."""
    roster = load_roster()
    out = []
    for site_id, site in roster.items():
        try:
            tcm = tools.heatmap(site["aoi"], date, filter_type=3, analytic_type="tcm")
        except tools.ToolsError:
            continue
        summary = tools.site_summary_f(tcm)
        if summary is None:
            out.append({"site_id": site_id, "name": site["name"], "empty": True,
                        "archetype": site["archetype"],
                        "predicted": site["expected_profile"]})
            continue

        row = {
            "site_id": site_id, "name": site["name"], "empty": False,
            "archetype": site["archetype"], "predicted": site["expected_profile"],
            "crew": int(site["crew_size"]),
            "night": site["night_shift"] == "True",
            "peak_f": summary["max_f"], "mean_f": summary["mean_f"],
            "min_f": summary["min_f"], "tiles": summary["n_tiles"],
        }

        lon, lat = site["centroid"]
        humidity = 20.0
        try:
            env = tools.env_params(lat=lat, lon=lon,
                                   air_temp_c=tools.f_to_c(summary["mean_f"]),
                                   date=date, filter_type=3)
            series = ((env.get("locations") or [{}])[0].get("parameters", {})
                      .get("relative_humidity_percent") or [])
            values = [v for v in series if v is not None]
            if values:
                humidity = sum(values) / len(values)
        except tools.ToolsError:
            pass
        row["humidity"] = humidity

        for threshold_f in THRESHOLDS_F:
            threshold_c = tools.air_temp_c_for_heat_index_f(threshold_f, humidity)
            try:
                res = tools.heatmap(site["aoi"], date, filter_type=3,
                                    analytic_type="exceedance",
                                    threshold_c=round(threshold_c, 2), direction="above")
                hours = tools.tile_hours(res)
                row[f"hours_{threshold_f:.0f}"] = (sum(hours) / len(hours)) if hours else None
            except tools.ToolsError:
                row[f"hours_{threshold_f:.0f}"] = None
        out.append(row)
    return out


def spread(values: list[float]) -> float:
    return max(values) - min(values)


def main(date: str) -> int:
    rows = gather(date)
    good = [r for r in rows if not r["empty"] and r.get("hours_103") is not None]
    empty = [r for r in rows if r["empty"]]

    print("=" * 100)
    print(f"DEMO DAY ANALYSIS — {date}   ({len(good)} sites with data, "
          f"{len(empty)} empty)")
    print("=" * 100)
    if empty:
        print("COVERAGE GAPS (Completed, zero tiles, billed anyway):")
        for r in empty:
            print(f"   {r['site_id']:<11} {r['name']}")
        print()

    print(f"{'site':<11}{'archetype':<20}{'peak °F':>9}{'mean °F':>9}"
          f"{'h>91HI':>8}{'h>103HI':>9}{'crew':>6}{'tiles':>7}  predicted")
    for r in sorted(good, key=lambda x: -x["peak_f"]):
        print(f"{r['site_id']:<11}{r['archetype']:<20}{r['peak_f']:>9.1f}"
              f"{r['mean_f']:>9.1f}{r['hours_91']:>8.1f}{r['hours_103']:>9.1f}"
              f"{r['crew']:>6}{r['tiles']:>7}  {r['predicted']}")

    # ------------------------------------------------------- 1. the thesis
    peaks = [r["peak_f"] for r in good]
    h103 = [r["hours_103"] for r in good]
    h91 = [r["hours_91"] for r in good]

    peak_spread = spread(peaks)
    h103_spread = spread(h103)
    print()
    print("=" * 100)
    print("1. DOES PEAK CONVERGE WHILE DURATION SEPARATES?")
    print("=" * 100)
    print(f"   peak            {min(peaks):6.1f} .. {max(peaks):6.1f} °F   "
          f"spread {peak_spread:5.2f} °F  ({peak_spread * 5 / 9:.2f} °C)   "
          f"relative {peak_spread / max(peaks) * 100:5.2f}%")
    print(f"   hours > 103 HI  {min(h103):6.1f} .. {max(h103):6.1f} h    "
          f"spread {h103_spread:5.2f} h                relative "
          f"{h103_spread / max(h103) * 100:5.1f}%")
    print(f"   hours >  91 HI  {min(h91):6.1f} .. {max(h91):6.1f} h    "
          f"spread {spread(h91):5.2f} h                relative "
          f"{spread(h91) / max(h91) * 100:5.1f}%")
    ratio = (h103_spread / max(h103)) / (peak_spread / max(peaks))
    print(f"\n   >>> duration discriminates {ratio:.0f}x better than peak, in relative terms")
    print(f"   >>> FortyGuard's own case study: 0.7 °C peak spread across six parcels "
          f"vs 19 h exceedance")
    print(f"   >>> ours: {peak_spread * 5 / 9:.2f} °C peak spread across {len(good)} "
          f"sites vs {h103_spread:.1f} h")

    # ------------------------------------------------------- 2. inversions
    print()
    print("=" * 100)
    print("2. INVERSIONS — higher peak, FEWER hours above threshold")
    print("=" * 100)
    found = []
    for a in good:
        for b in good:
            if a["peak_f"] > b["peak_f"] and b["hours_103"] > a["hours_103"]:
                found.append((a, b, a["peak_f"] - b["peak_f"],
                              b["hours_103"] - a["hours_103"]))
    if found:
        for a, b, dpeak, dhours in sorted(found, key=lambda x: -x[3]):
            print(f"   {a['site_id']:<11} peaks {dpeak:+.1f} °F HIGHER than "
                  f"{b['site_id']:<11} but spends {dhours:.1f} h LESS above threshold")
    else:
        print("   none at 103 °F HI")

    ties = [(a, b) for a in good for b in good
            if a["site_id"] < b["site_id"]
            and abs(a["peak_f"] - b["peak_f"]) < 0.15
            and abs(a["hours_103"] - b["hours_103"]) >= 1.0]
    if ties:
        print("\n   SAME PEAK, DIFFERENT DURATION (indistinguishable by peak alone):")
        for a, b in ties:
            print(f"   {a['site_id']:<11} and {b['site_id']:<11} peak within 0.15 °F, "
                  f"but {abs(a['hours_103'] - b['hours_103']):.1f} h apart")

    # ------------------------------------------------------- 3. predictions
    print()
    print("=" * 100)
    print("3. DID THE T1 PREDICTIONS HOLD? (docs/site_selection.md promised to report this)")
    print("=" * 100)
    median_peak = sorted(peaks)[len(peaks) // 2]
    median_hours = sorted(h103)[len(h103) // 2]

    def observed(r: dict) -> str:
        hi_peak = r["peak_f"] >= median_peak
        long_tail = r["hours_103"] >= median_hours
        if hi_peak and long_tail:
            return "high_peak_long_tail"
        if hi_peak and not long_tail:
            return "high_peak_fast_cool"
        if not hi_peak and long_tail:
            return "clipped_peak_long_tail"
        return "depressed_peak"

    hits = 0
    for r in sorted(good, key=lambda x: x["site_id"]):
        obs = observed(r)
        ok = obs == r["predicted"]
        hits += ok
        print(f"   {r['site_id']:<11} predicted {r['predicted']:<24} "
              f"observed {obs:<24} {'HIT' if ok else 'MISS'}")
    print(f"\n   {hits}/{len(good)} predictions correct "
          f"({hits / len(good) * 100:.0f}%) — chance would be ~25%")

    out = ROOT / "data" / "fixtures" / "t8" / f"analysis_{date}.json"
    out.write_text(json.dumps({
        "date": date, "rows": good, "empty": [r["site_id"] for r in empty],
        "peak_spread_f": peak_spread, "hours_103_spread": h103_spread,
        "hours_91_spread": spread(h91), "discrimination_ratio": ratio,
        "inversions": [{"higher_peak": a["site_id"], "longer_duration": b["site_id"],
                        "peak_delta_f": round(dp, 2), "hours_delta": round(dh, 2)}
                       for a, b, dp, dh in found],
        "predictions_correct": hits, "predictions_total": len(good),
    }, indent=2) + "\n", encoding="utf-8")
    print(f"\nwritten to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DATE))
