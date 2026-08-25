"""
API contract tests — assert that what we MEASURED is what the code ASSUMES.

Every fact here was observed against the live API during T3/T4 and captured into
data/fixtures/. These tests read the fixtures, never the network: zero credits, and they
keep working after **16 September, when the hackathon key is revoked**. At that point
these files are the only evidence the project has that any of this was ever true.

If FortyGuard changes behaviour, these fail and say which assumption broke.
"""

import json
from pathlib import Path

import pytest

from heatguard.tools import (
    CREDITS_PER_HEATMAP_CALL,
    GRANULARITIES,
    MAX_FUTURE_DAYS_ACCEPTED,
    MAX_FUTURE_DAYS_USABLE,
    c_to_f,
    f_to_c,
)

FIX = Path(__file__).resolve().parents[1] / "data" / "fixtures"
T3, T4 = FIX / "t3", FIX / "t4"

pytestmark = pytest.mark.skipif(
    not (T4 / "t4_probes.json").exists(),
    reason="live fixtures not captured yet — run scripts/t3_probe.py and t4_probe.py",
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def probes() -> dict:
    return load(T4 / "t4_probes.json")


@pytest.fixture(scope="module")
def results(probes) -> dict:
    return probes["results"]


# ============================================================ units are CELSIUS

def test_tcm_tiles_are_celsius_not_fahrenheit():
    """The vendor client docstring says "tiles in °F". It is wrong.

    Encanto Park, 2025-07-15: min 32.72, avg 36.92, max 40.20. Read as Celsius that is
    91-104 °F, exactly right for a Phoenix July day. Read as Fahrenheit it is 0.4-4.6 °C,
    which would be a hard freeze in July.
    """
    res = load(T3 / "heatmap_tcm_result.json")
    tile = res["map_data"]["features"][0]["properties"]
    lo, hi = tile["min_temperature"], tile["max_temperature"]

    assert 25.0 < lo < 40.0, "daily minimum is not plausible as Celsius"
    assert 35.0 < hi < 50.0, "daily maximum is not plausible as Celsius"
    assert 85.0 < c_to_f(lo) < 100.0
    assert 100.0 < c_to_f(hi) < 115.0
    # And the Fahrenheit reading must be absurd, or the test proves nothing.
    assert f_to_c(hi) < 10.0, "if this passes as Celsius too, the test is not decisive"


def test_a_real_day_has_a_diurnal_range():
    """min != max is what separates a real day from a placeholder."""
    res = load(T3 / "heatmap_tcm_result.json")
    tile = res["map_data"]["features"][0]["properties"]
    assert tile["max_temperature"] - tile["min_temperature"] > 3.0


# ================================================== THE UNIT TRAP, measured live

def test_the_unit_trap_returns_zero_hours_and_reports_success(results):
    """Same endpoint, same AOI, same date, same filter_type, same analytic_type.
    The only difference is whether the threshold was converted from °F to °C.

    95 °F -> 35.00 °C  => 17.0 hours above threshold
    95 sent raw        => the API reads 95 °C = 203 °F => 0.0 hours

    Both return status `completed`. Both cost 4,220 credits. Nothing raises.
    """
    good = results["exceedance_correct"]
    trap = results["exceedance_unit_trap"]

    assert good["status"] in ("completed", "succeeded")
    assert trap["status"] in ("completed", "succeeded"), "the trap must not error"

    good_hours = good["result"]["stats_data"]["mean"]
    trap_hours = trap["result"]["stats_data"]["mean"]

    assert good_hours == pytest.approx(17.0)
    assert trap_hours == 0.0
    assert good_hours > 0 and trap_hours == 0


def test_the_conversion_that_prevents_it():
    assert f_to_c(95.0) == pytest.approx(35.0)
    assert c_to_f(95.0) == pytest.approx(203.0)


def test_exceedance_and_persistence_report_hours(results):
    for key in ("exceedance_correct", "persistence"):
        stats = results[key]["result"]["stats_data"]
        assert stats["units"] == "hour"
        assert stats["analytic_type"] == key.split("_")[0]


def test_persistence_is_never_greater_than_exceedance(results):
    """A longest continuous run cannot exceed the total hours it is drawn from."""
    total = results["exceedance_correct"]["result"]["stats_data"]["mean"]
    longest = results["persistence"]["result"]["stats_data"]["mean"]
    assert longest <= total
    assert (total, longest) == (17.0, 16.0)


# ================================================ silent failures — the dangerous ones

def test_a_non_us_aoi_completes_empty_and_still_bills(results):
    """Fawad [00:13:39]: "it's just going to spend your credit." Confirmed.

    status `completed`, zero tiles, no error flag, 4,220 credits gone. This is why
    RefusalReason.OUTSIDE_US is checked first and before any call is made.
    """
    milan = results["non_us_milan"]
    assert milan["status"] in ("completed", "succeeded")
    assert milan["result"]["map_data"]["features"] == []
    assert milan.get("submit_error_flag") is False


def test_exceedance_without_a_threshold_silently_defaults(results):
    """The raw API does NOT reject a missing threshold — it defaults (to 30 °C) and
    returns 24.0 hours, a plausible number measured against a threshold nobody chose.

    Only the vendor client raises ValueError. That guard is load-bearing, which is why
    the router's invariants also refuse to emit an exceedance plan without one.
    """
    probe = results["exceedance_missing_threshold"]
    assert probe["status"] in ("completed", "succeeded")
    assert probe["result"]["stats_data"]["mean"] == 24.0


# ================================================== loud failures — the safe ones

@pytest.mark.parametrize("probe, expected_http, needle", [
    ("far_future_2030", 400, "in the future"),
    ("filter_type_5_single_month", 422, "1, 2, 3 or 4"),
    ("granularity_10m", 422, "60, 80 or 100"),
])
def test_these_fail_loudly_at_submit_and_cost_nothing(results, probe, expected_http, needle):
    p = results[probe]
    assert p["submit_http"] == expected_http
    assert p.get("submit_error_flag") is True
    assert needle in p["submit_message"]
    assert "activity_id" not in p, "rejected at submit means no task, no credit"


def test_filter_type_5_does_not_exist(results):
    """CLAUDE.md open question #6, ANSWERED. FortyGuard engineering enumerated five
    filter types on camera; the API accepts four. The vendor client was right."""
    msg = results["filter_type_5_single_month"]["submit_message"]
    assert "Input should be 1, 2, 3 or 4" in msg


def test_the_only_granularities_are_the_ones_we_declare(results):
    msg = results["granularity_10m"]["submit_message"]
    for g in GRANULARITIES:
        assert str(g) in msg


def test_a_range_over_thirty_days_is_a_server_error(results):
    """HTTP 500 with a non-JSON body — a server fault, not a clean rejection. The router
    refuses before submitting rather than relying on this."""
    assert results["range_over_30_days"]["submit_http"] == 500


def test_coverage_starts_a_year_later_than_documented():
    """CLAUDE.md said 2021-01-01. Measured on PHX-CHASE, one date per quarter: both 2021
    probes returned Completed with zero cells and were billed; 2022-01-15 onward returned
    10 tiles. A date inside that gap is a silent, billed empty — the same shape as a
    non-US AOI, and the reason the router refuses before sending."""
    coverage = load(T4.parent / "t8" / "coverage.json")
    empty = {f["date"] for f in coverage["findings"] if f["has_data"] is False}
    ok = {f["date"] for f in coverage["findings"] if f["has_data"]}

    assert {"2021-07-15", "2021-10-15"} <= empty
    assert {"2022-01-15", "2022-07-15", "2025-07-15"} <= ok
    assert max(empty) < min(ok), "the boundary must be a clean split, not interleaved"

    from heatguard.tools import EARLIEST_DATE
    assert max(empty) < EARLIEST_DATE <= min(ok), (
        "the refusal boundary must sit inside the measured bracket"
    )


def test_a_pre_2021_date_fails_slowly_rather_than_at_submit():
    """A third failure mode: accepted at submit, then `Processing` for over three minutes
    before turning `Failed`. Not loud, not silently wrong — just slow. Poll budgets have
    to survive it, and the router refuses the date up front so they never need to."""
    recheck = load(T4 / "t4b_forecast_and_costs.json")["pre_2021_recheck"]
    assert str(recheck["status"]).lower() == "failed"


# ================================================== forecast horizon, measured

def test_the_acceptance_boundary_is_today_plus_one():
    horizon = load(T4 / "t4c_forecast_horizon.json")["acceptance"]
    assert horizon["+0d"]["accepted"] is True
    assert horizon["+1d"]["accepted"] is True
    assert horizon["+2d"]["accepted"] is False
    assert horizon["+2d"]["http"] == 400
    assert MAX_FUTURE_DAYS_ACCEPTED == 1


def test_tomorrow_is_accepted_but_returns_a_flat_day():
    """The reason MAX_FUTURE_DAYS_USABLE is 0 and not 1."""
    quality = load(T4 / "t4c_forecast_horizon.json")["data_quality"]
    today, tomorrow = quality["+0d"], quality["+1d"]

    today_tile = today["tile0"]
    today_spread = today_tile["max_temperature"] - today_tile["min_temperature"]
    assert today_spread > 3.0, "today must have a real diurnal range"

    tomorrow_tile = tomorrow["tile0"]
    tomorrow_spread = tomorrow_tile["max_temperature"] - tomorrow_tile["min_temperature"]
    assert tomorrow_spread == 0.0, "tomorrow is a flat placeholder"

    assert MAX_FUTURE_DAYS_USABLE == 0


# ============================================================== cost model

def _failed_activity_ids() -> set[str]:
    """Activity ids known to have ended `Failed`.

    The pre-2021 probe outlived its own poll budget — it sat in `Processing` past 188 s
    and only turned `Failed` on a later re-poll, recorded in t4b. So "did it fail" cannot
    be read from t4_probes.json alone, which is itself the point of the slow-fail mode.
    """
    recheck = load(T4 / "t4b_forecast_and_costs.json").get("pre_2021_recheck", {})
    if str(recheck.get("status", "")).lower() == "failed":
        return {recheck["activity_id"]}
    return set()


def test_credits_are_flat_per_call_not_per_tile(results, probes):
    """A 3-tile AOI and a 44,690-tile AOI cost exactly the same."""
    small = len(results["exceedance_correct"]["result"]["map_data"]["features"])
    large = len(results["aoi_oversized"]["result"]["map_data"]["features"])
    assert small == 3 and large > 40_000

    failed = _failed_activity_ids()
    billed = [r for r in results.values()
              if r.get("activity_id") and r["activity_id"] not in failed]
    spent = probes["credits_after"]["used"] - probes["credits_before"]["used"]

    assert spent == len(billed) * CREDITS_PER_HEATMAP_CALL, (
        f"{spent} credits over {len(billed)} billed calls is "
        f"{spent / max(len(billed), 1):.0f} each, not {CREDITS_PER_HEATMAP_CALL}"
    )
    assert spent == 25_320 and len(billed) == 6


def test_failed_tasks_cost_nothing(results, probes):
    """CLAUDE.md's claim, now measured. Seven tasks were accepted and given activity ids;
    one of them failed; exactly six were billed."""
    got_ids = {r["activity_id"] for r in results.values() if r.get("activity_id")}
    failed = _failed_activity_ids()
    assert failed, "expected at least one failed task in the probe set"
    assert failed <= got_ids

    spent = probes["credits_after"]["used"] - probes["credits_before"]["used"]
    assert spent == (len(got_ids) - len(failed)) * CREDITS_PER_HEATMAP_CALL


def test_a_silently_empty_result_is_billed_just_like_a_good_one(results):
    """The non-US call returned zero tiles and was billed the full flat rate. There is no
    refund for asking a question the API cannot answer — which is the entire economic
    argument for refusing in the router instead of at the API."""
    failed = _failed_activity_ids()
    assert results["non_us_milan"]["activity_id"] not in failed


def test_the_oversized_aoi_was_not_rejected(results):
    """CLAUDE.md open question #5. A ~447 km² AOI — 11.5x the stated 15 mi² cap — was
    accepted and returned 44,690 tiles. The cap is not enforced server-side at that size,
    so ours stays a self-imposed limit."""
    big = results["aoi_oversized"]
    assert big["status"] in ("completed", "succeeded")
    assert len(big["result"]["map_data"]["features"]) > 40_000
