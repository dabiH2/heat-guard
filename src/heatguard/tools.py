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


# ------------------------------------------------------------------------ endpoints

def heatmap(aoi_geojson: dict, date: str, filter_type: int,
            analytic_type: str = "tcm", granularity: int = DEFAULT_GRANULARITY,
            threshold_c: float | None = None, direction: str | None = None,
            **kw) -> dict:
    """POST /v1/heatmap — thermal map over a polygon AOI. All plans.

    `threshold_c` is CELSIUS and is named so. `analytic_type` in
    {tcm, time_of_measure, exceedance, persistence}; the last two require both
    `threshold_c` and `direction`.
    """
    raise NotImplementedError("T5")


def env_params(lat: float, lon: float, air_temp_c: float, date: str,
               filter_type: int, **kw) -> dict:
    """POST /v1/env_params — humidity, AQI, solar irradiance and derived heat index.

    NOTE the required `air_temp_c`: this endpoint DERIVES from a temperature you supply,
    it does not measure one. Supply the tile temperature from `heatmap`. Its returned
    `heat_index_celsius` series varies only with humidity — see `heat_index_f`.
    """
    raise NotImplementedError("T5")


def satellite(lat: float, lon: float, date: str, **kw) -> dict:
    """POST /v1/satellite — land-cover segmentation. Available on the hackathon key.

    The one addition we keep: it answers *why* a site is hot, turning an alert into
    decision + cause + remedy. Cache aggressively — land cover barely moves.
    """
    raise NotImplementedError("T5")


def key_usage() -> dict:
    """POST /v1/system/fetch-api-key-usage — plan and credit balance. Run this first."""
    raise NotImplementedError("T3")


def poll(activity_id: str, timeout_s: int = 600) -> dict:
    """GET /v1/status/{activity_id} until terminal, with 3/6/12 s backoff.

    A 404 immediately after submit is EXPECTED — eventual consistency, not failure. Treat
    it as pending and keep polling; a naive poller discards a task that was fine.
    """
    raise NotImplementedError("T5")
