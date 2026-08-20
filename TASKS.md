# HeatGuard — ordered work

Work top to bottom. T1, T2 and T7 need no API, so nothing blocks.
Tick items as you go and keep this file current.

---

## T1 · Lock 12 Phoenix sites → `config/sites.csv` + `config/sites.geojson` — **DONE**

> Both files are now BUILD ARTIFACTS. Edit `config/sites_source.yaml`, then run
> `python scripts/build_sites.py`. Coordinates come from OpenStreetMap Nominatim with
> the resolved OSM object id recorded, because a hand-typed coordinate that is 400 m
> wrong returns a valid thermal profile for the wrong parking lot and raises nothing.
> That is not hypothetical — see `docs/site_selection.md`.
>
> The hypothesis below was accepted with one correction: Phoenix's heat island is
> **nocturnal**, so the downtown site's extra hours land in the evening. Night crews are
> therefore in the roster (real practice — Phoenix paves at night in summer), and an
> irrigated site provides a second, daytime contrast. Predictions are recorded per site
> as `expected_profile` and are tested against real data in T8.

Real locations a contractor or utility would have crews at: substations, city yards,
road-works corridors, water treatment, logistics depots. Research real coordinates.

**Selection criterion that matters most: thermal diversity.** The demo depends on two
sites *inverting* their ranking between peak temperature and hours-above-threshold.
If all twelve are similar, no inversion exists on any date and the demo dies.

Working hypothesis — challenge it if the data disagrees: a dense downtown site with
building shade and high thermal mass peaks *lower* but stays elevated *longer*
(restricted airflow, slow overnight release); an exposed desert-edge site peaks
*higher* and sheds heat faster. Seed both archetypes plus a few in between.

Schema in `config/sites.csv`. Also emit `sites.geojson`: ~200 m buffer polygon per
site, `[lon, lat]`, ring closed. Far under the 130 km² cap.

## T2 · Fill in `config/thresholds.yaml` — **DONE**
Already drafted with the NWS/OSHA bands. Verify the numbers, confirm the action
mapping is sane, keep the sources.

