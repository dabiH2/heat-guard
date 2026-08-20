# HeatGuard — ordered work

Work top to bottom. T1, T2 and T7 need no API, so nothing blocks.
Tick items as you go and keep this file current.

---

## T1 · Lock 12 Phoenix sites → `config/sites.csv` + `config/sites.geojson`
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

## T2 · Fill in `config/thresholds.yaml`
Already drafted with the NWS/OSHA bands. Verify the numbers, confirm the action
mapping is sane, keep the sources.

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

## T6 · Build `router.py` + `tests/test_router.py` — **the core IP**
Fill in the decision table. Six question types, six refusals, a rationale sentence per
branch. Deterministic — no LLM call anywhere in this module.

Any question containing *how long*, *chronically*, *typically*, *this summer* or
*worst* is a duration question and must **never** be answered with `filter_type=1`.

Tests are pure logic: zero credits, no network. Get them green before anything else.

## T7 · Close the baseline gap → `docs/routing_spec.md`
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
