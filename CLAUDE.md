# HeatGuard — project context for Claude Code

Read this first, every session. It is the verified ground truth; do not re-derive it.

## What this is

Solo entry for **FortyGuard Hackathon'26**, Track 4 (Government & Environment) × Track 6 (Agentic).

An outdoor-worker heat-safety agent for Phoenix job sites. It classifies each question against a decision table **before** calling the API, states which temperature analysis layer it chose and why, and **refuses** when the data cannot answer the question.

**Owner:** Gabriele Desimini · **Effective deadline: Aug 29 2026** (official is Aug 30 23:59 GST = 21:59 Rome, but connectivity is lost from Aug 30).

Strategy, rubric and rationale live one level up in `../08-spec-p3.md` and `../09-implementation-plan.md`. Read them once at the start of a session.

## The thesis

Fawad Shah (FortyGuard engineering lead) warned in the onboarding webinar: *"The API is asynchronous, and picking the wrong analysis layer will give you a confident wrong answer."* Wrong layer → plausible, well-formatted, wrong number, **no error raised**.

OSHA documents outdoor-worker heat-stroke deaths at a daily maximum heat index of only **86 °F** — inside the "Caution" band. So peak temperature is a poor predictor of harm; **duration above threshold** is the real signal. Ask a duration question, answer it with a single-hour query, and you get the opposite operational decision.

That inversion is both the product and the demo.

## Judging (weights are exact)

| Criterion | Weight |
|---|---|
| Impact & relevance | **40%** |
| Technical execution | **35%** |
| Innovation | **15%** |
| Communication | **10%** |

Handbook: *"Judges reward applied relevance over flashy demos."* A winning project needs the platform central not decorative, a clear problem and user, **a measurable outcome** (their example: "−7 °F on this route"), and a path to deployment.

## API — verified facts

Base `https://api.fortyguard.com` · header `api-key: <key>` · `Content-Type: application/json`

| Endpoint | Returns | Plan |
|---|---|---|
| `POST /v1/heatmap` | tile-by-tile thermal map over a polygon AOI | All |
| `POST /v1/env_params` | heat index, AQI, solar irradiance at a point | All |
| `POST /v1/satellite` | land-cover segmentation | Premium |
| `POST /v1/streetview` | ground-level segmentation | Premium |
| `POST /v1/heat_intelligence` | multi-dimensional analysis as a PDF | Premium |
| `POST /v1/system/fetch-api-key-usage` | plan + credit balance | All |
| `GET /v1/status/{activity_id}` | status / result of a submitted task | All |

**Async pattern:** POST → `activity_id` → poll `GET /v1/status/{activity_id}` until `succeeded`/`completed` (result in `data.result`) or `failed`/`error`. **Failed tasks cost nothing** — credits are deducted only on success, so probe freely.

**Hard constraints:**
- **US-only.** Non-US polygons error or return empty.
- **Dates 2021-01-01 → now.** Heatmap alone forecasts to **now + 12h**.
- **AOI ≤ ~130 km² (50 mi²).**
- `granularity`: **60 / 80 / 100 m** — smaller costs more credits.
- `filter_type`: **1** = single hour · **2** = hour range (+`end_time`) · **3** = entire day · **4** = day range · ~~**5** = single month~~ — **the vendor client documents only 1–4. Probe 5 in T4 before relying on it.**

**`analytic_type` on `/v1/heatmap` — was missing from this file, and it is load-bearing:**

| value | returns | units |
|---|---|---|
| `tcm` (default) | snapshot temperature per tile | °F |
| `time_of_measure` | UTC hour-of-day of each cell's peak | 0–23 |
| **`exceedance`** | **hours each cell spends past `threshold`** | hour |
| **`persistence`** | **longest continuous run of such hours** | hour |

The duration metric this project is built on is a first-class API product, not something
we derive. `exceedance`/`persistence` require `threshold` **and** `direction`.

This makes the layer trap *worse*, which is good for the pitch: `tcm` and `exceedance` are
the same endpoint, same `filter_type`, same AOI — one optional string apart. So the router
selects `analytic_type` too, and that is its highest-value decision.

