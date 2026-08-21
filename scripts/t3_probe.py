"""
t3_probe.py — T3. First contact with the live API.

Run:  python scripts/t3_probe.py

Three things, in order of cost:
  A. POST /v1/system/fetch-api-key-usage — plan and credit balance. Establishes that
     auth works before anything is spent.
  B. One heatmap call driven MANUALLY — raw POST, then raw GET /v1/status/{id} polling
     with 3/6/12 s backoff — so the activity_id and the status payloads are visible once,
     in full, including the 404 window right after submit that the vendor client hides.
  C. The same call through the vendored client, timed, as a cross-check.

Every raw response is written to data/fixtures/t3/ so T4 and the tests can work offline
and so the demo survives 16 September, when API access is revoked.

THE API KEY IS NEVER PRINTED. `fetch_api_key_usage` sends the key in the POST body and
the response may echo it, so every line printed goes through `mask()` first.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from heatguard.tools import BASE_URL, POLL_BACKOFF_SECONDS  # noqa: E402

OUT = ROOT / "data" / "fixtures" / "t3"
SITES_GEOJSON = ROOT / "config" / "sites.geojson"

# Encanto Park: smallest concern, irrigated, and a site we want data for anyway.
PROBE_SITE = "PHX-ENCA"
PROBE_DATE = "2025-07-15"        # well inside coverage, a real Phoenix summer day
PROBE_FILTER_TYPE = 3            # entire day
PROBE_GRANULARITY = 100          # coarsest, cheapest

load_dotenv(ROOT / ".env")
API_KEY = os.environ.get("FORTYGUARD_API_KEY", "")
if not API_KEY or API_KEY == "paste_key_here":
    raise SystemExit("FORTYGUARD_API_KEY is not set in .env")


def mask(text: str) -> str:
    """Redact the API key from anything on its way to stdout or to a fixture file."""
    return text.replace(API_KEY, "<FORTYGUARD_API_KEY>")


def show(label: str, obj, limit: int = 1200) -> None:
    body = json.dumps(obj, indent=2) if not isinstance(obj, str) else obj
    body = mask(body)
    if len(body) > limit:
        body = body[:limit] + f"\n  ... [{len(body) - limit} more chars]"
    print(f"{label}\n{body}\n")


def save(name: str, obj) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(mask(json.dumps(obj, indent=2)) + "\n", encoding="utf-8")
    return path


def single_site_aoi(site_id: str) -> dict:
    """One site's polygon as the FeatureCollection the API expects."""
    fc = json.loads(SITES_GEOJSON.read_text(encoding="utf-8"))
    feature = next(f for f in fc["features"] if f["properties"]["site_id"] == site_id)
    return {"type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {},
                          "geometry": feature["geometry"]}]}


session = requests.Session()
session.headers.update({"api-key": API_KEY, "Content-Type": "application/json"})


# ============================================================ A. plan and credits

print("=" * 78)
print("A. POST /v1/system/fetch-api-key-usage — plan and credits")
print("=" * 78)

t0 = time.monotonic()
resp = session.post(f"{BASE_URL}/v1/system/fetch-api-key-usage",
                    json={"api_key": API_KEY}, timeout=60)
print(f"HTTP {resp.status_code} in {time.monotonic() - t0:.2f}s")
try:
    usage = resp.json()
except ValueError:
    print(mask(resp.text[:800]))
    raise SystemExit("usage endpoint did not return JSON")

show("raw:", usage)
save("key_usage.json", usage)


# ============================================================ B. manual submit + poll

print("=" * 78)
print(f"B. Manual POST /v1/heatmap then raw polling — {PROBE_SITE} {PROBE_DATE}")
print("=" * 78)

aoi = single_site_aoi(PROBE_SITE)
payload = {
    "polygon_aoi": aoi,
    "date_time": {"start_date": PROBE_DATE, "filter_type": PROBE_FILTER_TYPE},
    "granularity": PROBE_GRANULARITY,
    "analytic_type": "tcm",
}
print(f"payload (aoi ring truncated): filter_type={PROBE_FILTER_TYPE} "
      f"granularity={PROBE_GRANULARITY} analytic_type=tcm")
print(f"aoi ring has {len(aoi['features'][0]['geometry']['coordinates'][0])} points\n")

submitted_at = time.monotonic()
resp = session.post(f"{BASE_URL}/v1/heatmap", json=payload, timeout=60)
print(f"submit -> HTTP {resp.status_code} in {time.monotonic() - submitted_at:.2f}s")
submit_body = resp.json()
show("submit response:", submit_body, limit=600)
save("heatmap_submit.json", submit_body)

