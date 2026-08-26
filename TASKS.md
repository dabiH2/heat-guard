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

## T3 · Wire the API — **DONE**

> Quickstart located by mining competitor repos (`FortyGuard-Tech/temperature-api-quickstart`),
> vendored at `f6de12d`. `.env` created and confirmed gitignored; the key is read via
> `os.environ` and never printed — `scripts/t3_probe.py` masks it from every line of
> output and every fixture it writes.
>
> **Plan `Hackathon`, 2,000,000 credits, key expires 2026-09-21T19:04:29Z** — five days
> after judging ends. Ran the same call both ways: manual POST-then-poll and via the
> client. Identical results. **Submit -> `Completed` in ~24 s** over three polls at
> 3/6/12 s backoff. The post-submit 404 window the client guards against was never
> observed in ~15 calls.
>
> Raw payloads in `data/fixtures/t3/`.

- **Ask Gabriele for the quickstart repo URL** (pinned in hackathon Slack) and for
  where to paste the key. Do not read the key into anything committed.
- `.env` from `.env.example`; confirm `.env` is gitignored.
- Run quickstart notebook `00_setup`. Report **plan** and **credits remaining**.
- Run one call **both ways** — via the client, and as a manual POST-then-poll — so the
  raw `activity_id` and status payloads are visible once. Note observed latency.

## T4 · Turn constraints into tested facts → `docs/api-notes.md` — **DONE**

> Nine constraints probed. **Three fail SILENTLY and all three are billed**: non-US
> (`Completed`, 0 tiles), tomorrow's date (`Completed`, one flat value for the whole day),
> and `exceedance` with no `threshold` (`Completed`, silently defaults to 30 °C, returns
> 24 h). Loud and free: future dates (400), `filter_type=5` (422), bad granularity (422).
> A fourth mode found: pre-2021 sits in `Processing` >188 s then turns `Failed` — slow,
> not loud, not wrong.
>
> **THE UNIT TRAP, EXECUTED LIVE.** Same endpoint, same AOI, same date, same filter_type,
> same analytic_type — the only difference is whether the threshold was converted:
> `threshold=35.00` (95 °F correctly converted) returns **17.0 hours**;
> `threshold=95` (sent raw, read as 95 °C) returns **0.0 hours**. Both `Completed`, both
> billed 4,220 credits, nothing raised. 17 hours of exposure reported as zero.
>
> Corrections to CLAUDE.md: the forecast horizon is not +12 h; `filter_type=5` does not
> exist; the AOI cap is not enforced at 447 km²; granularity does **not** affect cost;
> **cost is 4,220 credits per call FLAT, so ~474 calls is the whole budget**; the API is
> **Celsius** and the vendor client docstring saying °F is wrong.
>
> Open questions 2, 5 and 6 closed; 7 added. All of it pinned offline in
> `tests/test_api_contract.py` so it survives the key expiring.

Probe each limit deliberately: non-US location, pre-2021 date, forecast beyond +12h,
AOI over 130 km². **Failed tasks cost nothing.** Record status code, error shape, and
crucially whether it fails loudly or returns something empty and plausible-looking.

Produce: constraint → how it fails → what the code catches.

Then confirm `filter_type` semantics against real responses — run the same site and
date under `filter_type=1` and `filter_type=3` and show how results differ in shape
and value. Confirm `env_params` returns heat index directly.

## T5 · Build `tools.py` — **DONE**

> Typed wrappers over the vendored client, plus the cache. Validated end to end against
> the live API: one call spent 4,220 credits, the identical second call was served from
> cache for **zero**, offline mode serves hits and raises `CacheMiss` on a miss, and the
> Fahrenheit-threshold guard refuses before anything reaches the wire.
>
> **The cache is the deployment strategy, not an optimisation.** The key expires
> 2026-09-21 and the live link must outlive it, so `data/fixtures/api/` is the production
> data store and ships with the repo. `HEATGUARD_OFFLINE=1` makes the network path
> unreachable.
>
> `threshold_c` is written to the wire in exactly one place, and three guards sit in
> front of it: missing threshold (the raw API silently defaults to 30 °C and returns 24 h),
> missing direction, and any threshold above 60 °C — which is the live-measured trap that
> returned 0.0 hours where the truth was 17.0.
>
> The cache key includes `threshold_c`. Without it the trapped call and the correct call
> collide and the cache serves the wrong one. 40 offline tests; 314 total.

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

## T8 · Find the demo day → `docs/demo_day_candidates.md` — **DONE**

