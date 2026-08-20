"""
build_sites.py — turn config/sites_source.yaml into config/sites.csv + sites.geojson.

Run:  python scripts/build_sites.py            (uses config/geocode_cache.json)
      python scripts/build_sites.py --refresh  (re-queries Nominatim)

Why this exists rather than a hand-typed CSV: a coordinate that is 400 m wrong is the
quietest failure mode in the project. The FortyGuard API will return a perfectly valid
thermal profile for the wrong parking lot and raise nothing. Derived coordinates carry
provenance (OSM object id, the geocoder's own display name) and can be re-checked;
typed ones cannot.

The geocode cache is committed on purpose. It makes the build reproducible offline and
means a judge can see exactly which OSM object each site resolved to.

Five guards, all of which abort the build loudly rather than emit a plausible file:

  1. bbox           the point must land inside the Phoenix metro.
  2. expect_in_name the geocoder's own display_name must contain the expected substring.
  3. street-centroid an OSM class of `highway` is rejected unless the site opts in with
                    allow_street_geocode. This is the guard that matters most: during T1
                    the query "5615 South 91st Avenue, Tolleson" resolved to the street
                    centroid of 91st Avenue, 4.5 km off target, inside the bbox, and
                    entirely plausible-looking. Guards 1 and 2 alone would have let a
                    variant of it through.
  4. separation     no two AOIs may come within min_separation_m. Overlapping polygons
                    would double-count exposure-hours in the headline metric.
  5. geometry       ring closed, exterior ring counter-clockwise (RFC 7946), area under
                    the ~130 km2 AOI cap.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "config" / "sites_source.yaml"
CACHE = ROOT / "config" / "geocode_cache.json"
OUT_CSV = ROOT / "config" / "sites.csv"
OUT_GEOJSON = ROOT / "config" / "sites.geojson"

NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "heatguard-fortyguard-hackathon/0.1 (dabi.ai.eng@gmail.com)"
RATE_LIMIT_S = 1.1  # Nominatim usage policy: at most 1 request/second.

# Phoenix metropolitan area, generously drawn. A geocoder that returns Phoenix, Mauritius
# or drops a pin in the Pacific must fail the build rather than silently poison the AOI.
METRO_BBOX = {"lat_min": 32.9, "lat_max": 34.0, "lon_min": -113.0, "lon_max": -111.3}

# CLAUDE.md, verified: AOI <= ~130 km2 (50 mi2). We stay three orders of magnitude below.
MAX_AOI_KM2 = 130.0

CIRCLE_VERTICES = 24  # 24-gon inscribed error at r=200 m is under 1.8 m. Plenty.

CSV_COLUMNS = [
    "site_id", "name", "lat", "lon", "archetype", "expected_profile",
    "crew_size", "shift_start", "shift_end", "night_shift", "shift_hours",
    "why_chosen", "osm_type", "osm_id", "geocoded_name",
]


# ----------------------------------------------------------------- geodesy

def metres_per_degree(lat_deg: float) -> tuple[float, float]:
    """Metres per degree of latitude and longitude at a given latitude.

    WGS84 series expansion, accurate to well under a metre at Phoenix latitudes.
    Used instead of projecting with pyproj so the build has one fewer dependency.
    """
    phi = math.radians(lat_deg)
    m_per_deg_lat = 111132.92 - 559.82 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_per_deg_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi)
    return m_per_deg_lat, m_per_deg_lon


def buffer_ring(lat: float, lon: float, radius_m: float,
                vertices: int = CIRCLE_VERTICES) -> list[list[float]]:
    """A closed, counter-clockwise [lon, lat] ring approximating a circle.

    RFC 7946 asks for counter-clockwise exterior rings. Building the vertices with
    increasing bearing measured counter-clockwise from east gives that directly.
    """
    m_lat, m_lon = metres_per_degree(lat)
    ring: list[list[float]] = []
    for i in range(vertices):
        theta = 2 * math.pi * i / vertices          # CCW from due east
        d_lon = (radius_m * math.cos(theta)) / m_lon
        d_lat = (radius_m * math.sin(theta)) / m_lat
        ring.append([round(lon + d_lon, 7), round(lat + d_lat, 7)])
    ring.append(ring[0])                             # close the ring
    return ring


def ring_area_km2(ring: list[list[float]], lat_ref: float) -> float:
    """Shoelace area of a small lon/lat ring, converted to km^2.

    Valid because at 400 m across, the local tangent plane is flat to far better than
    the precision anyone needs here.
    """
    m_lat, m_lon = metres_per_degree(lat_ref)
    pts = [(x * m_lon, y * m_lat) for x, y in ring]
    total = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0 / 1e6


def ring_is_ccw(ring: list[list[float]]) -> bool:
    """Signed shoelace > 0 means counter-clockwise in a standard x-east/y-north frame."""
    total = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        total += x1 * y2 - x2 * y1
    return total > 0


def separation_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Flat-earth distance in metres between two (lat, lon) pairs.

    Exact enough across a metro area, and the only use is a threshold comparison.
    """
    lat_mid = (a[0] + b[0]) / 2
    m_lat, m_lon = metres_per_degree(lat_mid)
    return math.hypot((a[0] - b[0]) * m_lat, (a[1] - b[1]) * m_lon)


