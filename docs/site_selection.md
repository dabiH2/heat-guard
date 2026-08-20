# Site selection — T1

Twelve Phoenix-metro job sites, chosen for **thermal diversity during shift hours**.

Source of truth: [`config/sites_source.yaml`](../config/sites_source.yaml).
`config/sites.csv` and `config/sites.geojson` are build artifacts —
`python scripts/build_sites.py` regenerates them.

---

## The roster

| site_id | Site | Archetype | Predicted profile | Crew | Shift |
|---|---|---|---|---|---|
| PHX-SKY | Sky Harbor airfield ramp | industrial_asphalt | high_peak_long_tail | 14 | 05:00–13:30 |
| PHX-27TH | 27th Ave Resource Innovation Campus | industrial_asphalt | high_peak_long_tail | 22 | 05:30–14:00 |
| PHX-DVT | Deer Valley airport apron | industrial_asphalt | high_peak_long_tail | 8 | 06:00–14:30 |
| PHX-CHASE | Chase Tower block, N Central Ave | downtown_canyon | clipped_peak_long_tail | 6 | **21:00–05:30** |
| PHX-JEFF | Superior Court complex, W Jefferson | downtown_canyon | clipped_peak_long_tail | 5 | **21:00–05:30** |
| PHX-ROOS | Roosevelt Row corridor | downtown_canyon | clipped_peak_long_tail | 4 | **20:00–04:30** |
| PHX-SMTN | South Mountain Park trailhead | desert_edge | high_peak_fast_cool | 5 | 05:00–13:00 |
| PHX-ESTR | Estrella Mountain yard | desert_edge | high_peak_fast_cool | 6 | 05:00–13:00 |
| PHX-L202 | Loop 202 corridor paving | desert_edge | high_peak_fast_cool | 18 | **19:00–05:00** |
| PHX-TRES | Tres Rios wetlands (91st Ave) | park_adjacent | depressed_peak | 11 | 06:00–14:30 |
| PHX-ENCA | Encanto Park grounds | park_adjacent | depressed_peak | 7 | 05:30–14:00 |
| PHX-UNHL | Union Hills Water Treatment Plant | mixed_suburban | high_peak_fast_cool | 9 | 06:00–14:30 |

Bold shifts are night crews. 125 workers across 12 sites; 33 of them work nights.

Roster spans 34 km. Each AOI is a 200 m-radius polygon of 0.124 km² — about **313×
under the 15 mi² (38.85 km²) plan cap** that FortyGuard engineering states on camera.
(The handbook’s ~130 km² / 50 mi² figure is unsourced and 3.4× more generous; we build
against the smaller number.) AOI size is never the binding constraint on a request.

---

## The correction to the T1 hypothesis

`TASKS.md` proposed: a dense downtown site peaks *lower* but stays elevated *longer*;
an exposed desert-edge site peaks *higher* and sheds heat faster.

**The mechanism is right.** Sky-view factor is the dominant control on nocturnal cooling
rate. A street canyon can only radiate to the strip of sky it can see, so it cools slowly;
open desert radiates to the whole hemisphere under dry, transparent air and cools fast.
Phoenix has a large, well-documented **nocturnal** urban heat island.

**The operational hole:** it is nocturnal. By day, Phoenix is roughly neutral-to-cooler
than the surrounding desert, because irrigated and shaded surfaces evaporate and bare
desert does not. So the downtown site's extra hours above the danger band land mostly in
the **evening**. If every crew clocks out at 15:30, those extra hours are real physics
and a fake decision — nobody was standing in them. "Unsafe exposure-hours avoided" would
be counting hours nobody was ever exposed to, and the headline number carrying 40% of the
score would be measuring a crew that does not exist.

Two corrections, both applied:

**(a) Night shifts, because they are real.** Phoenix genuinely paves roads and does
downtown utility work at night in summer, specifically to dodge daytime heat. Putting
night crews on the canyon and freeway sites is not a demo convenience — it is what
actually happens, and it converts the nocturnal heat island from a curiosity into a
decision. **A night crew downtown is the strongest case in the project**: the city-wide
forecast *high* is a daytime number and says nothing whatsoever about a 21:00–05:30 shift.

