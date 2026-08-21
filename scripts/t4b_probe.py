"""
t4b_probe.py — T4 follow-up on the two questions the first pass left open.

1. IS THERE A FORECAST AT ALL? The far-future probe was rejected with "Requests must be
   for a past or present date." CLAUDE.md says the heatmap forecasts to now + 12 h. Those
   cannot both be true, and the router's FORECAST row depends on the answer: if there is
   no forecast, answering a forward-looking question with this endpoint returns history
   dressed as a prediction — precisely the failure this project exists to prevent.

2. Does the pre-2021 request ever terminate, or does it hang forever? A third failure
   mode — neither loud nor silent, just never finished — would block a naive poller.

Rejections at submit cost nothing, so most of this is free.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from heatguard.tools import BASE_URL  # noqa: E402

OUT = ROOT / "data" / "fixtures" / "t4"
load_dotenv(ROOT / ".env")
API_KEY = os.environ["FORTYGUARD_API_KEY"]
session = requests.Session()
session.headers.update({"api-key": API_KEY, "Content-Type": "application/json"})


def aoi_for(site_id: str) -> dict:
    fc = json.loads((ROOT / "config" / "sites.geojson").read_text(encoding="utf-8"))
    f = next(x for x in fc["features"] if x["properties"]["site_id"] == site_id)
    return {"type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {}, "geometry": f["geometry"]}]}


AOI = aoi_for("PHX-ENCA")
now = datetime.now(timezone.utc)
findings: dict = {}

print("=" * 78)
print("1. IS THERE A FORECAST? — submit-only, rejections are free")
print("=" * 78)
print(f"   now (UTC): {now.isoformat()}\n")

cases = [
    ("yesterday",        (now - timedelta(days=1)).date().isoformat(), 3, None),
    ("today_whole_day",  now.date().isoformat(),                       3, None),
    ("today_hour_now",   now.date().isoformat(),                       1, f"{now.hour:02d}:00"),
    ("today_hour_plus6", now.date().isoformat(),                       1,
     f"{(now + timedelta(hours=6)).hour:02d}:00"),
    ("tomorrow",         (now + timedelta(days=1)).date().isoformat(), 3, None),
]

for label, date, filter_type, start_time in cases:
    dt: dict = {"start_date": date, "filter_type": filter_type}
    if start_time:
        dt["start_time"] = start_time
    r = session.post(f"{BASE_URL}/v1/heatmap", json={
        "polygon_aoi": AOI, "date_time": dt, "granularity": 100, "analytic_type": "tcm",
    }, timeout=60)
    try:
        body = r.json()
    except ValueError:
        body = {"non_json": r.text[:200]}
    accepted = bool((body.get("data") or {}).get("activity_id"))
    findings[label] = {
        "date": date, "filter_type": filter_type, "start_time": start_time,
        "http": r.status_code, "accepted": accepted,
        "message": str(body.get("message"))[:220],
    }
    verdict = "ACCEPTED" if accepted else "REJECTED"
    print(f"  {label:<18} {date} ft={filter_type} "
          f"{'t=' + start_time if start_time else '':<8} "
          f"-> HTTP {r.status_code}  {verdict}")
    if not accepted:
        print(f"       {str(body.get('message'))[:190]}")
    time.sleep(1)

print()
print("=" * 78)
print("2. DOES THE PRE-2021 REQUEST EVER TERMINATE?")
print("=" * 78)
prior = json.loads((OUT / "t4_probes.json").read_text(encoding="utf-8"))
stuck = prior["results"].get("date_before_2021", {}).get("activity_id")
if stuck:
    print(f"   re-polling {stuck} (submitted ~10 min ago)")
    r = session.get(f"{BASE_URL}/v1/status/{stuck}", timeout=60)
    body = r.json()
    data = body.get("data") or {}
    print(f"   HTTP {r.status_code}  status={data.get('status')!r}  "
          f"message={str(body.get('message'))[:160]}")
    findings["pre_2021_recheck"] = {
        "activity_id": stuck, "http": r.status_code,
        "status": data.get("status"), "message": str(body.get("message"))[:220],
        "has_result": "result" in data,
    }
    if "result" in data:
        res = data["result"]
        feats = (res.get("map_data") or {}).get("features", [])
        print(f"   result present: {len(feats)} tiles")
        findings["pre_2021_recheck"]["n_tiles"] = len(feats)
else:
    print("   no activity_id recorded")

print()
print("=" * 78)
print("3. CREDIT COST BREAKDOWN")
print("=" * 78)
r = session.post(f"{BASE_URL}/v1/system/fetch-api-key-usage",
                 json={"api_key": API_KEY}, timeout=60)
usage = r.json()
cs = usage["credit_summary"]
print(f"   used={cs['cycle_credits_used']:,}  remaining={cs['cycle_remaining_credits']:,}")
print("   activity breakdown:")
for row in usage.get("activity_breakdown", []):
    print(f"     {row.get('name'):<28} credits={row.get('credits'):>10,}  "
          f"count={row.get('count')}")
findings["usage"] = usage

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "t4b_forecast_and_costs.json").write_text(
    json.dumps(findings, indent=2).replace(API_KEY, "<FORTYGUARD_API_KEY>") + "\n",
    encoding="utf-8")
print(f"\nwritten to data/fixtures/t4/t4b_forecast_and_costs.json")
