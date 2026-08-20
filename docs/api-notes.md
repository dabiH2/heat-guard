# API notes — verified behaviour

Two confidence levels, never mixed:

- **[VENDOR]** — read from the official quickstart client source and its bundled sample
  responses (`vendor/fortyguard/client.py`, `data/fixtures/vendor_samples/`). Costs no
  credits and needs no key. This is what the vendor's own code does and what their own
  captured responses contain. Strong, but it is not our key hitting the live API.
- **[LIVE]** — observed from an actual call with our key. Blank until T3 runs.
- **[TRANSCRIPT]** — stated on camera by a FortyGuard engineer in a recorded webinar
  (added 2026-08-20). Authoritative on *intent and plan limits*, unreliable on *exact
  numbers* — the source is Whisper output and several figures are audibly hedged. Where
  [TRANSCRIPT] and [VENDOR] disagree, [VENDOR] wins on code behaviour and [TRANSCRIPT]
  wins on commercial/plan facts the code cannot know.

Quickstart: `FortyGuard-Tech/temperature-api-quickstart` @ `f6de12d`. See `vendor/NOTICE.md`.
Transcripts: `../../02-temperature-api.txt` (Fawad Shah, Software Engineering Lead).

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

---

## What the engineer said on camera — **[TRANSCRIPT]**

Fawad Shah, `02-temperature-api`, 2026-08-18. Independent confirmation of the vendor
reading above, plus facts the client source cannot contain.

### `analytic_type` — confirmed verbally, and it is the "analysis layer"

`[00:24:30]`–`[00:25:16]`, verbatim:

> *"Then we have also the analytic type. So this is like basically the T same, this is just
> the simple snapshot. And then we have these other analysis thing like time of measure,
> exceedance persistence. So **exceedance** is something like for how many hours a certain
> value was above the threshold. For example, the temperatures you're getting is 25 to 40
> degrees. And you want to know for how many hours it was above 35 degrees Celsius. So it
> gets you that. And for **persistence**, it's quite similar but it gives you a continuous
> long run. Like for example, continuously it stayed above 35 for six hours, seven hours."*

("T same" is Whisper for `tcm`.) The [VENDOR] table is confirmed exactly. Note his example
threshold — *"35 degrees **Celsius**"* — independently corroborates finding (2) above.

Also flagged earlier in the same session, `[00:17:34]`, listing what heatmap returns:
*"It is basically **exceedance, persistence, time of measure**."*

### Plan, credits, limits — facts not derivable from the client

| Fact | Verbatim | TS |
|---|---|---|
| **On Premium, doubled** | *"this is the **most premium API key** that we are heading to you guys […] And actually **the limit is double than what we are normally giving**."* | `[00:14:24]` |
| **AOI limit 15 mi²** | *"on this plan, I think we have the premium one for you. So **the limit is about 15 miles square**."* | `[00:23:53]` |
| **2,000,000 credits/key** | *"you have about 2 million credits per API key."* | `[00:16:16]` |
| **Real cost anchor** | *"I have used about **187420** […] for tile segmentation, I use **72,000**"* — the entire demo build | `[00:22:50]` |
| **Failed tasks are free** | *"if a task fails, **it does not cost you any credit**. So just try to experiment freely."* | `[00:16:06]` |
| **Rate limit** | *"hourly, we have put a limit to it, not the daily one […] not more than **I think 100 requests per minute or something**. But as such, there's no other limits."* | `[00:56:17]` |
| **Max 30 days per call** | *"we are giving you the opportunity to get as much as **30 days worth of data** return to use for your use case."* | `[00:19:49]` |
| **Celsius everywhere** | *"everything is in Celsius, **including the thresholds you pass**."* | `[00:13:45]` |
| **Poll every 3–5 s** | *"every five seconds or three seconds, I would assume you can just start polling it."* | `[00:17:05]` |
| **Credits will be topped up** | *"if you use your credits for the API, unlikely, but if you do so, we will be happy to accommodate that."* | `[00:47:06]` |

### Observed latency — **[TRANSCRIPT]**, live demo

- `heatmap`, single hour, `granularity=100`, small polygon: *"the response is continuously
  being checked after two, three seconds. So we, and then it completed."* `[00:26:12]` —
  i.e. **a few seconds**, one or two poll cycles.
- `env_params`, `filter_type=2`: *"this one ran pretty quickly"* `[00:28:13]`.
- `heat_intelligence`: *"it takes about **two to three minutes**"* `[00:32:05]`. Output is a
  **25-page PDF** `[00:33:22]` with **five sections** `[00:18:19]`: geographic, environmental
  factors, urban factors, events (extreme weather/heat history), anthropogenic factors.
- ⚠ **Ambiguous line, do not record as latency:** `[00:27:21]` *"maximum it took about, was
  about six hours and minimum is two."* Spoken immediately after an `exceedance` run over a
  ~6-day window with `threshold=35, direction=above`. Almost certainly the **exceedance
  result** (max 6 h above threshold, min 2 h), *not* wall-clock latency. Treated as
  unresolved; do not cite it either way.

