"""
tools.py — typed wrappers over the FortyGuard endpoints, and the single source of truth
for verified API constants.

WRAPS the vendor quickstart client (`vendor/fortyguard/`, pinned at f6de12d); does not
reimplement it. That client already handles auth and the submit-then-poll cycle, and
accepts wait=False to return an activity_id for agent-driven polling.

Caching is not an optimisation here, it is a correctness and cost feature: results are
keyed on (endpoint, aoi_hash, date, time, filter_type, analytic_type, granularity) and
written to data/fixtures/ so tests run offline and no credit is ever spent twice.

It is also a SURVIVAL feature. API access is revoked when judging ends on 16 September,
but the live demo link must stay up through judging. Anything not in data/fixtures/ by
then is gone.

-------------------------------------------------------------------------------
THIS MODULE OWNS EVERY UNIT CONVERSION. NOTHING ELSE MAY DO ONE.
-------------------------------------------------------------------------------
Three conversions, each of which fails silently if skipped:

  1. °F -> °C. The router emits Fahrenheit because OSHA and NWS are Fahrenheit. The API
     takes Celsius. Pass 91 meaning °F and the API reads 91 °C = 195.8 °F: exceedance
     returns 0 hours at every cell, status `succeeded`, credit spent, and the tool
     reports a confident all-clear across all twelve sites.

  2. heat index -> air temperature. `analytic_type=exceedance` thresholds the TEMPERATURE
     field; OSHA bands are HEAT INDEX. In dry Phoenix air, heat index runs BELOW air
     temperature, so the air temperature equivalent to an OSHA threshold is HIGHER than
     the OSHA number. Under monsoon humidity it runs above, so the equivalent is LOWER.
     Same OSHA threshold, different air temperature, depending on the day.

  3. Reading the response. Verified from the vendor's own sample data: tcm tiles are
     CELSIUS (San José, 15 Jul: min 16.35, avg 20.86, max 27.60 — coherent as °C,
     impossible as °F). The vendor client docstring claims °F. It is wrong. Confirm
     against a live Phoenix call in T4 before trusting either.

Every public signature here is unit-suffixed. A bare `threshold` or `temperature`
argument must not exist in this codebase.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import requests

# ------------------------------------------------------------------ verified constants
# Single source of truth. router.py and scripts/build_sites.py import from here rather
# than redeclaring, because a safety limit that exists in three files is a limit that
# will disagree with itself.

BASE_URL = "https://api.fortyguard.com"

#: CLAUDE.md convention. The vendor client polls at a constant 3.0 s, so tools.py drives
#: its own loop via wait=False rather than calling client.wait_for.
POLL_BACKOFF_SECONDS = (3, 6, 12)

GRANULARITIES = (60, 80, 100)
DEFAULT_GRANULARITY = 100          # cheapest; finer costs more credits

EARLIEST_DATE = "2021-01-01"

# ---------------------------------------------------------------------------
# FORECAST HORIZON — measured in T4, and it is NOT "now + 12 h".
# ---------------------------------------------------------------------------
# Submit-level rule, measured by bisection on 2026-08-21:
#   start_date <= today + 1 day   -> HTTP 200, accepted
#   start_date >= today + 2 days  -> HTTP 400, "Field 'date_time.start_date' (...) is in
#                                    the future. Requests must be for a past or present
#                                    date."  (loud, free)
#
# But ACCEPTED IS NOT ANSWERED. Tomorrow is accepted, billed, and returns a DEGENERATE
# result — one flat value for the entire day:
#
#   2025-07-15 (history)  min 32.72  avg 36.92  max 40.20   spread 7.48 C
#   2026-08-21 (today)    min 33.72  avg 37.86  max 41.94   spread 8.22 C
#   2026-08-22 (tomorrow) min 34.34  avg 34.34  max 34.34   spread 0.00 C  <-- flat
#
# A flat 34.34 C across a Phoenix August day is physically impossible (overnight lows are
# near 30, afternoon highs near 42). There is no diurnal structure in it. Running
# exceedance against a constant returns exactly 0 hours or exactly 24 hours with nothing
# in between — a confidently formatted answer with no information in it.
#
# So the router refuses anything past TODAY, not past the submit boundary.
MAX_FUTURE_DAYS_ACCEPTED = 1     # what the API will take
MAX_FUTURE_DAYS_USABLE = 0       # what actually carries a diurnal profile

#: Max days per call. Fawad Shah [00:19:49]: "as much as 30 days worth of data." Measured:
#: a 61-day range returns HTTP 500 with a non-JSON body — a server fault, not a clean
#: rejection, so the router refuses before submitting.
MAX_DAYS_PER_CALL = 30

#: 15 mi² on the hackathon plan, per FortyGuard engineering [00:23:53].
#: ⚠ MEASURED IN T4: a ~447 km² AOI (11.5x the stated cap) was ACCEPTED and returned
#: 44,690 tiles for the same flat credit cost. The cap is not enforced server-side at
#: that size. Kept as a self-imposed limit because an unenforced limit is still a
#: documented one, and because tile count drives response size, not price.
MAX_AOI_MI2 = 15.0
MAX_AOI_KM2 = 38.85

#: MEASURED: 4,220 credits per heatmap call, FLAT — a 3-tile AOI and a 44,690-tile AOI
#: cost exactly the same. Billing is per call, not per tile.
#: 2,000,000 / 4,220 = ~474 heatmap calls for the whole hackathon. Not unlimited: one
#: demo day across 12 sites at two analytic types is 24 calls, ~5% of the budget.
CREDITS_PER_HEATMAP_CALL = 4_220
MAX_HEATMAP_CALLS = 474

#: Approximate; hedged by the speaker ("I think 100 requests per minute or something",
#: [00:56:17]) and the host asked people not to probe it. Treat as a ceiling to stay well
#: under, not a target.
RATE_LIMIT_PER_MINUTE = 100

#: Per API key, confirmed in two sessions. Fawad's entire demo build cost 187,420 —
#: under 10% of one key. Budget anxiety is unwarranted; probing failures is free.
CREDITS_PER_KEY = 2_000_000

#: Terminal statuses. MEASURED: the API sends title case — "Processing", "Completed",
#: "Failed" — so compare lowercased, as the vendor client does.
TERMINAL_SUCCESS = ("succeeded", "completed")
TERMINAL_FAILURE = ("failed", "error")

#: MEASURED over ~15 submissions: a 3-tile call reaches `Completed` in ~24 s; a
#: 44,690-tile call took ~42 s. A pre-2021 date sat in `Processing` for over three
#: minutes before turning `Failed` — a third failure mode that is neither loud at submit
#: nor silently wrong, just slow. Poll budgets must survive it.
TYPICAL_LATENCY_S = 24
OBSERVED_MAX_LATENCY_S = 300

#: The vendor client guards against a 404 window right after submit. NOT observed in any
#: of ~15 submissions during T4 — the first poll at t+3.7 s already returned 200. The
#: guard is kept because absence of evidence over 15 calls is not evidence of absence.
POST_SUBMIT_404_OBSERVED = False


# ------------------------------------------------------------------- unit conversions

def f_to_c(fahrenheit: float) -> float:
    """Fahrenheit to Celsius. The API speaks Celsius; our config speaks Fahrenheit."""
    return (fahrenheit - 32.0) * 5.0 / 9.0


def c_to_f(celsius: float) -> float:
    """Celsius to Fahrenheit. Every value read back from the API goes through here."""
    return celsius * 9.0 / 5.0 + 32.0


def heat_index_f(air_temp_f: float, relative_humidity_pct: float) -> float:
    """NWS heat index (Rothfusz regression) with both standard adjustments.

    Reproduced here rather than taken from the API because `env_params` computes heat
    index from ONE supplied temperature against hourly humidity — its 24 'hourly' values
    are a humidity curve at fixed temperature, not a temperature curve. Verified against
    the vendor's own sample response: recomputing from the single input temperature plus
    each hour's humidity matches their series to within 0.09 °C for 15 of 24 hours and
    0.87 °C at the >85% RH adjustment boundary.

    That matters because it means the API's heat-index series CANNOT be used as a site's
    hourly profile. Using it as one would invert the shape of the day — the sample peaks
    at 02:00 and troughs at 14:00.
    """
    t, r = air_temp_f, relative_humidity_pct
    simple = 0.5 * (t + 61.0 + (t - 68.0) * 1.2 + r * 0.094)
    if (simple + t) / 2.0 < 80.0:
        return simple

    hi = (-42.379 + 2.04901523 * t + 10.14333127 * r
          - 0.22475541 * t * r - 0.00683783 * t * t
          - 0.05481717 * r * r + 0.00122874 * t * t * r
          + 0.00085282 * t * r * r - 0.00000199 * t * t * r * r)

    if r < 13.0 and 80.0 <= t <= 112.0:
        hi -= ((13.0 - r) / 4.0) * ((17.0 - abs(t - 95.0)) / 17.0) ** 0.5
    elif r > 85.0 and 80.0 <= t <= 87.0:
        hi += ((r - 85.0) / 10.0) * ((87.0 - t) / 5.0)
    return hi


def air_temp_c_for_heat_index_f(
    target_heat_index_f: float,
    relative_humidity_pct: float,
    *,
    tolerance_f: float = 0.01,
) -> float:
    """The air temperature (°C) whose heat index equals `target_heat_index_f` at a given
    humidity — the conversion that lets an OSHA heat-index threshold be handed to
    `analytic_type=exceedance`, which thresholds AIR TEMPERATURE.

    Solved by bisection because the Rothfusz regression does not invert in closed form.
    Monotonic in temperature over any range that matters here, so bisection is safe.

    In dry Phoenix air (RH ~20%) this returns a HIGHER number than the target; under
    monsoon humidity (RH ~50%) a LOWER one. Handing the raw OSHA °F number straight to
    the API would be wrong in both directions and wrong by different amounts on different
    days — which is precisely the kind of plausible, unflagged error this project is about.
    """
    lo_f, hi_f = -40.0, 200.0
    for _ in range(200):
        mid_f = (lo_f + hi_f) / 2.0
        produced = heat_index_f(mid_f, relative_humidity_pct)
        if abs(produced - target_heat_index_f) < tolerance_f:
            return f_to_c(mid_f)
        if produced < target_heat_index_f:
            lo_f = mid_f
        else:
            hi_f = mid_f
    return f_to_c((lo_f + hi_f) / 2.0)


# ============================================================================ cache
# Not an optimisation. The key expires 2026-09-21 and the live demo must survive
# judging, so data/fixtures/ is the PRODUCTION data store and the network is the
# fallback. HEATGUARD_OFFLINE=1 makes that explicit: cache only, and a miss raises
# rather than inventing anything.

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "api"
ACTIVITY_LOG = Path(__file__).resolve().parents[2] / "data" / "activity_log.jsonl"


class ToolsError(RuntimeError):
    """Anything the API layer refuses to do."""


class CacheMiss(ToolsError):
    """Offline, and this call is not in the cache."""


class UnitError(ToolsError):
    """A value crossed the API boundary without a declared unit."""


def offline() -> bool:
    return os.environ.get("HEATGUARD_OFFLINE", "").strip().lower() in ("1", "true", "yes")


def _aoi_hash(aoi_geojson: dict) -> str:
    """Stable 12-char digest of an AOI, so the cache key survives dict reordering."""
    canonical = json.dumps(aoi_geojson, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def cache_key(endpoint: str, **parts) -> str:
    """(endpoint, aoi_hash, date, time, filter_type, analytic_type, granularity, …).

    Every parameter that changes the ANSWER belongs in the key. `threshold_c` is in it
    for a specific reason: the unit trap produced two different results from calls that
    were otherwise identical, and a key that omitted the threshold would have served the
    17-hour answer for the 0-hour call, or worse, the reverse.
    """
    slug = "_".join(
        f"{k}={parts[k]}" for k in sorted(parts) if parts[k] is not None
    )
    digest = hashlib.sha256(f"{endpoint}|{slug}".encode()).hexdigest()[:10]
    safe = endpoint.strip("/").replace("/", "-")
    return f"{safe}__{digest}"


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def cache_read(key: str) -> dict | None:
    path = _cache_path(key)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def cache_write(key: str, payload: dict) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(key)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _log_activity(record: dict) -> None:
    """Append every activity_id. CLAUDE.md requires it; it is also the only way to
    reconcile a credit balance against what was actually asked for."""
    ACTIVITY_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ACTIVITY_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


# ========================================================================= transport

def _session() -> requests.Session:
    key = os.environ.get("FORTYGUARD_API_KEY", "").strip()
    if not key or key == "paste_key_here":
        raise ToolsError(
            "FORTYGUARD_API_KEY is not set. Copy .env.example to .env and paste the key, "
            "or set HEATGUARD_OFFLINE=1 to serve from data/fixtures/ only."
        )
    s = requests.Session()
    s.headers.update({"api-key": key, "Content-Type": "application/json"})
    return s


def submit_and_poll(endpoint: str, payload: dict, *, timeout_s: int = 600,
                    label: str = "") -> dict:
    """POST, then poll GET /v1/status/{id} to terminal with 3 → 6 → 12 s backoff.

    A 404 right after submit is treated as pending, not failure. It was never observed in
    ~15 T4 calls, but the vendor client guards against it and 15 calls is not proof.
    """
    session = _session()
    started = time.monotonic()

    response = session.post(f"{BASE_URL}{endpoint}", json=payload, timeout=60)
    try:
        body = response.json()
    except ValueError:
        raise ToolsError(
            f"POST {endpoint} -> HTTP {response.status_code} with a non-JSON body: "
            f"{response.text[:200]}"
        ) from None

    if body.get("error") or not (body.get("data") or {}).get("activity_id"):
        raise ToolsError(
            f"POST {endpoint} rejected at submit (HTTP {response.status_code}), no credit "
            f"spent: {body.get('message')}"
        )

    activity_id = body["data"]["activity_id"]
    delays = list(POLL_BACKOFF_SECONDS)
    attempt = 0

    while time.monotonic() - started < timeout_s:
        time.sleep(delays[min(attempt, len(delays) - 1)])
        attempt += 1
        status_response = session.get(
            f"{BASE_URL}/v1/status/{activity_id}", timeout=60)

        if status_response.status_code == 404:
            continue                       # eventual consistency, not failure

        data = (status_response.json().get("data") or {})
        status = str(data.get("status", "")).lower()

        if status in TERMINAL_SUCCESS:
            elapsed = round(time.monotonic() - started, 1)
            _log_activity({"activity_id": activity_id, "endpoint": endpoint,
                           "label": label, "status": status, "elapsed_s": elapsed,
                           "credits": CREDITS_PER_HEATMAP_CALL})
            return data.get("result", data)

        if status in TERMINAL_FAILURE:
            _log_activity({"activity_id": activity_id, "endpoint": endpoint,
                           "label": label, "status": status, "credits": 0})
            raise ToolsError(f"{endpoint} task {activity_id} failed (no credit spent)")

    raise ToolsError(
        f"{endpoint} task {activity_id} still running after {timeout_s}s. A pre-2021 date "
        f"behaves like this — accepted, then Processing for minutes, then Failed."
    )


# ======================================================================== endpoints

ANALYTIC_TYPES = ("tcm", "time_of_measure", "exceedance", "persistence")
NEEDS_THRESHOLD = ("exceedance", "persistence")


def heatmap(aoi_geojson: dict, date: str, filter_type: int,
            analytic_type: str = "tcm", granularity: int = DEFAULT_GRANULARITY,
            threshold_c: float | None = None, direction: str | None = None,
            end_date: str | None = None, start_time: str | None = None,
            end_time: str | None = None, *, label: str = "",
            refresh: bool = False) -> dict:
    """POST /v1/heatmap — thermal map over a polygon AOI.

    `threshold_c` is CELSIUS and is named so. Passing a Fahrenheit number here is the
    trap that returned 0 hours where the truth was 17: measured live in T4, status
    `Completed`, credit spent, nothing raised. The guard below is the last line of
    defence, and it is a heuristic — it cannot catch 40 °F passed as 40 °C.
    """
    if analytic_type not in ANALYTIC_TYPES:
        raise ValueError(f"unknown analytic_type {analytic_type!r}; use {ANALYTIC_TYPES}")

    if analytic_type in NEEDS_THRESHOLD:
        if threshold_c is None:
            raise UnitError(
                f"analytic_type={analytic_type!r} needs threshold_c. The raw API does NOT "
                f"reject a missing threshold — measured in T4 it silently defaults to "
                f"30 °C and returns 24.0 hours, a plausible number measured against a "
                f"threshold nobody chose."
            )
        if direction not in ("above", "below"):
            raise ValueError(f"analytic_type={analytic_type!r} needs direction above/below")
        if threshold_c > 60.0:
            raise UnitError(
                f"threshold_c={threshold_c} is above 60 °C ({c_to_f(threshold_c):.0f} °F). "
                f"Nowhere on Earth reaches that, so this is almost certainly a Fahrenheit "
                f"value that skipped f_to_c(). Sent as-is it returns 0 hours everywhere, "
                f"status Completed, and reads as an all-clear."
            )

    if granularity not in GRANULARITIES:
        raise ValueError(f"granularity must be one of {GRANULARITIES}, got {granularity}")

    key = cache_key("/v1/heatmap", aoi=_aoi_hash(aoi_geojson), date=date,
                    end_date=end_date, start_time=start_time, end_time=end_time,
                    filter_type=filter_type, analytic_type=analytic_type,
                    granularity=granularity, threshold_c=threshold_c,
                    direction=direction)

    if not refresh:
        if (hit := cache_read(key)) is not None:
            return hit
    if offline():
        raise CacheMiss(
            f"HEATGUARD_OFFLINE is set and {key} is not cached. The live demo serves from "
            f"data/fixtures/api/ because the key expires 2026-09-21; anything not cached "
            f"before then cannot be answered."
        )

    date_time: dict[str, Any] = {"start_date": date, "filter_type": filter_type}
    for name, value in (("end_date", end_date), ("start_time", start_time),
                        ("end_time", end_time)):
        if value is not None:
            date_time[name] = value

    payload: dict[str, Any] = {
        "polygon_aoi": aoi_geojson,
        "date_time": date_time,
        "granularity": granularity,
        "analytic_type": analytic_type,
    }
    if threshold_c is not None:
        payload["threshold"] = round(threshold_c, 2)   # the ONLY place this is written
    if direction is not None:
        payload["direction"] = direction

    result = submit_and_poll("/v1/heatmap", payload,
                             label=label or f"{analytic_type}:{date}")
    cache_write(key, result)
    return result


def env_params(lat: float, lon: float, air_temp_c: float, date: str,
               filter_type: int = 3, end_date: str | None = None,
               *, label: str = "", refresh: bool = False) -> dict:
    """POST /v1/env_params — humidity, AQI, solar irradiance and a derived heat index.

    NOTE the required `air_temp_c`: this endpoint DERIVES from a temperature you supply,
    it does not measure one. Supply a tile temperature from `heatmap`.

    Its `heat_index_celsius` series varies ONLY with humidity — the temperature is held
    at whatever you passed. Do not use it as a site's hourly profile; it peaks at 02:00
    and troughs at 14:00. See `heat_index_f`.
    """
    if air_temp_c > 60.0:
        raise UnitError(
            f"air_temp_c={air_temp_c} is above 60 °C ({c_to_f(air_temp_c):.0f} °F) — "
            f"almost certainly Fahrenheit that skipped f_to_c()."
        )

    key = cache_key("/v1/env_params", lat=round(lat, 6), lon=round(lon, 6),
                    air_temp_c=round(air_temp_c, 3), date=date, end_date=end_date,
                    filter_type=filter_type)

    if not refresh:
        if (hit := cache_read(key)) is not None:
            return hit
    if offline():
        raise CacheMiss(f"HEATGUARD_OFFLINE is set and {key} is not cached.")

    date_time: dict[str, Any] = {"start_date": date, "filter_type": filter_type}
    if end_date is not None:
        date_time["end_date"] = end_date

    result = submit_and_poll("/v1/env_params", {
        "latitude": lat, "longitude": lon,
        "temperature": air_temp_c, "date_time": date_time,
    }, label=label or f"env_params:{date}")
    cache_write(key, result)
    return result


def satellite(lat: float, lon: float, date: str, filter_type: int = 3,
              granularity: int = DEFAULT_GRANULARITY, *, label: str = "",
              refresh: bool = False) -> dict:
    """POST /v1/satellite — land-cover segmentation.

    The one addition we keep: it answers *why* a site is hot, turning an alert into
    decision + cause + remedy. Cache hard — land cover barely moves.
    """
    key = cache_key("/v1/satellite", lat=round(lat, 6), lon=round(lon, 6),
                    date=date, filter_type=filter_type, granularity=granularity)
    if not refresh:
        if (hit := cache_read(key)) is not None:
            return hit
    if offline():
        raise CacheMiss(f"HEATGUARD_OFFLINE is set and {key} is not cached.")

    result = submit_and_poll("/v1/satellite", {
        "sat": {"latitude": lat, "longitude": lon},
        "date_time": {"start_date": date, "filter_type": filter_type},
        "granularity": granularity,
    }, label=label or f"satellite:{date}")
    cache_write(key, result)
    return result


def key_usage() -> dict:
    """POST /v1/system/fetch-api-key-usage — plan and credit balance. Never cached."""
    session = _session()
    body = session.post(f"{BASE_URL}/v1/system/fetch-api-key-usage",
                        json={"api_key": session.headers["api-key"]}, timeout=60).json()
    return body


def credits_remaining() -> int:
    return int(key_usage()["credit_summary"]["cycle_remaining_credits"])


# ==================================================================== reading results

def tile_temperatures_c(result: dict) -> list[dict]:
    """`tcm` tiles as {tile_id, average_c, min_c, max_c}.

    VALUES ARE CELSIUS. The vendor client docstring says °F and is wrong — measured live,
    Encanto Park 2025-07-15 returned 32.72-40.20, which is 91-104 °F as Celsius and an
    impossible hard freeze as Fahrenheit.
    """
    return [
        {"tile_id": f["properties"]["tile_id"],
         "average_c": f["properties"]["average_temperature"],
         "min_c": f["properties"]["min_temperature"],
         "max_c": f["properties"]["max_temperature"]}
        for f in (result.get("map_data") or {}).get("features", [])
    ]


def tile_hours(result: dict) -> list[float]:
    """`exceedance` / `persistence` tile values, in hours."""
    stats = result.get("stats_data") or {}
    if stats.get("units") not in (None, "hour"):
        raise UnitError(f"expected units 'hour', got {stats.get('units')!r}")
    return [f["properties"]["value"]
            for f in (result.get("map_data") or {}).get("features", [])
            if "value" in f.get("properties", {})]


def site_summary_f(result: dict) -> dict | None:
    """One site's day, converted to Fahrenheit at the boundary. None if empty.

    An empty result is what a non-US AOI returns — `Completed`, zero tiles, billed. It is
    surfaced as None rather than as a zero so callers cannot mistake it for a reading.
    """
    tiles = tile_temperatures_c(result)
    if not tiles:
        return None
    return {
        "n_tiles": len(tiles),
        "mean_f": c_to_f(sum(t["average_c"] for t in tiles) / len(tiles)),
        "min_f": c_to_f(min(t["min_c"] for t in tiles)),
        "max_f": c_to_f(max(t["max_c"] for t in tiles)),
    }