# --------------------------------------------------------------- geocoding

def load_cache() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def geocode(query: str, cache: dict, *, refresh: bool) -> dict:
    """Resolve a free-text query to a cached geocode record.

    Cache-first by default. The cache is committed, so a clean checkout rebuilds the
    site roster byte-identically without touching the network.
    """
    if not refresh and query in cache:
        return cache[query]

    time.sleep(RATE_LIMIT_S)
    resp = requests.get(
        NOMINATIM,
        params={"q": query, "format": "json", "limit": 1, "countrycodes": "us"},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    hits = resp.json()
    if not hits:
        raise SystemExit(f"GEOCODE FAILED — no result for: {query!r}")

    hit = hits[0]
    record = {
        "lat": round(float(hit["lat"]), 6),
        "lon": round(float(hit["lon"]), 6),
        "osm_type": hit.get("osm_type", ""),
        "osm_id": hit.get("osm_id", ""),
        "display_name": hit.get("display_name", ""),
        "class": hit.get("class", ""),
        "type": hit.get("type", ""),
    }
    cache[query] = record
    return record


# ------------------------------------------------------------------ validation

def validate_geocode(site: dict, rec: dict) -> str | None:
    """Guards 1-3. Returns a human-readable problem, or None if the record is sound.

    Pure and side-effect free so tests/test_build_sites.py can pin the exact bad
    Nominatim record that caused the 91st Avenue mis-resolution during T1.
    """
    sid = site["site_id"]
    lat, lon = rec["lat"], rec["lon"]

    if not (METRO_BBOX["lat_min"] <= lat <= METRO_BBOX["lat_max"]
            and METRO_BBOX["lon_min"] <= lon <= METRO_BBOX["lon_max"]):
        return (f"{sid}: geocoded to ({lat}, {lon}) — outside the Phoenix metro bbox. "
                f"Resolved to {rec['display_name']!r}")

    expect = site["expect_in_name"]
    if expect.lower() not in rec["display_name"].lower():
        return (f"{sid}: expected {expect!r} in the resolved name but got "
                f"{rec['display_name']!r}")

    if rec.get("class") == "highway" and not site.get("allow_street_geocode"):
        return (f"{sid}: resolved to a street centroid ({rec['class']}/{rec.get('type')}) "
                f"— the address was not found and Nominatim fell back to the road. Fix "
                f"the query, or set allow_street_geocode if the site really is a road.")

    return None


# ------------------------------------------------------------------- build

def shift_hours(start: str, end: str) -> float:
    """Shift length in hours, handling the wrap past midnight that night crews need."""
    sh, sm = (int(p) for p in start.split(":"))
    eh, em = (int(p) for p in end.split(":"))
    minutes = (eh * 60 + em) - (sh * 60 + sm)
    if minutes <= 0:
        minutes += 24 * 60
    return round(minutes / 60, 2)


def crosses_midnight(start: str, end: str) -> bool:
    return end <= start


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refresh", action="store_true",
                    help="re-query Nominatim instead of using config/geocode_cache.json")
    args = ap.parse_args()

    spec = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    buffer_m = float(spec["buffer_m"])
    min_sep = float(spec["min_separation_m"])
    cache = load_cache()

    rows: list[dict] = []
    features: list[dict] = []
    problems: list[str] = []
    placed: list[tuple[str, float, float]] = []

    for site in spec["sites"]:
        rec = geocode(site["query"], cache, refresh=args.refresh)
        lat, lon = rec["lat"], rec["lon"]
        sid = site["site_id"]

        # Guards 1-3 — bbox, expected name, street-centroid fallback.
        if (problem := validate_geocode(site, rec)) is not None:
            problems.append(problem)
            continue

        # Guard 4 — AOIs must not overlap or exposure-hours get double-counted.
        too_close = [
            (other_id, d)
            for other_id, olat, olon in placed
            if (d := separation_m((lat, lon), (olat, olon))) < min_sep
        ]
        if too_close:
            near = ", ".join(f"{oid} at {d:.0f} m" for oid, d in too_close)
            problems.append(f"{sid}: closer than {min_sep:.0f} m to {near}")
            continue

        ring = buffer_ring(lat, lon, buffer_m)
        # Guard 5 — geometry.
        area = ring_area_km2(ring, lat)
        if area > MAX_AOI_KM2:
            problems.append(f"{sid}: AOI {area:.3f} km2 exceeds the {MAX_AOI_KM2} km2 cap")
            continue
        if ring[0] != ring[-1]:
            problems.append(f"{sid}: ring not closed")
            continue
        if not ring_is_ccw(ring):
            problems.append(f"{sid}: exterior ring is not counter-clockwise")
            continue

        placed.append((sid, lat, lon))
        rows.append({
            "site_id": sid,
            "name": site["name"],
            "lat": lat,
            "lon": lon,
            "archetype": site["archetype"],
            "expected_profile": site["expected_profile"],
            "crew_size": site["crew_size"],
            "shift_start": site["shift_start"],
            "shift_end": site["shift_end"],
            "night_shift": crosses_midnight(site["shift_start"], site["shift_end"]),
            "shift_hours": shift_hours(site["shift_start"], site["shift_end"]),
            "why_chosen": " ".join(site["why_chosen"].split()),
            "osm_type": rec["osm_type"],
            "osm_id": rec["osm_id"],
            "geocoded_name": rec["display_name"],
        })

        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": {
                "site_id": sid,
                "name": site["name"],
                "archetype": site["archetype"],
                "expected_profile": site["expected_profile"],
                "centroid": [lon, lat],
                "buffer_m": buffer_m,
                "area_km2": round(area, 4),
            },
        })

    CACHE.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if problems:
        print("BUILD ABORTED — validation failures:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    OUT_GEOJSON.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, indent=2) + "\n",
        encoding="utf-8",
    )

    closest = min(
        ((separation_m((a[1], a[2]), (b[1], b[2])), a[0], b[0])
         for i, a in enumerate(placed) for b in placed[i + 1:]),
        default=(float("inf"), "", ""),
    )

    total_area = sum(f["properties"]["area_km2"] for f in features)
    print(f"{len(rows)} sites -> {OUT_CSV.relative_to(ROOT)} + "
          f"{OUT_GEOJSON.relative_to(ROOT)}")
    print(f"AOI per site {features[0]['properties']['area_km2']:.4f} km2 · "
          f"total {total_area:.4f} km2 · cap {MAX_AOI_KM2} km2 per request")
    print(f"closest pair {closest[1]}<->{closest[2]} at {closest[0]:.0f} m "
          f"(floor {min_sep:.0f} m, AOI diameter {2 * buffer_m:.0f} m)\n")

    width = max(len(r["name"]) for r in rows)
    print(f"{'site_id':<10} {'name':<{width}} {'lat':>10} {'lon':>11}  "
          f"{'expected_profile':<22} shift")
    for r in rows:
        night = " (night)" if r["night_shift"] else ""
        print(f"{r['site_id']:<10} {r['name']:<{width}} {r['lat']:>10.6f} "
              f"{r['lon']:>11.6f}  {r['expected_profile']:<22} "
              f"{r['shift_start']}-{r['shift_end']}{night}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