**(b) A daytime lever as well.** The irrigated and open-water sites should run measurably
cooler at midday through evaporation. That gives a second, independent contrast that lands
inside a normal day shift, so the demo does not stand or fall on the nocturnal mechanism.

---

## Predictions, written down before the data

Every site carries a falsifiable `expected_profile`. **T8 tests these.**

| Profile | Mechanism | Sites |
|---|---|---|
| `high_peak_fast_cool` | open, dry, high sky-view factor | PHX-SMTN, PHX-ESTR, PHX-L202, PHX-UNHL |
| `clipped_peak_long_tail` | shade + low sky-view factor + thermal mass | PHX-CHASE, PHX-JEFF, PHX-ROOS |
| `high_peak_long_tail` | no shade **and** massive thermal mass | PHX-SKY, PHX-27TH, PHX-DVT |
| `depressed_peak` | evaporative — irrigation, open water | PHX-TRES, PHX-ENCA |

The inversion the demo hunts is `high_peak_fast_cool` vs `clipped_peak_long_tail`.
`high_peak_long_tail` sites are the "worst site" headline. `depressed_peak` sites are the
*why* — land cover — and the mitigation story.

**Sites whose prediction fails are kept and reported.** A roster where all twelve came
true would be evidence of tuning, not of a working instrument.

Three predictions are deliberately vulnerable:

- **PHX-ROOS is predicted to land in the middle.** If the canyon mechanism is graded
  rather than binary, a partially-enclosed block must sit between the full canyon and the
  open sites. If it pins to an extreme, the story is wrong.
- **PHX-DVT and PHX-UNHL sit 1.7 km apart** under identical regional weather with
  different surfaces. If the API returns the same numbers for both, it is re-reporting a
  regional forecast rather than measuring a surface — and the entire per-site claim
  collapses. This is the cheapest possible test of the product's core premise.
- **PHX-L202 may turn out to be the safest crew on the roster** despite one of the
  highest daytime peaks, because open desert dumps heat fast after dark. If the tool says
  so, it is arguing against the intuition that a hot site means a hot shift — which is
  exactly why duration inside the shift window beats a reported maximum.

PHX-JEFF is **not** claimed as an independent replicate — it is 571 m from PHX-CHASE in
the same district and the same air. It tests something narrower and still worth knowing:
whether the API's 20 m grid resolves intra-district variation at all.

---

## Why coordinates are derived, not typed

A coordinate that is 400 m wrong is the quietest failure available here. The FortyGuard
API returns a perfectly valid thermal profile for the wrong parking lot and raises
nothing — the same class of failure as picking the wrong analysis layer, which is what
this whole project is about.

This is not hypothetical. During T1 the query
`"5615 South 91st Avenue, Tolleson, Arizona"` resolved to the **street centroid of 91st
Avenue** — 4.5 km north of the wastewater plant, still inside Maricopa County, still a
perfectly plausible coordinate. A bounding-box check would have passed it.

So `scripts/build_sites.py` runs five guards, each aborting the build loudly:

| # | Guard | Catches |
|---|---|---|
| 1 | Phoenix metro bounding box | Phoenix, Mauritius; a transposed sign |
| 2 | `expect_in_name` substring | resolved to a different object entirely |
| 3 | OSM class `highway` rejected unless opted in | **the 91st Avenue failure** — address not found, fell back to the road |
| 4 | minimum 450 m separation | overlapping AOIs double-counting exposure-hours |
| 5 | ring closed, counter-clockwise, under the AOI cap | invalid GeoJSON; oversized requests |

Guard 3 is the one that matters. Guards 1 and 2 alone would let a variant through.

`config/geocode_cache.json` is committed so a clean checkout rebuilds the roster
byte-identically without network access, and so the exact OSM object behind each site is
inspectable.

The real bad record is fixtured in `tests/test_build_sites.py::test_street_centroid_fallback_is_rejected`.
If someone loosens the guards, that test fails.

---

## Verification

```bash
python scripts/build_sites.py     # rebuild; aborts loudly on any guard failure
pytest tests/test_build_sites.py tests/test_site_roster.py -q
```

45 tests, offline, zero credits. `tests/test_site_roster.py` is the T1 acceptance test:
it cannot prove an inversion exists — only T8's real data can — but it fails fast if the
roster loses the structural preconditions for one.
