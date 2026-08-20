"""
Acceptance tests for T1 — does the SHIPPED roster satisfy the selection criterion?

TASKS.md T1: "Selection criterion that matters most: thermal diversity. The demo depends
on two sites inverting their ranking between peak temperature and hours-above-threshold.
If all twelve are similar, no inversion exists on any date and the demo dies."

These tests cannot prove an inversion exists — only real data can, and that is T8. What
they CAN do is fail fast if the roster loses the structural preconditions for one: both
halves of the inversion pair present, a daytime lever present, and night crews present so
the nocturnal mechanism is attached to someone who is actually standing outside.

They also enforce the two artifacts staying in step with each other. sites.csv and
sites.geojson are generated from the same source in the same pass, so a disagreement
between them means somebody hand-edited a build artifact.
"""

import pytest

from build_sites import separation_m
from heatguard.tools import MAX_AOI_KM2

EXPECTED_SITE_COUNT = 12
REQUIRED_PROFILES = {
    "high_peak_fast_cool",
    "clipped_peak_long_tail",
    "high_peak_long_tail",
    "depressed_peak",
}


# ------------------------------------------------------------------ basic integrity

def test_roster_has_twelve_sites(site_rows):
    assert len(site_rows) == EXPECTED_SITE_COUNT


def test_site_ids_are_unique(site_rows):
    ids = [r["site_id"] for r in site_rows]
    assert len(set(ids)) == len(ids)


def test_every_site_explains_why_it_is_here(site_rows):
    for row in site_rows:
        assert len(row["why_chosen"]) > 80, f"{row['site_id']} has no real rationale"


def test_every_site_carries_geocode_provenance(site_rows):
    """osm_id + the geocoder's own name are what make a coordinate re-checkable."""
    for row in site_rows:
        assert row["osm_id"], f"{row['site_id']} has no OSM id"
        assert row["geocoded_name"], f"{row['site_id']} has no resolved name"


# ------------------------------------------------------------- the T1 criterion

def test_all_four_thermal_profiles_are_represented(site_rows):
    present = {r["expected_profile"] for r in site_rows}
    assert present == REQUIRED_PROFILES, f"missing: {REQUIRED_PROFILES - present}"


def test_both_halves_of_the_inversion_pair_exist(site_rows):
    """Without both, there is nothing to invert and the demo has no money shot."""
    profiles = [r["expected_profile"] for r in site_rows]
    assert profiles.count("high_peak_fast_cool") >= 2, "need a replicate for the peak half"
    assert profiles.count("clipped_peak_long_tail") >= 2, "need a replicate for the tail half"


def test_a_daytime_lever_exists(site_rows):
    """The nocturnal mechanism must not be the demo's only contrast — see sites_source.yaml."""
    daytime_oasis = [
        r for r in site_rows
        if r["expected_profile"] == "depressed_peak" and r["night_shift"] == "False"
    ]
    assert daytime_oasis, "no evaporative site on a day shift; the daytime lever is gone"


def test_night_crews_exist_so_the_nocturnal_heat_island_is_decision_relevant(site_rows):
    """Extra evening hours only avoid exposure if somebody was scheduled into them."""
    night = [r for r in site_rows if r["night_shift"] == "True"]
    assert night, "no night shifts — the nocturnal heat island changes nobody's decision"


def test_the_lead_site_is_a_downtown_canyon_on_a_night_shift(site_rows):
    """The strongest case in the project: a crew whose whole shift a daytime high misses."""
    lead = [
        r for r in site_rows
        if r["archetype"] == "downtown_canyon" and r["night_shift"] == "True"
    ]
    assert lead, "no night crew in a street canyon"


def test_shift_lengths_are_plausible(site_rows):
    for row in site_rows:
        assert 6.0 <= float(row["shift_hours"]) <= 12.0, f"{row['site_id']} shift is odd"


# ------------------------------------------------------------- artifacts agree

def test_csv_and_geojson_describe_the_same_sites(site_rows, site_geojson):
    csv_ids = {r["site_id"] for r in site_rows}
    geo_ids = {f["properties"]["site_id"] for f in site_geojson["features"]}
    assert csv_ids == geo_ids


def test_geojson_centroids_match_the_csv(site_rows, site_geojson):
    by_id = {r["site_id"]: r for r in site_rows}
    for feature in site_geojson["features"]:
        lon, lat = feature["properties"]["centroid"]
        row = by_id[feature["properties"]["site_id"]]
        assert (lat, lon) == (float(row["lat"]), float(row["lon"]))


def test_every_polygon_is_closed_and_under_the_aoi_cap(site_geojson):
    for feature in site_geojson["features"]:
        ring = feature["geometry"]["coordinates"][0]
        assert ring[0] == ring[-1], f"{feature['properties']['site_id']}: ring not closed"
        assert feature["properties"]["area_km2"] < MAX_AOI_KM2


def test_no_two_aois_overlap(site_rows, site_source):
    """Overlapping AOIs would double-count exposure-hours in the headline metric."""
    floor = float(site_source["min_separation_m"])
    points = [(r["site_id"], float(r["lat"]), float(r["lon"])) for r in site_rows]
    for i, (id_a, lat_a, lon_a) in enumerate(points):
        for id_b, lat_b, lon_b in points[i + 1:]:
            d = separation_m((lat_a, lon_a), (lat_b, lon_b))
            assert d >= floor, f"{id_a} and {id_b} are {d:.0f} m apart (floor {floor:.0f} m)"


def test_source_and_built_roster_have_not_drifted(site_rows, site_source):
    """sites.csv is a build artifact. If it disagrees with the source, someone edited it."""
    source_ids = [s["site_id"] for s in site_source["sites"]]
    assert [r["site_id"] for r in site_rows] == source_ids, (
        "config/sites.csv is out of date — run: python scripts/build_sites.py"
    )


# -------------------------------------------------------------- geographic spread

def test_the_roster_spans_the_metro_not_one_neighbourhood(site_rows):
    """Twelve sites within a kilometre of each other would sample one air mass."""
    points = [(float(r["lat"]), float(r["lon"])) for r in site_rows]
    widest = max(
        separation_m(a, b)
        for i, a in enumerate(points) for b in points[i + 1:]
    )
    assert widest > 30_000, f"roster spans only {widest / 1000:.1f} km"


@pytest.mark.parametrize("archetype", [
    "industrial_asphalt", "downtown_canyon", "desert_edge",
    "park_adjacent", "mixed_suburban",
])
def test_every_archetype_in_the_vocabulary_is_used(site_rows, archetype):
    assert any(r["archetype"] == archetype for r in site_rows)
