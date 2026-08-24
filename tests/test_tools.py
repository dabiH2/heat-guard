"""
tools.py tests — pure logic and cache behaviour. No network, no credits, no API key.

Three jobs:

  1. THE UNIT GUARDS. `heatmap` is the only place a threshold is written to the wire, so
     it is the only place the °C/°F trap can be stopped. T4 proved the API will not stop
     it: `threshold=95` meaning °F returned 0.0 hours, status `Completed`, credit spent,
     where the truth was 17.0.

  2. THE CACHE KEY. A key that omitted `threshold_c` would have served the 17-hour answer
     to the 0-hour call. Every parameter that changes the ANSWER must change the key.

  3. OFFLINE MODE. The key expires 2026-09-21 and the live demo must outlive it. Offline
     must serve from cache and RAISE on a miss, never invent.
"""

import json

import pytest

from heatguard.tools import (
    ANALYTIC_TYPES,
    CacheMiss,
    UnitError,
    _aoi_hash,
    air_temp_c_for_heat_index_f,
    c_to_f,
    cache_key,
    f_to_c,
    heat_index_f,
    heatmap,
    site_summary_f,
    tile_hours,
    tile_temperatures_c,
)

AOI = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {},
     "geometry": {"type": "Polygon", "coordinates": [[[-112.09, 33.47], [-112.08, 33.47],
                                                      [-112.08, 33.48], [-112.09, 33.47]]]}}]}


# ------------------------------------------------------------------ unit conversions

def test_round_trip_conversion():
    for f in (-40.0, 32.0, 91.0, 103.0, 115.0):
        assert c_to_f(f_to_c(f)) == pytest.approx(f)


def test_the_two_numbers_from_the_live_trap():
    assert f_to_c(95.0) == pytest.approx(35.0)
    assert c_to_f(95.0) == pytest.approx(203.0)


def test_heat_index_below_eighty_uses_the_simple_form():
    """NWS uses a linear approximation below 80 °F rather than the Rothfusz regression,
    which is only fitted above it. Assert the formula, not a remembered constant."""
    t, r = 70.0, 50.0
    simple = 0.5 * (t + 61.0 + (t - 68.0) * 1.2 + r * 0.094)
    assert heat_index_f(t, r) == pytest.approx(simple)
    assert heat_index_f(t, r) == pytest.approx(69.05, abs=0.01)


def test_heat_index_exceeds_air_temp_in_humid_air():
    assert heat_index_f(95.0, 70.0) > 95.0


def test_heat_index_falls_below_air_temp_in_dry_phoenix_air():
    """The reason an OSHA heat-index threshold cannot be handed to exceedance raw."""
    assert heat_index_f(105.0, 10.0) < 105.0


@pytest.mark.parametrize("rh", [10.0, 20.0, 35.0, 50.0, 70.0])
def test_inverting_heat_index_round_trips(rh):
    target = 91.0
    air_c = air_temp_c_for_heat_index_f(target, rh)
    assert heat_index_f(c_to_f(air_c), rh) == pytest.approx(target, abs=0.05)


def test_the_equivalent_temperature_moves_the_right_way_with_humidity():
    """Dry air needs a HIGHER temperature to reach 91 °F heat index; humid air a lower
    one. Same OSHA threshold, different air temperature, depending on the day — which is
    the monsoon hypothesis in T8, quantified."""
    dry = air_temp_c_for_heat_index_f(91.0, 15.0)
    humid = air_temp_c_for_heat_index_f(91.0, 60.0)
    assert dry > humid
    assert c_to_f(dry) > 91.0 > c_to_f(humid)


# ------------------------------------------------------------------- the unit guards

def test_a_fahrenheit_threshold_is_refused():
    """THE guard. 95 meaning °F would be read as 95 °C = 203 °F and return 0 hours."""
    with pytest.raises(UnitError, match="Fahrenheit"):
        heatmap(AOI, "2025-07-15", 3, analytic_type="exceedance",
                threshold_c=95.0, direction="above")


def test_a_correctly_converted_threshold_passes_the_guard(monkeypatch):
    """35.00 °C is accepted — the guard must not block the correct call."""
    captured = {}

    def fake(endpoint, payload, **kw):
        captured.update(payload)
        return {"map_data": {"features": []}, "stats_data": {"units": "hour"}}

    monkeypatch.setattr("heatguard.tools.submit_and_poll", fake)
    monkeypatch.setattr("heatguard.tools.cache_read", lambda k: None)
    monkeypatch.setattr("heatguard.tools.cache_write", lambda k, v: None)

    heatmap(AOI, "2025-07-15", 3, analytic_type="exceedance",
            threshold_c=f_to_c(95.0), direction="above")
    assert captured["threshold"] == pytest.approx(35.0, abs=0.01)


def test_a_missing_threshold_is_refused_because_the_api_does_not_refuse_it():
    """Measured in T4: the raw API silently defaults to 30 °C and returns 24.0 hours."""
    with pytest.raises(UnitError, match="silently defaults"):
        heatmap(AOI, "2025-07-15", 3, analytic_type="exceedance", direction="above")


def test_a_missing_direction_is_refused():
    with pytest.raises(ValueError, match="direction"):
        heatmap(AOI, "2025-07-15", 3, analytic_type="exceedance", threshold_c=35.0)