activity_id = (submit_body.get("data") or {}).get("activity_id")
if not activity_id:
    raise SystemExit(f"no activity_id in submit response: {mask(str(submit_body))}")
print(f"activity_id = {activity_id}\n")

print("--- polling GET /v1/status/{id} with 3/6/12s backoff ---")
poll_log: list[dict] = []
delays = list(POLL_BACKOFF_SECONDS) + [12] * 60      # 3, 6, 12, then 12s forever
result = None
first_404_seen = False

for attempt, delay in enumerate(delays, start=1):
    time.sleep(delay)
    elapsed = time.monotonic() - submitted_at
    r = session.get(f"{BASE_URL}/v1/status/{activity_id}", timeout=60)
    entry = {"attempt": attempt, "elapsed_s": round(elapsed, 2),
             "http": r.status_code}

    if r.status_code == 404:
        first_404_seen = True
        entry["note"] = "404 — activity not queryable yet (eventual consistency)"
        poll_log.append(entry)
        print(f"  [{attempt}] t+{elapsed:5.1f}s  HTTP 404  (not visible yet)")
        continue

    body = r.json()
    data = body.get("data") or {}
    status = str(data.get("status", "")).lower()
    entry["status"] = status
    entry["keys"] = sorted(data.keys())
    poll_log.append(entry)
    print(f"  [{attempt}] t+{elapsed:5.1f}s  HTTP {r.status_code}  status={status!r}  "
          f"data keys={sorted(data.keys())}")

    if attempt == 1 or status not in ("pending", "running", "in_progress", "queued"):
        show("    raw status payload:", body, limit=700)

    if status in ("succeeded", "completed"):
        result = data.get("result", data)
        entry["terminal"] = True
        break
    if status in ("failed", "error"):
        entry["terminal"] = True
        print(f"  TASK FAILED: {mask(str(body))[:500]}")
        break
    if elapsed > 600:
        print("  giving up after 600s")
        break

total = time.monotonic() - submitted_at
print(f"\nsubmit -> terminal in {total:.1f}s over {len(poll_log)} polls")
print(f"post-submit 404 window observed: {first_404_seen}")
save("heatmap_poll_log.json", poll_log)

if result is not None:
    save("heatmap_tcm_result.json", result)
    stats = result.get("stats_data", {})
    feats = (result.get("map_data") or {}).get("features", [])
    print(f"\nresult: {len(feats)} tiles")
    show("stats_data:", stats, limit=900)
    if feats:
        show("feature[0].properties:", feats[0].get("properties", {}), limit=400)
        vals = [f["properties"].get("average_temperature") for f in feats
                if f.get("properties", {}).get("average_temperature") is not None]
        if vals:
            lo, hi = min(vals), max(vals)
            print(f"average_temperature across tiles: {lo:.2f} .. {hi:.2f}")
            print(f"  read as C -> {lo * 9 / 5 + 32:.1f} .. {hi * 9 / 5 + 32:.1f} F")
            print(f"  read as F -> {(lo - 32) * 5 / 9:.1f} .. {(hi - 32) * 5 / 9:.1f} C")
            print("  Phoenix on 2025-07-15 was roughly 30-43 C / 86-110 F.")


# ============================================================ C. via the vendor client

print()
print("=" * 78)
print("C. Same call through the vendored client, timed")
print("=" * 78)

from fortyguard import FortyGuardClient  # noqa: E402

client = FortyGuardClient(api_key=API_KEY)
t0 = time.monotonic()
via_client = client.create_heatmap(
    polygon_aoi=aoi,
    start_date=PROBE_DATE,
    filter_type=PROBE_FILTER_TYPE,
    granularity=PROBE_GRANULARITY,
    analytic_type="tcm",
    wait=True,
    verbose=True,
)
client_elapsed = time.monotonic() - t0
print(f"\nclient round trip: {client_elapsed:.1f}s")
print(f"client activity_id: {via_client.get('activity_id')}")
save("heatmap_via_client.json", via_client)

print()
print("=" * 78)
print("SUMMARY")
print("=" * 78)
print(f"manual submit->terminal : {total:.1f}s over {len(poll_log)} polls")
print(f"client submit->terminal : {client_elapsed:.1f}s")
print(f"404 window after submit : {'observed' if first_404_seen else 'NOT observed'}")
print(f"fixtures written to      : {OUT.relative_to(ROOT)}")
print(f"stamped at               : {datetime.now(timezone.utc).isoformat()}")
