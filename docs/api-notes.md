# API notes — verified behaviour

Two confidence levels, never mixed:

- **[VENDOR]** — read from the official quickstart client source and its bundled sample
  responses (`vendor/fortyguard/client.py`, `data/fixtures/vendor_samples/`). Costs no
  credits and needs no key. This is what the vendor's own code does and what their own
  captured responses contain. Strong, but it is not our key hitting the live API.
- **[LIVE]** — observed from an actual call with our key. Blank until T3 runs.

Quickstart: `FortyGuard-Tech/temperature-api-quickstart` @ `f6de12d`. See `vendor/NOTICE.md`.

---

## THE THREE FINDINGS THAT CHANGE THE PROJECT

### 1. The API already computes duration. `analytic_type` was missing from our model.

**[VENDOR]** `POST /v1/heatmap` takes an `analytic_type`, and CLAUDE.md's endpoint table
never mentioned it. Four values:

| `analytic_type` | Returns | Units |
|---|---|---|
| `tcm` (default) | snapshot temperature per tile — the classic heatmap | °F |
| `time_of_measure` | UTC hour-of-day 0–23 at which each cell peaks | hour-of-day |
| **`exceedance`** | **count of hours each cell spends past `threshold`** | `hour` |
| **`persistence`** | **longest continuous run of such hours** | `hour` |

This is HeatGuard's entire thesis, already a first-class server-side product. Duration is
not something we derive client-side from an hourly profile — we can ask for it directly,
per tile, at 20 m resolution.

It also *sharpens* the thesis rather than undercutting it. The trap Fawad Shah described
gets worse, not better: `tcm` and `exceedance` are the **same endpoint, same filter_type,
same AOI** — one optional string apart. Ask "how long were they above the danger band",
get handed `tcm`, and you receive a beautifully-formatted map of peak temperature with no
error and no hint that the question went unanswered. The router now has to select
`analytic_type` as well as `filter_type`, and that is the highest-value decision it makes.

`persistence` is arguably the better safety metric of the two. Heat stroke is driven by
continuous uninterrupted exposure, not by a day's scattered total — six separate hours
above the band with breaks between them is a different physiological event from six
consecutive ones. **Report both.**

`exceedance` and `persistence` require `threshold` **and** `direction` (`"above"`/
`"below"`); the client raises `ValueError` if either is missing. Good — that one fails loudly.

### 2. `threshold` is in CELSIUS while tile readings are in FAHRENHEIT.

**[VENDOR]** From the client docstring, verbatim:

> `threshold` (**°C**, default 30 on the API side — note the contrast with the °F tile readings)

This is the single most dangerous fact found so far, and it is worth more to the demo than
the layer trap.

Pass `threshold=91` intending 91 °F. The API reads **91 °C = 195.8 °F**. Nothing on Earth
has ever been that hot. Every cell returns **exceedance = 0 hours**. The response is
well-formed, the status is `succeeded`, the credit is spent, and the tool reports:

> *No unsafe exposure at any of your twelve sites today.*

A plausible, confidently-formatted, unit-confused **all-clear** — the worst possible wrong
answer a heat-safety tool can produce, and no error is raised anywhere in the stack.

`tools.py` must therefore convert at the boundary and refuse ambiguity: HeatGuard's
config is °F throughout (OSHA and NWS are °F, the users are US supervisors), so the
conversion happens in exactly one place, is unit-suffixed in every signature
(`threshold_c`, `heat_index_f`), and is covered by tests. A bare `threshold` argument
should not exist anywhere in our code.

### 3. `env_params` returns heat index directly — in Celsius.

**[VENDOR]** Answers CLAUDE.md open question #4. Sample response, `locations[0].parameters`:

```
heat_index_celsius            [31.8, 32.4, 32.5, ...]   24 hourly values
apparent_temperature_celsius  [14.8, 14.4, 14.2, ...]
wet_bulb_temperature_celsius  [...]
relative_humidity_percent     [...]
precipitation_mm, cloud_cover_octas
air_quality:idx, air_quality_pm2p5:idx, air_quality_pm10:idx,
air_quality_no2:idx, air_quality_o3:idx, air_quality_so2:idx, aqi_us_co
methane_ppb, co2_ppm, elevation
solar_irradiance: {clear_sky: {ghi, dni, dhi}}
```

Yes, directly. **In Celsius** — the same trap as (2), one layer down. `config/thresholds.yaml`
is authored in °F against NWS/OSHA bands; conversion is `tools.py`'s job and nowhere else's.

`metadata` carries `timezone` (`"GMT-8"` in the sample), `timezone_offset_hours`,
`time_range {start, end, interval: "1h", count: 24}` and a `timestamps` array of 24
**local-time** ISO strings. Phoenix is MST year-round (GMT-7, no DST), so shift windows —
including the ones that wrap past midnight — map onto these timestamps without a
conversion step. That is a real convenience for the night-crew case.

