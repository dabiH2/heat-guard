"""
build_demo_cache.py — fetch everything the live demo needs, once, and commit it.

Run:  python scripts/build_demo_cache.py [YYYY-MM-DD ...]

The deployed app runs with HEATGUARD_OFFLINE=1 and serves entirely from
data/fixtures/api/. That is deliberate: the FortyGuard key expires 2026-09-21 and judging
runs to 2026-09-16, so a demo that depends on the API being reachable is a demo that dies
during judging. It also means the deployed app needs no key at all — nothing to leak into
a public Streamlit deployment, nothing to appear in a video frame.

The consequence is that whatever the demo shows has to be in the cache BEFORE deploy.
This script is the "before".

Per site, per date: tcm (the peak), exceedance (the duration), env_params (the humidity
the heat-index -> air-temperature conversion needs). Re-running is free — cached calls
return without spending anything — so this is safe to resume after an interruption, which
matters because API latency degraded to ~230 s per call during deadline week and a full
pass takes hours.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")

from heatguard import tools  # noqa: E402
from heatguard.bands import load_thresholds  # noqa: E402

DEFAULT_DATES = ["2025-07-15"]

# Both thresholds, because T2 requires the headline number at 91 AND 103 — the free
# weather shortlist showed 91 °F saturates on the hottest Phoenix nights (24 of 24 hours
# above at every site), and a saturated metric cannot discriminate.
THRESHOLDS_F = (91.0, 103.0)


def aoi_of(feature: dict) -> dict:
    return {"type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {},
                          "geometry": feature["geometry"]}]}


def main(dates: list[str]) -> int:
    geo = json.loads((ROOT / "config" / "sites.geojson").read_text(encoding="utf-8"))
    features = {f["properties"]["site_id"]: f for f in geo["features"]}

    start_credits = tools.credits_remaining()
    planned = len(features) * len(dates) * (1 + len(THRESHOLDS_F) + 1)
    print(f"credits remaining : {start_credits:,}")
    print(f"sites             : {len(features)}")
    print(f"dates             : {', '.join(dates)}")
    print(f"calls if none cached: {planned} "
          f"(~{planned * tools.CREDITS_PER_HEATMAP_CALL:,} credits, "
          f"~{planned * 230 / 3600:.1f} h at current latency)")
    print("cached calls are free and instant — re-running resumes\n")

    began = time.monotonic()
    done = 0
    for date in dates:
        for site_id, feature in features.items():
            aoi = aoi_of(feature)
            lon, lat = feature["properties"]["centroid"]
            print(f"[{date}] {site_id}")

            try:
                tcm = tools.heatmap(aoi, date, filter_type=3, analytic_type="tcm",
                                    label=f"demo-tcm:{site_id}:{date}")
                summary = tools.site_summary_f(tcm)
                done += 1
                if summary is None:
                    print("    tcm         EMPTY — coverage gap, skipping the rest")
                    continue
                print(f"    tcm         peak {summary['max_f']:6.1f} °F   "
                      f"mean {summary['mean_f']:6.1f} °F   {summary['n_tiles']} tiles")
            except tools.ToolsError as exc:
                print(f"    tcm         FAILED: {str(exc)[:70]}")
                continue

            # Humidity, for the heat-index -> air-temperature conversion.
            humidity = 20.0
            try:
                env = tools.env_params(lat=lat, lon=lon,
                                       air_temp_c=tools.f_to_c(summary["mean_f"]),
                                       date=date, filter_type=3,
                                       label=f"demo-env:{site_id}:{date}")
                done += 1
                series = ((env.get("locations") or [{}])[0].get("parameters", {})
                          .get("relative_humidity_percent") or [])
                values = [v for v in series if v is not None]
                if values:
                    humidity = sum(values) / len(values)
                print(f"    env_params  humidity {humidity:4.1f}%")
            except tools.ToolsError as exc:
                print(f"    env_params  unavailable ({str(exc)[:44]}) — using 20%")

            for threshold_f in THRESHOLDS_F:
                threshold_c = tools.air_temp_c_for_heat_index_f(threshold_f, humidity)
                try:
                    exc_result = tools.heatmap(
                        aoi, date, filter_type=3, analytic_type="exceedance",
                        threshold_c=round(threshold_c, 2), direction="above",
                        label=f"demo-exc{threshold_f:.0f}:{site_id}:{date}")
                    done += 1
                    hours = tools.tile_hours(exc_result)
                    mean_hours = sum(hours) / len(hours) if hours else 0.0
                    print(f"    exceedance  {threshold_f:.0f} °F HI "
                          f"= {tools.c_to_f(threshold_c):5.1f} °F air "
                          f"({threshold_c:5.2f} °C)  ->  {mean_hours:5.1f} h")
                except tools.ToolsError as exc:
                    print(f"    exceedance  {threshold_f:.0f} °F FAILED: {str(exc)[:50]}")

            elapsed = time.monotonic() - began
            print(f"    ({done} calls, {elapsed / 60:.0f} min elapsed)\n")

    end_credits = tools.credits_remaining()
    print("=" * 72)
    print(f"credits: {start_credits:,} -> {end_credits:,} "
          f"(spent {start_credits - end_credits:,})")
    print(f"cache:   {len(list(tools.CACHE_DIR.glob('v1-*.json')))} responses, "
          f"{len(tools.cache_index())} indexed")
    print(f"elapsed: {(time.monotonic() - began) / 60:.0f} min")
    print("\nCommit data/fixtures/api/ — it is the demo's data source after the key dies.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or DEFAULT_DATES))