**⚠ UNIT TRAP — `threshold` is in °C while `tcm` tiles are in °F.** Pass `threshold=91`
meaning °F and the API reads 91 °C = 195.8 °F: exceedance returns **0 hours everywhere**,
status `succeeded`, credit spent, and the tool reports "no unsafe exposure at any site".
A confidently-formatted **all-clear** — the worst wrong answer a safety tool can give.
Conversion happens in `tools.py` and nowhere else; every signature is unit-suffixed
(`threshold_c`, `heat_index_f`). A bare `threshold` must not exist in our code.

**`env_params` returns `heat_index_celsius`** (open question #4: answered — directly, but
in °C), plus `wet_bulb_temperature_celsius`, humidity, six AQI series, solar irradiance,
and 24 **local-time** timestamps. Phoenix is MST year-round, so shift windows — including
ones wrapping past midnight — map straight onto them.
- Data is measured **2 m above ground** at **20 m spatial resolution**. Do not claim 2 m spatial resolution.

**The quickstart repo ships a Python client that already does auth and submit-then-poll. Wrap it. Do not rebuild it.** It accepts `wait=False` to return the `activity_id` for agent-driven polling.

Located and vendored: **`github.com/FortyGuard-Tech/temperature-api-quickstart`** @ `f6de12d`
(MIT). Four files, unmodified, in `vendor/fortyguard/` — see `vendor/NOTICE.md`. Its bundled
sample responses are offline fixtures in `data/fixtures/vendor_samples/`, which is how
`docs/api-notes.md` got filled in before a credit was spent.

Also from the client, and not obvious: **`GET /v1/status/{id}` 404s for a short window right
after submit** — eventual consistency, not failure. A naive poller treats that 404 as an
error and discards a task that was fine.

## Scope discipline

| Tier | What |
|---|---|
| Load-bearing | `heatmap`, `env_params`, status polling |
| One addition | `satellite` — answers *why* a site is hot (land cover) |
| Stretch only | `heat_intelligence` PDF as a compliance artefact |
| Explicitly out | `streetview` — pretty, changes no decision |

A judge is literally giving a talk called *"The Builder's Trap: escaping the hype."* Innovation is 15%; Impact is 40%. Do not add surface.

## Architecture rule — non-negotiable

```
app.py     Streamlit surface
  ↓
agent.py   LLM: parses intent, narrates. NEVER picks the layer.
  ↓
router.py  ** CORE IP ** deterministic. question → layer → params + rationale + refusal
  ↓
tools.py   typed wrappers + cache keyed (endpoint, aoi_hash, date, time, filter_type, granularity)
  ↓
vendor quickstart client (auth + poll)

bands.py   leaf. heat index → NWS band + OSHA action, from config/thresholds.yaml.
           Imported by router.py and metrics.py; imports nothing of ours. Total
           functions — band_for/action_for never return None. (Added T2.)
```

The LLM does not choose the analysis layer. `router.py` does, deterministically. Reasons: **auditable** (safety tool), **reproducible** (demo takes must match), **testable with zero credits and no network**. Say this out loud in the video — constraining the LLM to what it is good at reads as maturity to a Google/NVIDIA panel.

## Conventions

- Secrets in `.env` only (`FORTYGUARD_API_KEY`). Never in code, never committed, never in client-side output, never visible in a demo video frame. **Keys in repos are an explicit disqualifier.**
- Cache every API result to `data/fixtures/` — tests run offline, and credits are never spent twice.
- Poll with backoff 3s → 6s → 12s.
- Append every agent decision to `data/decisions.jsonl` — site, date, question, layer, rationale, result, action. This is the compliance audit trail and the evidence the system works.
- Validate on a tiny polygon and a single timestamp before batching.

## Submission requirements

- Live demo link (working, not a prototype)
- Judge-accessible repo + README explaining how to run it
- **Add `Hackathon-FG (hackathon@fortyguard.com)` as a GitHub collaborator**
- ~3-minute demo video
- **Written summary, max 500 words**, structured exactly: problem → user → FortyGuard endpoints used → measured result
- Disclose AI tool usage

## Open questions to resolve by probing, not assuming

1. Is the key on Premium? Quickstart notebook `00_setup` prints plan + credits.
2. How does each constraint fail — status code, error shape, loud or silent?
3. Does an inversion day exist? **Highest risk in the project.**
4. Does `env_params` return heat index directly?