**`wet_bulb_temperature_celsius` is available.** `config/thresholds.yaml` currently says
the API "exposes heat index, not WBGT". That needs softening: wet-bulb temperature is not
WBGT (outdoor WBGT = 0.7·Tnwb + 0.2·Tg + 0.1·Ta and needs a globe thermometer), but with
wet bulb + air temp + solar irradiance a WBGT *estimate* is reachable. Out of scope for
this build; worth one sentence in the pitch as the honest next step, because it is the
metric OSHA actually regulates against.

---

## Client behaviour worth knowing

**[VENDOR]** `vendor/fortyguard/client.py`:

- Auth: header `api-key: <key>` plus `Content-Type: application/json` on a `requests.Session`.
  `fetch_api_key_usage` **also** puts the key in the POST body.
- Base URL from `FORTYGUARD_BASE_URL`, default `https://api.fortyguard.com`. A dev host
  exists (`tos-enterprise-api.dev.app.fortyguard.com`) — do not point the demo at it.
- Submit returns `data.activity_id`. Every analysis method accepts `wait=False` to return
  the bare `activity_id` for agent-driven polling.
- **`GET /v1/status/{id}` 404s for a short window right after submit** — eventual
  consistency, not an error. The client raises `ActivityNotReadyError` and keeps polling.
  A naive poller treats that 404 as failure and throws away a task that was fine.
- Terminal statuses: success `{"succeeded", "completed"}`, failure `{"failed", "error"}`.
  Result at `data.result`.
- The client polls at a **constant** 3.0 s. CLAUDE.md specifies 3→6→12 backoff, so
  `tools.py` drives its own polling loop via `wait=False` rather than calling `wait_for`.
- `heat_intelligence` returns a **PDF** via a short-lived pre-signed `result.download_link`
  (older versions streamed the body; both paths handled).

### Response shapes

**[VENDOR]** `analytic_type` in `{exceedance, persistence}`:

```
map_data.type          "FeatureCollection"
map_data.features[]    {id, type, properties: {tile_id, value}, geometry: Polygon}
stats_data             {activity_id, analytic_type, units, n_cells, min, max, mean}
```

Sample: `units: "hour"`, `n_cells: 329`, `min: 25.51`, `max: 40.68`, `mean: 35.30` over a
7-day window (168 h). Note **values are fractional**, so exceedance is interpolated rather
than a whole-hour tally — and `n_cells: 329` over a small parcel confirms genuine per-tile
spatial variation rather than one number smeared over the AOI.

`tcm` returns different per-tile fields; do not write one parser for both.

---

## Divergences from CLAUDE.md — resolve in T4

| CLAUDE.md says | Vendor client says | Action |
|---|---|---|
| `filter_type` 1/2/3/4/**5 = single month** | docstring lists only 1–4; no 5 anywhere | **[LIVE]** probe `filter_type=5`. Loud error or silent wrong window? |
| endpoint table has no `analytic_type` | four analytic types on `/v1/heatmap` | Corrected in CLAUDE.md |
| `env_params` returns "heat index" | returns `heat_index_celsius` | Corrected; conversion in `tools.py` |
| granularity 60/80/100 m | client default 100, docstring says 60/80/100 | consistent |
| "Data measured 2 m above ground at 20 m spatial resolution" | not contradicted | keep |

---

## Plan & credits — **[LIVE]**, blocked on T3

- Plan:
- Credits remaining:
- Premium endpoints available (`satellite`, `streetview`, `heat_intelligence`):

## Observed async behaviour — **[LIVE]**

- Latency, submit → terminal, `env_params` single day:
- Latency, submit → terminal, `heatmap` `filter_type=3` at 100 m:
- Terminal status strings actually seen:
- How long the post-submit 404 window lasts in practice:

## Constraint failure modes — **[LIVE]**, T4

**Failed tasks cost nothing — probe freely.** The column that matters is the fourth: a
loud failure is a bug caught, a silent plausible one is a bug shipped.

| Constraint | How it fails | Status code | Loud or silent? | What the code catches |
|---|---|---|---|---|
| Non-US location | | | | |
| Date before 2021-01-01 | | | | |
| Forecast beyond now +12h | | | | |
| AOI > ~130 km² | | | | |
| `granularity` not in {60,80,100} | | | | |
| `filter_type=5` | | | | |
| `exceedance` with no `threshold` | client-side `ValueError` | n/a | **loud** | vendor client |
| `threshold` passed in °F by mistake | **[VENDOR]** returns 0 h everywhere | 200 | **SILENT** | `tools.py` unit guard |

## filter_type, verified — **[LIVE]**, T4

Same site, same date, `filter_type=1` vs `filter_type=3`, and `tcm` vs `exceedance`:
