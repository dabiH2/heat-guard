"""
t5_validate.py — prove tools.py end to end against the live API.

Run:  python scripts/t5_validate.py

Costs ONE heatmap call (4,220 credits). The second call must be served from cache for
zero, which is the whole point: after the key expires on 2026-09-21 the cache IS the
data source, so it has to work before then, not after.
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
from heatguard.bands import action_for, band_for, load_thresholds  # noqa: E402

SITE = "PHX-CHASE"        # the lead demo site: downtown canyon, night crew
DATE = "2025-07-15"


def aoi_for(site_id: str) -> dict:
    fc = json.loads((ROOT / "config" / "sites.geojson").read_text(encoding="utf-8"))
    f = next(x for x in fc["features"] if x["properties"]["site_id"] == site_id)
    return {"type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {}, "geometry": f["geometry"]}]}


aoi = aoi_for(SITE)
before = tools.credits_remaining()
print(f"credits remaining: {before:,}\n")

print("=" * 72)
print(f"1. LIVE CALL — {SITE} {DATE} tcm")
print("=" * 72)
result = tools.heatmap(aoi, DATE, filter_type=3, analytic_type="tcm", label="t5-validate")
summary = tools.site_summary_f(result)
print(f"  tiles: {summary['n_tiles']}")
print(f"  min {summary['min_f']:.1f} °F · mean {summary['mean_f']:.1f} °F · "
      f"max {summary['max_f']:.1f} °F")
print(f"  peak band: {band_for(summary['max_f']).id}")
print(f"  peak action: {action_for(summary['max_f']).action}")

after_live = tools.credits_remaining()
print(f"\n  credits: {before:,} -> {after_live:,}  (spent {before - after_live:,})")

print()
print("=" * 72)
print("2. SAME CALL AGAIN — must come from cache, must cost nothing")
print("=" * 72)
again = tools.heatmap(aoi, DATE, filter_type=3, analytic_type="tcm")
after_cached = tools.credits_remaining()
print(f"  identical result: {again == result}")
print(f"  credits: {after_live:,} -> {after_cached:,}  "
      f"(spent {after_live - after_cached:,})")
assert again == result, "cache returned something different"
assert after_cached == after_live, "cached call spent credits"

print()
print("=" * 72)
print("3. OFFLINE MODE — cache hit works, miss raises")
print("=" * 72)
import os  # noqa: E402

os.environ["HEATGUARD_OFFLINE"] = "1"
offline_hit = tools.heatmap(aoi, DATE, filter_type=3, analytic_type="tcm")
print(f"  cached call while offline: OK ({len(tools.tile_temperatures_c(offline_hit))} tiles)")
try:
    tools.heatmap(aoi, "2025-06-01", filter_type=3, analytic_type="tcm")
    print("  ERROR: uncached offline call did not raise")
except tools.CacheMiss as exc:
    print(f"  uncached call while offline raised CacheMiss: {str(exc)[:90]}...")
os.environ.pop("HEATGUARD_OFFLINE")

print()
print("=" * 72)
print("4. UNIT GUARD — the trap is refused before it reaches the wire")
print("=" * 72)
try:
    tools.heatmap(aoi, DATE, filter_type=3, analytic_type="exceedance",
                  threshold_c=95.0, direction="above")
    print("  ERROR: the Fahrenheit threshold was not caught")
except tools.UnitError as exc:
    print(f"  refused: {str(exc)[:120]}...")

t = load_thresholds()
print(f"\n  OSHA threshold {t.unsafe_from_f} °F -> {tools.f_to_c(t.unsafe_from_f):.2f} °C")
print(f"  cache dir: {tools.CACHE_DIR.relative_to(ROOT)}")
print(f"  activity log: {tools.ACTIVITY_LOG.relative_to(ROOT)}")
if tools.ACTIVITY_LOG.exists():
    lines = tools.ACTIVITY_LOG.read_text(encoding="utf-8").strip().splitlines()
    print(f"  logged activities: {len(lines)}")
    print(f"    last: {lines[-1][:130]}")
