"""
t4c_forecast.py — where exactly does the forecast horizon end, and is it real data?

`tomorrow` was ACCEPTED at submit while `2030-07-15` was rejected as "in the future".
Both cannot be right about a 12 h horizon, and ACCEPTED does not mean ANSWERED — the
non-US probe was also accepted, ran to `completed`, returned zero tiles and still cost
4,220 credits.

So two questions, in order:
  A. Where is the rejection boundary? Rejections at submit are free, so this is cheap.
  B. Inside the accepted range, does a future date return REAL tiles or an empty shell?
     This is the one that matters for the router's FORECAST row.
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

fc = json.loads((ROOT / "config" / "sites.geojson").read_text(encoding="utf-8"))
feat = next(x for x in fc["features"] if x["properties"]["site_id"] == "PHX-ENCA")
AOI = {"type": "FeatureCollection",
       "features": [{"type": "Feature", "properties": {}, "geometry": feat["geometry"]}]}

now = datetime.now(timezone.utc)
findings: dict = {"probed_at": now.isoformat(), "acceptance": {}, "data_quality": {}}


def submit(date: str) -> tuple[int, bool, str, str | None]:
    r = session.post(f"{BASE_URL}/v1/heatmap", json={
        "polygon_aoi": AOI,
        "date_time": {"start_date": date, "filter_type": 3},
        "granularity": 100, "analytic_type": "tcm",
    }, timeout=60)
    try:
        body = r.json()
    except ValueError:
        return r.status_code, False, r.text[:180], None
    aid = (body.get("data") or {}).get("activity_id")
    return r.status_code, bool(aid), str(body.get("message"))[:200], aid


print("=" * 78)
print("A. ACCEPTANCE BOUNDARY (rejections are free)")
print("=" * 78)
offsets = [0, 1, 2, 3, 7, 14, 30, 90, 365]
accepted_ids: dict[int, str] = {}
for days in offsets:
    date = (now + timedelta(days=days)).date().isoformat()
    code, ok, msg, aid = submit(date)
    findings["acceptance"][f"+{days}d"] = {
        "date": date, "http": code, "accepted": ok, "message": msg,
    }
    print(f"  +{days:>3}d  {date}  HTTP {code}  {'ACCEPTED' if ok else 'REJECTED'}")
    if not ok:
        print(f"          {msg[:150]}")
    else:
        accepted_ids[days] = aid
    time.sleep(1)

accepted = [d for d in offsets if findings["acceptance"][f"+{d}d"]["accepted"]]
rejected = [d for d in offsets if not findings["acceptance"][f"+{d}d"]["accepted"]]
print(f"\n  accepted offsets: {accepted}")
print(f"  rejected offsets: {rejected}")
if accepted and rejected:
    print(f"  boundary lies between +{max(accepted)}d and +{min(rejected)}d")


print()
print("=" * 78)
print("B. IS FUTURE-DATED DATA REAL? (already paid for at submit)")
print("=" * 78)


def poll(aid: str, budget_s: int = 240) -> dict:
    t0, delay = time.monotonic(), 3
    while time.monotonic() - t0 < budget_s:
        time.sleep(delay)
        delay = min(delay * 2, 12)
        r = session.get(f"{BASE_URL}/v1/status/{aid}", timeout=60)
        if r.status_code == 404:
            continue
        body = r.json()
        data = body.get("data") or {}
        status = str(data.get("status", "")).lower()
        if status in ("succeeded", "completed"):
            return {"status": status, "result": data.get("result", data)}
        if status in ("failed", "error"):
            return {"status": status, "message": str(body.get("message"))[:200]}
    return {"status": "timeout"}


for days in sorted(accepted_ids):
    if days not in (0, 1, 3, 7):     # keep the spend contained
        continue
    aid = accepted_ids[days]
    print(f"\n  +{days}d  polling {aid}")
    outcome = poll(aid)
    entry = {"offset_days": days, "status": outcome["status"]}
    res = outcome.get("result") or {}
    feats = (res.get("map_data") or {}).get("features", [])
    ts = (res.get("stats_data") or {}).get("temperature_stats") or {}
    entry["n_tiles"] = len(feats)
    entry["temperature_stats"] = ts
    if feats:
        p = feats[0]["properties"]
        entry["tile0"] = p
        print(f"     status={outcome['status']}  tiles={len(feats)}  "
              f"avg={p.get('average_temperature')}  "
              f"min={p.get('min_temperature')}  max={p.get('max_temperature')}")
    else:
        print(f"     status={outcome['status']}  tiles=0  <- EMPTY SHELL, still billed")
    findings["data_quality"][f"+{days}d"] = entry

r = session.post(f"{BASE_URL}/v1/system/fetch-api-key-usage",
                 json={"api_key": API_KEY}, timeout=60)
cs = r.json()["credit_summary"]
findings["credits_after"] = cs
print(f"\ncredits used={cs['cycle_credits_used']:,}  "
      f"remaining={cs['cycle_remaining_credits']:,}")

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "t4c_forecast_horizon.json").write_text(
    json.dumps(findings, indent=2).replace(API_KEY, "<FORTYGUARD_API_KEY>") + "\n",
    encoding="utf-8")
print("written to data/fixtures/t4/t4c_forecast_horizon.json")