### Terminology — **[TRANSCRIPT]**

**A parcel is smaller than a tile.** `[00:33:49]`: *"Parcel is basically a more smaller area
than a tile. Like tile could be 180, 60 meter, it could be even less than that."* The
worked case study operates on **parcels clipped from tiles** — six parcels totalling
**17.38 acres**, `granularity=80`, window **28 Jul – 3 Aug** `[00:34:24]`–`[00:34:52]`.
This is the unit HeatGuard's "job site" should map to.

### Non-US fails silently *and bills you* — **[TRANSCRIPT]**

`[00:13:23]`: *"if you are going to set up the location to Dubai or Berlin or whatever, you
are, apart from the US, I don't think it's going to work. And **it's just going to spend
your credit**. So I would advise not to do that."*

Contradicts the assumption that failures are free: a *task* failure costs nothing, but an
out-of-coverage AOI apparently completes and charges. **`router.py` must reject non-US
before `tools.py` is ever reached.** Confirm the exact behaviour in T4.

---

## Divergences — resolve in T4

| Source A says | Source B says | Action |
|---|---|---|
| CLAUDE.md: **AOI ≤ ~130 km² (50 mi²)** | **[TRANSCRIPT]** `[00:23:53]`: *"about 15 miles square"* | 🔴 **3.4× apart.** Engineer is describing the premium plan live; handbook figure is unsourced. **Assume 15 mi² until probed.** Highest-impact open number — it sizes every demo AOI. |
| CLAUDE.md: `filter_type` **5 = single month** | **[VENDOR]** docstring lists only 1–4 | **[TRANSCRIPT]** `[00:19:39]` confirms five: *"single hour […] range of hours […] a single day […] a range of days and then we have a single month."* So 5 exists per the engineer but is **undocumented in the client**. Probe. |
| CLAUDE.md endpoint table has no `analytic_type` | four analytic types on `/v1/heatmap` | Corrected in CLAUDE.md; **[TRANSCRIPT]** independently confirms |
| CLAUDE.md: `env_params` returns "heat index" | returns `heat_index_celsius` | Corrected; **[TRANSCRIPT]** `[00:27:45]` confirms *"heat index Celsius"* |
| CLAUDE.md: **7 endpoints** in the table | **[TRANSCRIPT]** `[00:10:23]`: *"majorly **six** end points"* | Not a real conflict — Fawad counts 5 analysis + 1 status and omits `fetch-api-key-usage`, which he then uses in the notebook. Keep 7. |
| CLAUDE.md: poll **3→6→12 backoff** | **[VENDOR]** client polls constant 3.0 s; **[TRANSCRIPT]** advises *"every five seconds or three seconds"* | Keep our backoff — it is strictly gentler than both. No conflict. |
| CLAUDE.md: **failed tasks cost nothing** | **[TRANSCRIPT]** confirms — *but* non-US AOIs *"spend your credit"* | Both true. Distinguish *task failure* (free) from *out-of-coverage success* (billed). |
| granularity 60/80/100 m | client default 100, docstring 60/80/100; **[TRANSCRIPT]** `[00:12:56]` confirms | consistent |
| "2 m above ground, 20 m spatial resolution" | not contradicted by any source | keep |

---

## Plan & credits — **[LIVE]**, blocked on T3

- Plan: **[TRANSCRIPT] Premium, at double the normal limits** `[00:14:24]`. Confirm the string the API returns.
- Credits remaining: **[TRANSCRIPT] 2,000,000 issued per key** `[00:16:16]`. Confirm balance.
- Premium endpoints available (`satellite`, `streetview`, `heat_intelligence`): **[TRANSCRIPT] all three — demoed live on a hackathon key in-session** (`satellite` `[00:29:25]`, `streetview` `[00:30:17]`, `heat_intelligence` `[00:31:54]`). Nothing is gated. Confirm.

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
| Non-US location | **[TRANSCRIPT]** *"it's just going to spend your credit"* `[00:13:39]` — completes and bills | ? | **likely SILENT** | `router.py` US bounds check, pre-`tools.py` |
| Date before 2021-01-01 | | | | |
| Forecast beyond now +12h | | | | |
| AOI > **15 mi²** (not 130 km² — see divergences) | | | | |
| Window > 30 days | **[TRANSCRIPT]** 30-day cap stated `[00:19:49]` | ? | ? | `router.py` window guard |
| `granularity` not in {60,80,100} | | | | |
| `filter_type=5` | **[TRANSCRIPT]** engineer says it exists; **[VENDOR]** client omits it | ? | ? | |
| >100 requests/minute | **[TRANSCRIPT]** hourly cap, ~100 rpm `[00:56:17]` | ? | ? | backoff already well under |
| `exceedance` with no `threshold` | client-side `ValueError` | n/a | **loud** | vendor client |
| `threshold` passed in °F by mistake | **[VENDOR]** returns 0 h everywhere | 200 | **SILENT** | `tools.py` unit guard |

## filter_type, verified — **[LIVE]**, T4

Same site, same date, `filter_type=1` vs `filter_type=3`, and `tcm` vs `exceedance`:
