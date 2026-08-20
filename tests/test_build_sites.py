"""
Tests for the site-roster build — pure logic. No network, no credits, no API key.

Two jobs. First, pin the geometry: the AOI polygons are what every FortyGuard request
is drawn against, so a ring that is unclosed, clockwise, or the wrong size would poison
every downstream number silently.

Second, and more important, pin the GUARDS. During T1 the query
"5615 South 91st Avenue, Tolleson, Arizona" resolved to the street centroid of 91st
Avenue — 4.5 km north of the wastewater plant it was meant to find, still inside
Maricopa County, still a perfectly plausible coordinate. The API would have returned a
valid thermal profile for it and raised nothing.

The real Nominatim record from that failure is fixtured below. If someone loosens the
guards, this file fails.
"""

import math

import pytest

from build_sites import (
    METRO_BBOX,
    buffer_ring,
    crosses_midnight,
    metres_per_degree,
    ring_area_km2,
    ring_is_ccw,
    separation_m,
    shift_hours,
    validate_geocode,
)

PHOENIX_LAT = 33.45
PHOENIX_LON = -112.07


# ----------------------------------------------------------------------- geodesy

def test_metres_per_degree_at_phoenix():
    m_lat, m_lon = metres_per_degree(PHOENIX_LAT)
    # A degree of latitude is ~111 km everywhere; a degree of longitude shrinks with
    # cos(lat), so at 33.45 N it must be meaningfully shorter than a degree of latitude.
    assert 110_800 < m_lat < 111_400
    assert 92_000 < m_lon < 93_500
    assert m_lon < m_lat


def test_metres_per_degree_longitude_collapses_toward_the_pole():
    assert metres_per_degree(0)[1] > metres_per_degree(45)[1] > metres_per_degree(80)[1]


# ---------------------------------------------------------------------- geometry

def test_buffer_ring_is_closed():
    ring = buffer_ring(PHOENIX_LAT, PHOENIX_LON, 200)
    assert ring[0] == ring[-1], "an unclosed ring is not a valid GeoJSON polygon"


def test_buffer_ring_is_counter_clockwise():
    """RFC 7946 asks for counter-clockwise exterior rings."""
    assert ring_is_ccw(buffer_ring(PHOENIX_LAT, PHOENIX_LON, 200))


def test_buffer_ring_vertices_sit_at_the_requested_radius():
    radius = 200.0
    ring = buffer_ring(PHOENIX_LAT, PHOENIX_LON, radius)
    for lon, lat in ring:
        d = separation_m((PHOENIX_LAT, PHOENIX_LON), (lat, lon))
        assert d == pytest.approx(radius, abs=1.0)


def test_buffer_ring_area_matches_the_inscribed_polygon_exactly():
    """An inscribed regular n-gon has area (n/2)·r²·sin(2π/n) — assert that, not a fudge.

    The ring is inscribed, so it under-covers the nominal circle by 1.14% of area at
    n=24. That is deliberate and irrelevant: the 200 m radius is itself a judgement call
    about how much ground a crew occupies, not a boundary anything depends on.
    """
    radius, n = 200.0, 24
    ring = buffer_ring(PHOENIX_LAT, PHOENIX_LON, radius, vertices=n)
    exact_km2 = (n / 2) * (radius / 1000) ** 2 * math.sin(2 * math.pi / n)
    assert ring_area_km2(ring, PHOENIX_LAT) == pytest.approx(exact_km2, rel=1e-4)


def test_buffer_ring_stays_within_one_and_a_half_percent_of_a_circle():
    radius = 200.0
    ring = buffer_ring(PHOENIX_LAT, PHOENIX_LON, radius)
    circle_km2 = math.pi * (radius / 1000) ** 2
    assert ring_area_km2(ring, PHOENIX_LAT) == pytest.approx(circle_km2, rel=0.015)


def test_site_aoi_is_far_under_the_api_cap():
    """CLAUDE.md, verified: AOI <= ~130 km2. A 200 m buffer is ~0.126 km2."""
    ring = buffer_ring(PHOENIX_LAT, PHOENIX_LON, 200)
    assert ring_area_km2(ring, PHOENIX_LAT) < 1.0


