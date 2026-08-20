"""
tools.py — typed wrappers over the FortyGuard endpoints.

WRAPS the vendor quickstart client; does not reimplement it. That client already
handles auth and the submit-then-poll cycle, and accepts wait=False to return an
activity_id for agent-driven polling.

Caching is not an optimisation here, it is a correctness and cost feature: results
are keyed on (endpoint, aoi_hash, date, time, filter_type, granularity) and written
to data/fixtures/ so tests run offline and no credit is ever spent twice.

Verified constraints (see CLAUDE.md): US-only; 2021-01-01 to now; heatmap forecasts
to now +12h; AOI <= ~130 km2; granularity 60/80/100 m.
Failed tasks cost nothing — credits are deducted only on success, so probe freely.
"""

from __future__ import annotations

BASE_URL = "https://api.fortyguard.com"
POLL_BACKOFF_SECONDS = (3, 6, 12)      # be polite; do not hammer /v1/status
GRANULARITIES = (60, 80, 100)
MAX_AOI_KM2 = 130
EARLIEST_DATE = "2021-01-01"
FORECAST_HORIZON_HOURS = 12


def heatmap(aoi_geojson: dict, date: str, time: str, filter_type: int,
            granularity: int = 100, **kw) -> dict:
    """POST /v1/heatmap — tile-by-tile thermal map over a polygon AOI. All plans."""
    raise NotImplementedError("T5")


def env_params(lat: float, lon: float, date: str, time: str, **kw) -> dict:
    """POST /v1/env_params — heat index, AQI, solar irradiance at a point. All plans.

    T4: confirm heat index is returned directly; thresholds.yaml depends on it.
    """
    raise NotImplementedError("T5")


def satellite(aoi_geojson: dict, date: str, **kw) -> dict:
    """POST /v1/satellite — land-cover segmentation. PREMIUM.

    The one premium addition we keep: it answers *why* a site is hot, turning an
    alert into decision + cause + remedy. Cache aggressively — land cover barely moves.
    """
    raise NotImplementedError("T5")


def key_usage() -> dict:
    """POST /v1/system/fetch-api-key-usage — plan and credit balance. Run this first."""
    raise NotImplementedError("T3")


def poll(activity_id: str, timeout_s: int = 600) -> dict:
    """GET /v1/status/{activity_id} until terminal.

    succeeded/completed -> result in data.result ; failed/error -> free, log and raise.
    Only needed if driving the raw API; the vendor client polls for you.
    """
    raise NotImplementedError("T5")