> 610 Phoenix summer days shortlisted from free Open-Meteo history for zero credits, then
> 2025-07-15 fetched across all 12 sites.
>
> **The thesis is confirmed on our own data.** Peak spread 1.96 °F (1.09 °C) across 11
> sites — 1.9% relative. Duration spread 2.62 h at the 103 °F band — 37% relative.
> **Duration discriminates 20x better than peak.** Close to FortyGuard's own case study
> (0.7 °C peak spread vs 19 h), reproduced independently.
>
> **`filter_type=2` scopes exceedance to an hour range** — so exposure can be measured
> inside the shift a crew actually works. That is the T1 correction in code.
>
> **MY T1 PREDICTIONS FAILED — 2 of 11, worse than chance.** Reported, not dropped, as
> `docs/site_selection.md` committed to. What the API separates is urban core from
> periphery, not surface type: the three sites that differ are the three outermost, while
> canyon, asphalt and irrigated park inside the core return identical numbers. The project
> thesis survives; the site-selection hypothesis does not.

One historical date (2021→now) where two sites invert: one higher peak, the other far
longer above the danger band.

Shortlist from public Phoenix weather history, then confirm with cheap `filter_type=3`
calls. Worth testing: monsoon days (Jul–Sep) carry humidity that keeps the *heat index*
elevated for long stretches even when the raw temperature peak is unremarkable, whereas
dry pre-monsoon June days spike higher and fall away faster. Verify before relying on it.

**Highest risk in the project.** If no inversion exists, the fallback is contrasting the
*same* site under two layers rather than two sites. Find out early.

## T9 · `agent.py` — thin — **DONE**

> route -> execute -> narrate -> log. Routing happens BEFORE any call, so a refusal costs
> nothing and the layer is fixed before a byte of data is seen.
>
> **The LLM is inert by construction.** With no ANTHROPIC_API_KEY the templated narration
> is used and the answer is identical apart from wording — enforced by a test that runs
> the same question with and without a model and asserts every decisive field matches.
> A safety tool whose recommendation depends on whether a language model was reachable is
> not a safety tool. It also has to keep working after the key expires on 21 September.
>
> The heat-index -> air-temperature conversion lives here rather than in the router,
> because it needs the site's live humidity. `env_params` failing falls back to a stated
> Phoenix default rather than pretending to have measured it.
>
> An empty API result is never narrated as an all-clear — it says "coverage gap, not a
> safe reading", which matters because two separate silent failures produce exactly that
> shape. 16 offline tests; 334 total.

LLM parses intent and narrates. Calls `router.classify()` first, then executes the
returned plan via `tools.py`. Never selects a layer itself.

## T10 · `app.py` — deploy a skeleton early — **BUILT, DEPLOY PENDING**

> Four tabs: the morning call (roster-wide headline), an interactive question, the unit
> trap, and the decision table. See `DEPLOY.md`.
>
> **Offline by DEFAULT — opt in to spending, never out.** A deployed app that can reach
> the API can be made to spend 4,220 credits per click, and there is no rate limit between
> a curious judge and the budget. `HEATGUARD_ONLINE=1` is required to go live, which only
> happens on a dev machine. The deployed instance needs no API key at all.
>
> Streamlit Community Cloud connection needs Gabriele's GitHub OAuth — see `DEPLOY.md`.

Streamlit. Site picker, date picker, the call, the chosen layer + rationale, the
refusal path. **Deploy a hardcoded version to a public URL on Aug 24**, then keep
shipping to it. The live URL is a submission gate — turn the cliff into a slope.

## T11 · The money shot — **FOUND**

> Not the shape predicted. Better.
>
> **701 worker-hours vs 58.** Applying the city-wide figure uniformly across 107 workers
> implies 701 unsafe worker-hours. Scoped to the shifts those crews actually work: 58.
> **643 worker-hours — 92% — of "unsafe exposure" nobody was ever standing in**, because
> the dangerous window runs ~13:00-20:00 and almost every shift on the roster is outside
> it.
>
> And a real inversion in the metric that matters: 8 of 11 sites tie at 7.0 h above
> threshold and are indistinguishable by heat; scoped to shifts only 4 carry exposure at
> all, and PHX-27TH tops it at 22 worker-hours against PHX-L202's 18 — the same 1 hour of
> overlap, but 22 people standing in it rather than 18. **Heat maps rank tiles. Crews are
> what get hurt.**

Two sites, same day, opposite conclusions under `filter_type=1` vs `filter_type=3`.
Screenshot it. Report exposure-hours avoided.

## T12 · Submission
Freeze Aug 27. Then README, 500-word summary (problem → user → endpoints → measured
result), add `Hackathon-FG (hackathon@fortyguard.com)` as collaborator, ~3-min video,
submit **Aug 29**.