> Verified against primary sources; the draft had three real defects.
>
> 1. **Two silent holes.** `caution` ended at 90 and `extreme_caution` began at 91;
>    `danger` ended at 124 and `extreme_danger` began at 126. So 90.5 °F and 125 °F
>    matched no band. The draft numbers are the widely-copied *secondary*-source
>    transcription; [NWS](https://www.weather.gov/ama/heatindex) says Extreme Caution
>    90–103 and Extreme Danger **125**+. Now half-open `[min, max)`, contiguous, and
>    validated at load.
> 2. **`unsafe_from: danger` contradicted the thesis.** The project's central claim is
>    that workers have died at a daily max heat index of 86 °F; counting only hours above
>    103 °F makes the headline metric blind to the 86–103 °F range that argument is
>    about. Now **91 °F** — the first heat index at which OSHA prescribes a work/rest
>    cycle rather than general advice. T7 must report the number at 91 **and** 103.
> 3. **One action across a 20 °F span.** NWS `danger` is 103–124, but OSHA splits at 115.
>    Split into two tables: `nws_bands` (what the forecast says) and `osha_actions`
>    (what the supervisor does).
>
> Lookup lives in `src/heatguard/bands.py` — a leaf module under `router` and `metrics`,
> both of which need it. `band_for()` / `action_for()` are **total**: they never return
> `None`. 60 offline tests.

## T3 · Wire the API
- **Ask Gabriele for the quickstart repo URL** (pinned in hackathon Slack) and for
  where to paste the key. Do not read the key into anything committed.
- `.env` from `.env.example`; confirm `.env` is gitignored.
- Run quickstart notebook `00_setup`. Report **plan** and **credits remaining**.
- Run one call **both ways** — via the client, and as a manual POST-then-poll — so the
  raw `activity_id` and status payloads are visible once. Note observed latency.

## T4 · Turn constraints into tested facts → `docs/api-notes.md`
Probe each limit deliberately: non-US location, pre-2021 date, forecast beyond +12h,
AOI over 130 km². **Failed tasks cost nothing.** Record status code, error shape, and
crucially whether it fails loudly or returns something empty and plausible-looking.

Produce: constraint → how it fails → what the code catches.

Then confirm `filter_type` semantics against real responses — run the same site and
date under `filter_type=1` and `filter_type=3` and show how results differ in shape
and value. Confirm `env_params` returns heat index directly.

## T5 · Build `tools.py`
Typed wrappers over the endpoints, wrapping the quickstart client. Cache keyed on
`(endpoint, aoi_hash, date, time, filter_type, granularity)` into `data/fixtures/`.
Backoff 3s → 6s → 12s. Log every `activity_id`.

## T6 · Build `router.py` + `tests/test_router.py` — **the core IP** — **DONE**

> Built against the corrected mechanism: `analytic_type`, not `filter_type` alone. The
> table now selects BOTH, and `analytic_type` is the higher-value decision — `tcm` and
> `exceedance` are the same endpoint, same `filter_type`, same AOI, one optional string
> apart. See `docs/routing_spec.md`.
>
> The duration-marker rule is an **override on the classifier**, not just a post-check.
> It caught a real gap: "Tell me about the worst at this site" carries the authoritative
> marker `worst`, matches no comparison phrasing, fell through to SNAPSHOT, and would
> have been answered with a single hour. Classifier miss -> escalate and record it in
> `escalated_from`. Table bug -> `RouterInvariantError`, crash loudly.
>
> `WRONG_LAYER_WOULD_MISLEAD` has two real triggers, both refusing questions the API
> would happily answer: a chronic question scoped to one day, and a duration question
> scoped to one hour. Added `EXCEEDS_30_DAY_WINDOW` — past 30 days the API truncates
> quietly.
>
> 225 offline tests, zero credits, zero network, zero skips.

Fill in the decision table. Six question types, six refusals, a rationale sentence per
branch. Deterministic — no LLM call anywhere in this module.

Any question containing *how long*, *chronically*, *typically*, *this summer* or
*worst* is a duration question and must **never** be answered with `filter_type=1`.

Tests are pure logic: zero credits, no network. Get them green before anything else.

## T7 · Close the baseline gap → `docs/routing_spec.md` — **DONE**

> Pressure-tested and **replaced**. "Unsafe exposure-hours avoided" is signed, and the
> sign flips on the best case: for the Chase Tower night crew the city-wide *daytime*
> high implies ~0 relevant hours across a 21:00-05:30 shift while the real profile shows
> several, so the formula returns a NEGATIVE number for the strongest case in the
> project. The tool did not avoid those hours, it revealed them. It also sums two
> opposite-signed wins (over-warning corrected vs under-warning corrected) that cancel,
> so the tool can be right at twelve sites and net to ~zero.
>
> Replaced by three non-cancelling numbers, all in WORKER-hours and all inside the shift
> window: `unsafe_worker_hours_caught`, `productive_worker_hours_recovered`,
> `decisions_changed`.
>
> **The baseline is not a proxy.** The official Phoenix temperature is observed at KPHX -
> Sky Harbor - which is PHX-SKY in the roster. The counterfactual is one of the twelve
> sites we already measure, and structurally one of the hottest.
>
> Two quiet bugs fixed on the way: boundary readings are now weighted by their overlap
> with the shift (counting readings as hours inflated every day shift ~6%), and a night
> shift given only one calendar day raises instead of undercounting by two thirds.
>
> 251 offline tests.

The headline metric "unsafe exposure-hours avoided" has no baseline. Proposal: the
supervisor's current practice — one city-wide Phoenix forecast high applied uniformly
to all sites — versus the per-site hourly profile. Pressure-test it, propose better if
better exists, then implement in `metrics.py`.

## T8 · Find the demo day → `docs/demo_day_candidates.md`
One historical date (2021→now) where two sites invert: one higher peak, the other far
longer above the danger band.

Shortlist from public Phoenix weather history, then confirm with cheap `filter_type=3`
calls. Worth testing: monsoon days (Jul–Sep) carry humidity that keeps the *heat index*
elevated for long stretches even when the raw temperature peak is unremarkable, whereas
dry pre-monsoon June days spike higher and fall away faster. Verify before relying on it.

**Highest risk in the project.** If no inversion exists, the fallback is contrasting the
*same* site under two layers rather than two sites. Find out early.

## T9 · `agent.py` — thin
LLM parses intent and narrates. Calls `router.classify()` first, then executes the
returned plan via `tools.py`. Never selects a layer itself.

## T10 · `app.py` — deploy a skeleton early
Streamlit. Site picker, date picker, the call, the chosen layer + rationale, the
refusal path. **Deploy a hardcoded version to a public URL on Aug 24**, then keep
shipping to it. The live URL is a submission gate — turn the cliff into a slope.

## T11 · The money shot
Two sites, same day, opposite conclusions under `filter_type=1` vs `filter_type=3`.
Screenshot it. Report exposure-hours avoided.

## T12 · Submission
Freeze Aug 27. Then README, 500-word summary (problem → user → endpoints → measured
result), add `Hackathon-FG (hackathon@fortyguard.com)` as collaborator, ~3-min video,
submit **Aug 29**.