def test_separation_is_symmetric_and_zero_on_itself():
    a, b = (PHOENIX_LAT, PHOENIX_LON), (33.39, -112.26)
    assert separation_m(a, b) == pytest.approx(separation_m(b, a))
    assert separation_m(a, a) == pytest.approx(0.0)


# ------------------------------------------------------------------------ shifts

@pytest.mark.parametrize("start, end, expected", [
    ("05:00", "13:30", 8.5),
    ("06:00", "14:30", 8.5),
    ("21:00", "05:30", 8.5),    # night crew, wraps past midnight
    ("19:00", "05:00", 10.0),   # the Loop 202 paving shift
    ("20:00", "04:30", 8.5),
])
def test_shift_hours(start, end, expected):
    assert shift_hours(start, end) == expected


@pytest.mark.parametrize("start, end, expected", [
    ("05:00", "13:30", False),
    ("21:00", "05:30", True),
    ("19:00", "05:00", True),
])
def test_crosses_midnight(start, end, expected):
    assert crosses_midnight(start, end) is expected


def test_night_shift_is_not_silently_negative():
    """A naive end-minus-start would give -15.5 h here and quietly break the metric."""
    assert shift_hours("21:00", "05:30") > 0


# ------------------------------------------------------- geocode guards (regression)

# The real Nominatim response for "5615 South 91st Avenue, Tolleson, Arizona, USA".
# 4.5 km off target, inside the metro, class `highway` — a street centroid.
BAD_91ST_AVE = {
    "lat": 33.445234,
    "lon": -112.255154,
    "osm_type": "way",
    "osm_id": 0,
    "display_name": "South 91st Avenue, Tolleson, Maricopa County, Arizona, 85353, "
                    "United States",
    "class": "highway",
    "type": "secondary",
}

GOOD_SKY_HARBOR = {
    "lat": 33.432849,
    "lon": -112.006792,
    "osm_type": "relation",
    "osm_id": 8367318,
    "display_name": "Phoenix Sky Harbor International Airport, East University Drive, "
                    "Central City, Phoenix, Maricopa County, Arizona, 85034, "
                    "United States",
    "class": "aeroway",
    "type": "aerodrome",
}


def test_street_centroid_fallback_is_rejected():
    """THE regression. This exact record nearly shipped as a site coordinate."""
    site = {"site_id": "PHX-91ST", "expect_in_name": "91st Avenue"}
    problem = validate_geocode(site, BAD_91ST_AVE)
    assert problem is not None
    assert "street centroid" in problem


def test_street_centroid_is_allowed_when_the_site_really_is_a_road():
    """PHX-L202 is a freeway paving corridor — a highway result is correct there."""
    site = {"site_id": "PHX-L202", "expect_in_name": "91st Avenue",
            "allow_street_geocode": True}
    assert validate_geocode(site, BAD_91ST_AVE) is None


def test_a_good_record_passes():
    site = {"site_id": "PHX-SKY", "expect_in_name": "Sky Harbor"}
    assert validate_geocode(site, GOOD_SKY_HARBOR) is None


def test_wrong_place_is_rejected_by_name():
    """Right city, right class, wrong object."""
    site = {"site_id": "PHX-SKY", "expect_in_name": "Deer Valley Airport"}
    problem = validate_geocode(site, GOOD_SKY_HARBOR)
    assert problem is not None and "expected" in problem


def test_outside_the_metro_is_rejected():
    """Phoenix, Mauritius is at -20.4, 57.5 and would otherwise geocode happily."""
    site = {"site_id": "PHX-SKY", "expect_in_name": "Phoenix"}
    elsewhere = dict(GOOD_SKY_HARBOR, lat=-20.4, lon=57.5,
                     display_name="Phoenix, Plaines Wilhems District, Mauritius")
    problem = validate_geocode(site, elsewhere)
    assert problem is not None and "bbox" in problem


def test_bbox_covers_every_shipped_site(site_rows):
    for row in site_rows:
        lat, lon = float(row["lat"]), float(row["lon"])
        assert METRO_BBOX["lat_min"] <= lat <= METRO_BBOX["lat_max"]
        assert METRO_BBOX["lon_min"] <= lon <= METRO_BBOX["lon_max"]
