"""
t4_probe.py — T4. Turn every documented constraint into an observed fact.

Run:  python scripts/t4_probe.py

The column that matters is not "does it fail" but "does it fail LOUDLY". A loud failure
is a bug caught; a silent, plausible one is a bug shipped. Failed tasks cost nothing, so
these are probed deliberately.

Part 2 is the important one: the same exceedance call twice, differing only in whether
the threshold was converted from Fahrenheit. It is the project's whole thesis, executed
live against the vendor's own API, and it is the strongest artefact the demo can carry.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from heatguard.tools import BASE_URL, c_to_f, f_to_c  # noqa: E402

OUT = ROOT / "data" / "fixtures" / "t4"
SITES_GEOJSON = ROOT / "config" / "sites.geojson"

SITE = "PHX-ENCA"
DATE = "2025-07-15"

load_dotenv(ROOT / ".env")
API_KEY = os.environ.get("FORTYGUARD_API_KEY", "")
if not API_KEY or API_KEY == "paste_key_here":
    raise SystemExit("FORTYGUARD_API_KEY is not set in .env")


def mask(t: str) -> str:
    return t.replace(API_KEY, "<FORTYGUARD_API_KEY>")


def save(name: str, obj):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(mask(json.dumps(obj, indent=2)) + "\n", encoding="utf-8")


session = requests.Session()
session.headers.update({"api-key": API_KEY, "Content-Type": "application/json"})


def aoi_for(site_id: str) -> dict:
    fc = json.loads(SITES_GEOJSON.read_text(encoding="utf-8"))
    f = next(x for x in fc["features"] if x["properties"]["site_id"] == site_id)
    return {"type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {}, "geometry": f["geometry"]}]}


def shift_aoi(aoi: dict, dlat: float, dlon: float) -> dict:
    """Move a polygon somewhere else on Earth — for the non-US probe."""
    out = json.loads(json.dumps(aoi))
    ring = out["features"][0]["geometry"]["coordinates"][0]
    out["features"][0]["geometry"]["coordinates"][0] = [
        [lon + dlon, lat + dlat] for lon, lat in ring
    ]
    return out


def scale_aoi(aoi: dict, factor: float) -> dict:
    """Blow a polygon up around its centroid — for the oversized-AOI probe."""
    out = json.loads(json.dumps(aoi))
    ring = out["features"][0]["geometry"]["coordinates"][0]
    clon = sum(p[0] for p in ring[:-1]) / (len(ring) - 1)
    clat = sum(p[1] for p in ring[:-1]) / (len(ring) - 1)
    out["features"][0]["geometry"]["coordinates"][0] = [
        [clon + (lon - clon) * factor, clat + (lat - clat) * factor] for lon, lat in ring
    ]
    return out


def credits() -> tuple[int, int]:
    r = session.post(f"{BASE_URL}/v1/system/fetch-api-key-usage",
                     json={"api_key": API_KEY}, timeout=60)
    cs = r.json()["credit_summary"]
    return cs["cycle_credits_used"], cs["cycle_remaining_credits"]


def run(label: str, payload: dict, *, timeout_s: int = 300) -> dict:
    """Submit, poll to terminal, and report exactly how it behaved."""
    t0 = time.monotonic()
    r = session.post(f"{BASE_URL}/v1/heatmap", json=payload, timeout=60)
    outcome: dict = {"label": label, "submit_http": r.status_code}
    try:
        body = r.json()
    except ValueError:
        outcome["submit_body"] = mask(r.text[:400])
        outcome["verdict"] = "LOUD — non-JSON response at submit"
        print(f"  submit HTTP {r.status_code} — non-JSON")
        return outcome

    outcome["submit_error_flag"] = body.get("error")
    outcome["submit_message"] = body.get("message")

    activity_id = (body.get("data") or {}).get("activity_id")
    if not activity_id:
        outcome["verdict"] = "LOUD — rejected at submit, no credit consumed"
        outcome["submit_body"] = body
        print(f"  submit HTTP {r.status_code}  error={body.get('error')}  "
              f"msg={mask(str(body.get('message')))[:120]}")
        return outcome

    outcome["activity_id"] = activity_id
    print(f"  submitted {activity_id}")

    delay = 3
    while time.monotonic() - t0 < timeout_s:
        time.sleep(delay)
        delay = min(delay * 2, 12)
        s = session.get(f"{BASE_URL}/v1/status/{activity_id}", timeout=60)
        if s.status_code == 404:
            print(f"    t+{time.monotonic() - t0:5.1f}s  404 (not visible yet)")
            outcome["saw_404_window"] = True
            continue
        sb = s.json()
        data = sb.get("data") or {}
        status = str(data.get("status", "")).lower()
        print(f"    t+{time.monotonic() - t0:5.1f}s  {status!r}")
        if status in ("succeeded", "completed"):
            outcome["status"] = status
            outcome["elapsed_s"] = round(time.monotonic() - t0, 1)
            outcome["result"] = data.get("result", data)
            return outcome
        if status in ("failed", "error"):
            outcome["status"] = status
            outcome["elapsed_s"] = round(time.monotonic() - t0, 1)
            outcome["message"] = mask(str(data.get("message") or sb.get("message")))
            outcome["verdict"] = "LOUD — task failed after submit"
            return outcome
    outcome["verdict"] = "TIMEOUT"
    return outcome


def summarise(outcome: dict) -> str:
    res = outcome.get("result") or {}
    stats = res.get("stats_data") or {}
    feats = (res.get("map_data") or {}).get("features", [])
    if "analytic_type" in stats:
        vals = [f["properties"].get("value") for f in feats
                if f.get("properties", {}).get("value") is not None]
        lo = min(vals) if vals else None
        hi = max(vals) if vals else None
        return (f"analytic_type={stats.get('analytic_type')} units={stats.get('units')} "
                f"n_cells={stats.get('n_cells')} min={stats.get('min')} "
                f"max={stats.get('max')} mean={stats.get('mean')} "
                f"| tile values {lo}..{hi}")
    ts = stats.get("temperature_stats") or {}
    return (f"tcm tiles={len(feats)} min={ts.get('minimum')} max={ts.get('maximum')} "
            f"mean={ts.get('mean')}")


BASE_AOI = aoi_for(SITE)
results: dict[str, dict] = {}

used_before, remaining_before = credits()
print("=" * 78)
print(f"credits before: used={used_before:,}  remaining={remaining_before:,}")
print("=" * 78)


# ===================================================== 1. exceedance, done correctly
print("\n1. EXCEEDANCE with a correctly-converted Celsius threshold")
print("-" * 78)
THRESHOLD_F = 95.0
threshold_c = f_to_c(THRESHOLD_F)
print(f"   OSHA-style threshold {THRESHOLD_F} F -> {threshold_c:.2f} C  (what we send)")
results["exceedance_correct"] = run("exceedance_correct", {
    "polygon_aoi": BASE_AOI,
    "date_time": {"start_date": DATE, "filter_type": 3},
    "granularity": 100,
    "analytic_type": "exceedance",
    "threshold": round(threshold_c, 2),
    "direction": "above",
})
print("  ->", summarise(results["exceedance_correct"]))


# ============================================================== 2. THE UNIT TRAP
print("\n2. THE UNIT TRAP — identical call, threshold passed as if it were Fahrenheit")
print("-" * 78)
print(f"   sending threshold={THRESHOLD_F} — the API reads it as "
      f"{THRESHOLD_F} C = {c_to_f(THRESHOLD_F):.1f} F")
results["exceedance_unit_trap"] = run("exceedance_unit_trap", {
    "polygon_aoi": BASE_AOI,
    "date_time": {"start_date": DATE, "filter_type": 3},
    "granularity": 100,
    "analytic_type": "exceedance",
    "threshold": THRESHOLD_F,          # <- the bug, expressed in one number
    "direction": "above",
})
print("  ->", summarise(results["exceedance_unit_trap"]))


# ==================================================================== 3. persistence
print("\n3. PERSISTENCE — longest continuous run, same correct threshold")
print("-" * 78)
results["persistence"] = run("persistence", {
    "polygon_aoi": BASE_AOI,
    "date_time": {"start_date": DATE, "filter_type": 3},
    "granularity": 100,
    "analytic_type": "persistence",
    "threshold": round(threshold_c, 2),
    "direction": "above",
})
print("  ->", summarise(results["persistence"]))


# =============================================================== 4. constraint probes
print("\n4. CONSTRAINT PROBES — do they fail loudly or quietly?")
print("-" * 78)

PROBES = [
    ("non_us_milan", {
        "polygon_aoi": shift_aoi(BASE_AOI, 45.46 - 33.47, 9.19 + 112.09),
        "date_time": {"start_date": DATE, "filter_type": 3},
        "granularity": 100, "analytic_type": "tcm"}),
    ("date_before_2021", {
        "polygon_aoi": BASE_AOI,
        "date_time": {"start_date": "2019-07-15", "filter_type": 3},
        "granularity": 100, "analytic_type": "tcm"}),
    ("far_future_2030", {
        "polygon_aoi": BASE_AOI,
        "date_time": {"start_date": "2030-07-15", "filter_type": 3},
        "granularity": 100, "analytic_type": "tcm"}),
    ("filter_type_5_single_month", {
        "polygon_aoi": BASE_AOI,
        "date_time": {"start_date": "2025-07-01", "filter_type": 5},
        "granularity": 100, "analytic_type": "tcm"}),
    ("granularity_10m", {
        "polygon_aoi": BASE_AOI,
        "date_time": {"start_date": DATE, "filter_type": 3},
        "granularity": 10, "analytic_type": "tcm"}),
    ("aoi_oversized", {
        "polygon_aoi": scale_aoi(BASE_AOI, 60.0),      # ~0.124 km2 * 3600 = ~447 km2
        "date_time": {"start_date": DATE, "filter_type": 3},
        "granularity": 100, "analytic_type": "tcm"}),
    ("exceedance_missing_threshold", {
        "polygon_aoi": BASE_AOI,
        "date_time": {"start_date": DATE, "filter_type": 3},
        "granularity": 100, "analytic_type": "exceedance", "direction": "above"}),
    ("range_over_30_days", {
        "polygon_aoi": BASE_AOI,
        "date_time": {"start_date": "2025-06-01", "end_date": "2025-07-31",
                      "filter_type": 4},
        "granularity": 100, "analytic_type": "tcm"}),
]

for name, payload in PROBES:
    print(f"\n  [{name}]")
    results[name] = run(name, payload, timeout_s=180)
    if results[name].get("result"):
        print("  ->", summarise(results[name]))


used_after, remaining_after = credits()
print()
print("=" * 78)
print(f"credits after : used={used_after:,}  remaining={remaining_after:,}")
print(f"CONSUMED BY THIS RUN: {used_after - used_before:,} credits "
      f"across {len(results)} submissions")
print("=" * 78)

save("t4_probes.json", {
    "credits_before": {"used": used_before, "remaining": remaining_before},
    "credits_after": {"used": used_after, "remaining": remaining_after},
    "results": results,
})
print(f"\nwritten to {(OUT / 't4_probes.json').relative_to(ROOT)}")