@pytest.mark.parametrize("bad", [10, 20, 45, 75, 250])
def test_granularities_the_api_rejects_are_refused_before_submitting(bad):
    with pytest.raises(ValueError, match="granularity"):
        heatmap(AOI, "2025-07-15", 3, granularity=bad)


def test_unknown_analytic_types_are_refused():
    with pytest.raises(ValueError, match="analytic_type"):
        heatmap(AOI, "2025-07-15", 3, analytic_type="snapshot")


def test_the_four_analytic_types_are_the_measured_ones():
    assert ANALYTIC_TYPES == ("tcm", "time_of_measure", "exceedance", "persistence")


# ----------------------------------------------------------------------- cache keys

def test_the_threshold_is_part_of_the_cache_key():
    """Without this, the unit-trap call and the correct call collide and the cache serves
    17 hours for the 0-hour request, or the reverse."""
    correct = cache_key("/v1/heatmap", aoi="x", date="2025-07-15", threshold_c=35.0)
    trapped = cache_key("/v1/heatmap", aoi="x", date="2025-07-15", threshold_c=95.0)
    assert correct != trapped


@pytest.mark.parametrize("changed", [
    {"analytic_type": "exceedance"}, {"filter_type": 1}, {"granularity": 60},
    {"date": "2025-07-16"}, {"direction": "below"}, {"aoi": "other"},
])
def test_every_answer_changing_parameter_changes_the_key(changed):
    base = dict(aoi="x", date="2025-07-15", filter_type=3,
                analytic_type="tcm", granularity=100, direction="above")
    assert cache_key("/v1/heatmap", **base) != cache_key("/v1/heatmap", **{**base, **changed})


def test_the_key_is_stable_across_argument_order():
    a = cache_key("/v1/heatmap", date="2025-07-15", aoi="x", filter_type=3)
    b = cache_key("/v1/heatmap", filter_type=3, aoi="x", date="2025-07-15")
    assert a == b


def test_the_aoi_hash_ignores_dict_ordering():
    reordered = {"features": AOI["features"], "type": AOI["type"]}
    assert _aoi_hash(AOI) == _aoi_hash(reordered)


def test_a_different_polygon_hashes_differently():
    moved = json.loads(json.dumps(AOI))
    moved["features"][0]["geometry"]["coordinates"][0][0][0] += 0.01
    assert _aoi_hash(AOI) != _aoi_hash(moved)


# --------------------------------------------------------------------- offline mode

def test_offline_raises_on_a_cache_miss_rather_than_calling_out(monkeypatch):
    """After 2026-09-21 the key is dead. A miss must say so, not invent or hang."""
    monkeypatch.setenv("HEATGUARD_OFFLINE", "1")
    monkeypatch.setattr("heatguard.tools.cache_read", lambda k: None)
    with pytest.raises(CacheMiss, match="expires"):
        heatmap(AOI, "2025-07-15", 3)


def test_offline_serves_a_cache_hit(monkeypatch):
    monkeypatch.setenv("HEATGUARD_OFFLINE", "1")
    canned = {"map_data": {"features": []}, "stats_data": {}}
    monkeypatch.setattr("heatguard.tools.cache_read", lambda k: canned)
    assert heatmap(AOI, "2025-07-15", 3) is canned


def test_offline_never_reaches_the_network(monkeypatch):
    monkeypatch.setenv("HEATGUARD_OFFLINE", "1")
    monkeypatch.setattr("heatguard.tools.cache_read", lambda k: None)

    def explode(*a, **k):
        raise AssertionError("offline mode attempted a network call")

    monkeypatch.setattr("heatguard.tools.submit_and_poll", explode)
    with pytest.raises(CacheMiss):
        heatmap(AOI, "2025-07-15", 3)


# ------------------------------------------------------------------ reading results

def test_tile_temperatures_are_read_as_celsius():
    result = load_live("t3/heatmap_tcm_result.json")
    tiles = tile_temperatures_c(result)
    assert tiles and all(20.0 < t["average_c"] < 50.0 for t in tiles)


def test_site_summary_converts_to_fahrenheit_at_the_boundary():
    summary = site_summary_f(load_live("t3/heatmap_tcm_result.json"))
    assert 85.0 < summary["min_f"] < 100.0
    assert 100.0 < summary["max_f"] < 115.0


def test_an_empty_result_summarises_as_none_not_as_zero():
    """A non-US AOI returns `Completed` with zero tiles. Returning 0 °F would be a
    reading; returning None is an absence, and callers must not confuse them."""
    assert site_summary_f({"map_data": {"features": []}}) is None


def test_exceedance_hours_are_read_from_the_live_capture():
    probes = load_live("t4/t4_probes.json")["results"]
    assert tile_hours(probes["exceedance_correct"]["result"]) == [17.0, 17.0, 17.0]
    assert tile_hours(probes["exceedance_unit_trap"]["result"]) == [0.0, 0.0, 0.0]


def test_wrong_units_on_an_hours_result_raise():
    with pytest.raises(UnitError, match="units"):
        tile_hours({"stats_data": {"units": "celsius"}, "map_data": {"features": []}})


def load_live(relative: str) -> dict:
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "data" / "fixtures" / relative
    if not path.exists():
        pytest.skip(f"live fixture {relative} not captured")
    return json.loads(path.read_text(encoding="utf-8"))
