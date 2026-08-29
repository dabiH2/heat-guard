# 🌡️ HeatGuard

**Per-site outdoor-worker heat safety for Phoenix job sites, built on the FortyGuard
Temperature API®.**

*FortyGuard Hackathon'26 · Track 4 (Government & Environment) × Track 6 (Agentic)*

### ▶ **[Live demo](https://heat-fortyguard.streamlit.app/)**

*Runs entirely from committed fixtures — no API key, nothing to break when the FortyGuard key expires on 21 September.*

> **Submission prerequisites, stated here because they cannot be verified from outside.**
> `Hackathon-FG` **was added as a collaborator on this repository and the invitation was
> accepted** (write access, 24 Aug 2026) — the prerequisite FortyGuard called out at
> `02-temperature-api` `[00:50:22]`: *"if it's not added as a collaborator […] this
> submission would not be counted."* The repository is public, the live demo opens
> logged-out, and no key is committed or required to run anything here.

---

> A safety manager with twelve Phoenix sites decides each morning where crews can work.
> Today that decision comes from a single city-wide forecast high — a *daytime maximum*,
> measured at Sky Harbor. OSHA records outdoor-worker heat-stroke deaths at a daily
> maximum heat index of only **86 °F**, inside the "Caution" band [[EV:HARM-04]] —
> and OSHA's own instruction is *"do not rely solely on the Heat Index reported by
> weather forecasts for your safety at work, as it may underestimate your actual
> risk"* [[EV:CTR-06]]. Station readings *"may not reflect the conditions at the
> specific worksite"*, and *"the potential error increases with distance from the
> weather station"* [[EV:CTR-07]].
>
> **Every occupational heat limit in force — NIOSH's RAL and REL [[EV:NIOSH-01]], ACGIH's
> TLV, ISO 7933 [[EV:ISO-01]] — is defined as *time at a condition*, and NIOSH removed its
> peak-temperature ceiling limit in 2016 [[EV:NIOSH-02]]. A daily maximum cannot be
> compared against any of them. Hours above a threshold can.**

*Every external figure below carries an `EV` marker resolving to
[`data/evidence/claims.json`](data/evidence/claims.json). Figures without one are measured
by this project from its own committed fixtures.*

## The measured result

2025-07-15, at OSHA's high-risk band. The roster is **twelve sites, 115 workers** — but
**PHX-DVT returned zero tiles that day**, which is one of the silent failure modes
documented below, so every figure here is over the **11 sites with data, 107 workers**.
The twelfth is counted as a coverage gap, not as a site that was safe.

| | |
|---|---|
| Peak spread across 11 sites | **1.96 °F** (1.09 °C) — indistinguishable |
| Duration spread | **2.62 h — 37% relative.** Duration discriminates **20× better** |
| City-wide figure applied uniformly | **701 unsafe worker-hours** |
| Scoped to the shifts crews actually work | **58 worker-hours** |
| **Phantom exposure removed** | **643 worker-hours — 92%** |

The dangerous window ran roughly **13:00–20:00** — outside nearly every shift on the
roster. A city-wide "stop work" call would have been 92% wrong, and **over-warning is the
expensive error**.

Eight of eleven sites tie at 7.0 h above threshold and are identical on any heat map.
Scoped to shifts, only four carry exposure at all — and the worst is not the hottest site
but the one with **22 people standing in that hour instead of 18**. *Heat maps rank tiles.
Crews are what get hurt.*

Independently reproduces FortyGuard's own client case study: 0.7 °C peak spread across six
parcels against 19 h of exceedance.

### Why anyone would pay for this

A pure safety pitch competes with a free National Weather Service forecast and loses. Four
arguments survive contact with a buyer.

- **The free tool has been measured against the worksite, and it failed.** The OSHA-NIOSH
  Heat Safety Tool, fed by NWS data, identified **0% of high or extreme risk conditions**
  when checked against on-site WBGT; the authors' verdict was *"not protective of
  workers… not recommended"* [[EV:CTR-01]]. That is the only published evaluation of the
  incumbent free tool.

- **Over-warning is the expensive error, and nobody counts it.** OSHA makes that argument
  itself, in writing, against its own cost estimate: assuming full-shift exceedance *"may
  overstate the number of breaks employers need to provide since there may be some days
  where the heat triggers are met or exceeded but for shorter periods of time"*
  [[EV:REG-04]]. Priced at the BLS construction loaded rate of **$51.23/h**
  [[EV:COST-01]], the 643 phantom worker-hours are worth, for one day on one roster:

  | Bound | Basis | Value |
  |---|---|---|
  | Lower | 643 h × 12.5% mandated rest [[EV:COST-02]] × $51.23 [[EV:COST-01]] | **≈$4,118** |
  | Upper | 643 h fully idle × $51.23 [[EV:COST-01]] | **≈$32,941** |

  The truth is between them, and which end it sits nearer depends on what the employer
  actually does. The lower bound is what is owed *even while the crew keeps working* — a
  15-minute paid break every two hours at the high heat trigger, which is **proposed, not
  in force** [[EV:REG-05]] [[EV:REG-02]]. The upper bound assumes the crew stands idle for
  every one of those hours. **No published figure exists for the cost of precautionary work
  stoppage**; that negative result is recorded in
  [`docs/impact-evidence.md` §6](docs/impact-evidence.md#6-what-i-could-not-source), item 8.
  The app exposes the rate as a slider rather than baking it in, because a buyer who
  disagrees should be able to move it.

  *The pitch video was recorded before this rate was sourced, so it shows $55/h and
  $35,363.*

- **HeatGuard is an API, not a sensor.** No hardware, no calibration, no per-site
  instrument. The Construction Industry Safety Coalition told OSHA that WBGT equipment is
  *"not only expensive, but also complex… requires regular calibration"* and asked for
  simpler methods instead
  ([`docs/practice-and-efficacy-evidence.md`](docs/practice-and-efficacy-evidence.md#6-counter-evidence-you-must-be-ready-for)).
  That is the buyer's own objection to the measurement they are being asked to take, and
  the form factor already answers it.

- **The decision log is the other product.** Every question the running app answers is
  appended to `data/decisions.jsonl` — question, layer chosen, why, both thresholds,
  result, action, timestamp — including the ones it *refuses*, and why it refused. In an
  OSHA citation or a workers'-compensation dispute, what protects a supervisor is
  evidence of a consistent, documented process. A screenshot of a weather app is not
  that.

  The runtime log is gitignored, as an append-only operational log should be. A **real
  generated sample** is committed as
  [`data/decisions.sample.jsonl`](data/decisions.sample.jsonl) — nine records produced by
  running the actual agent against the committed fixtures
  (`python scripts/make_decisions_sample.py`), covering a snapshot, a duration question
  routed to `exceedance`, a comparison across three sites, an escalation, and three
  refusals. Nothing in it is hand-written.

## Impact — who is exposed, and what today's alert misses

Nothing in this section is my measurement. Every figure is external and cited.

**The harm is counted, and the count is known to be low.** 48 US workers died of
exposure to environmental heat in 2024 [[EV:HARM-01]], 40 of them outdoors [[EV:HARM-02]].
OSHA's own risk assessment applies an undercount factor of **14** to heat fatalities
[[EV:HARM-03]].

**Reach, counted from the bottom up.** 154,320 people work in construction and extraction,
landscaping, refuse collection and line installation in the Phoenix-Mesa-Chandler MSA
[[EV:REACH-01]] — **6.50% of everyone employed in the metro** [[EV:REACH-03]]. The same
five occupations across sixteen US Sun Belt metros total 1,364,770 [[EV:REACH-02]]. Every
cell and every addition is shown, per occupation code, in
[`docs/impact-evidence.md` §4](docs/impact-evidence.md#4-bottom-up-reach). Two things this
count is not: it counts **jobs, not customers** — the buyer is an employer's safety
function, and I have not counted those — and BLS OEWS **excludes the self-employed
entirely**, which is material in construction and landscaping, so the figure is a floor.

**What today's alert misses.** 64% of Maricopa County's 430 heat-related deaths in 2025
fell on days NWS HeatRisk was *not* Major or Extreme [[EV:POP-01]] [[EV:POP-02]]. **These
are general-population deaths, not worker deaths: Maricopa County does not record
occupation.** The claim is about the alert, not about the decedents' jobs — in the US
county with the most heat deaths, the categorical alert that a supervisor reads each
morning was outside its top two categories on the days most deaths occurred. A supervisor
reading that alert inherits the same blind spot.

**What supervisors use instead.** 87% of US contractors assess heat risk from weather
forecasts [[EV:PRAC-01]]; 42% take any direct jobsite measurement [[EV:PRAC-02]]; 13% use
WBGT [[EV:PRAC-03]].

## The problem it solves

`POST /v1/heatmap` takes an `analytic_type`, and the choice is invisible:

| value | returns |
|---|---|
| `tcm` *(default)* | snapshot temperature per tile — **the peak** |
| `exceedance` | **hours each cell spends past a threshold** |
| `persistence` | longest **continuous** run of those hours |

`tcm` and `exceedance` are the **same endpoint, the same `filter_type`, the same area —
one optional string apart.** Ask *"how long were they above the danger band"*, let the
default stand, and you get a beautifully-formatted map of peak temperature. Same shape of
output, opposite operational decision, **no error raised anywhere**.

HeatGuard chooses that string **deterministically, before any call is made**, states why,
and refuses when the data cannot answer.

### The unit trap, executed live

Two calls. Same endpoint, area, date, `filter_type`, `analytic_type`, `direction`. The
only difference is whether the threshold was converted from Fahrenheit:

```
threshold = 35.00   (95 °F, converted)              →  17.0 hours above threshold
threshold = 95      (95 °F raw, read as 95 °C)      →   0.0 hours
```

Both returned `Completed`. Both cost 4,220 credits. Nothing raised.
**17 hours of dangerous exposure, reported as zero — a confidently formatted all-clear.**

Reproducible from `data/fixtures/t4/t4_probes.json`, pinned by
`tests/test_api_contract.py`.

## Architecture — the LLM never picks the layer

```
app.py     Streamlit surface
  ↓
agent.py   LLM: parses intent, narrates. NEVER picks the layer.
  ↓
router.py  ** CORE IP ** deterministic. question → layer → params + rationale + refusal
  ↓
tools.py   typed wrappers, the only unit conversion, the fixture cache
  ↓
vendor/fortyguard/   the official quickstart client, pinned at f6de12d (MIT)

bands.py   leaf. heat index → NWS band + OSHA action. Total functions, never None.
```

`router.py` contains **no model call**. That makes layer selection **auditable** (this is
a safety tool), **reproducible** (demo takes match exactly), and **testable at zero cost**.

With no `ANTHROPIC_API_KEY` the templated narration is used and the answer is identical
apart from wording — [a test][t] runs the same question both ways and asserts every
decisive field matches. *A safety tool whose recommendation depends on whether a language
model was reachable is not a safety tool.*

[t]: tests/test_agent.py

## Built to be relied on

*Deployable, client-grade — the standard applied to what was actually built, which is
deliberately narrow.*

**It works on a cold visit.** The deployed app is **offline by default** and serves the
committed fixture cache. It needs no API key, so there is nothing to leak and nothing
that breaks when the FortyGuard key expires. A judge clicking around **cannot spend a
credit** — going live requires setting `HEATGUARD_ONLINE=1`, which only ever happens on a
developer machine. Every path a visitor can click was verified offline: 12 sites × 6
question shapes × 2 thresholds — 36 answered, 12 refused by design, **0 cache misses**.

**The build is sound.** Over 400 tests, all offline, no network, no credits, no key. Layer
selection is deterministic and its post-conditions *crash* rather than emit a layer
already known to be wrong. A [live-uptime check](.github/workflows/keep-alive.yml) runs
every 3 hours and fails loudly rather than pinging blindly.

**The data is handled well.** These are the documented ways to misuse this API and get a
confident wrong answer. Each is handled in code, not just noted:

| Trap | What goes wrong | What we do |
|---|---|---|
| **Analysis layers use a different schema** | `tcm` returns per-tile temperature fields; `exceedance`/`persistence` return `properties.value`. Code reading `properties.temperature` finds nothing. | Two separate readers. `tile_hours()` raises `UnitError` unless `stats_data.units == "hour"`. |
| **`exceedance` counts hours, not degree-hours** | `6.0` means six hours past the threshold — not accumulated °C·h. | Labelled hours everywhere. Never called an intensity or a severity. |
| **`env_params` heat index is a humidity artifact** | One temperature anchor across 24 h with only humidity varying, so it peaks *overnight*. It is a humidity-sensitivity curve, not a diurnal forecast. | **No duration metric is derived from it.** Duration comes from `exceedance`. `env_params` supplies humidity only, for the heat-index → air-temperature conversion. Verified independently by reproducing their series from the single input temperature. |
| **`env_params` is coarser than a parcel** | Nearby points return identical arrays; it is a re-expression of the heatmap, not an independent measurement. | Never used to discriminate between sites. |
| **`threshold` is °C while readings are °F** | Sending 95 meaning °F returns **0.0 h where the truth is 17.0** — `Completed`, billed, silent. | One conversion point, unit-suffixed signatures, and a guard that refuses any threshold above 60 °C. |

Six further silent-and-billed failure modes, all measured live, are in
[`docs/api-notes.md`](docs/api-notes.md) — every one refused before the call is made.

## What we got wrong

`docs/site_selection.md` committed to reporting failed predictions rather than dropping
them. **Our per-site predictions scored 2 of 11 — worse than chance.**

The archetype hypothesis (street canyon clips its peak and holds heat; desert spikes and
sheds) does not describe what the API returns. What the data separates is **urban core
from periphery**, not surface type: the three sites that differ are the three outermost,
while downtown canyon, airfield asphalt and irrigated park inside the core return
identical numbers. At 20 m native resolution over a 400 m area, the regional heat-island
gradient dominates street-level differences.

The project thesis survives that. The site-selection hypothesis does not.

## Six ways the API fails silently — and bills you

Each returns `Completed` with a plausible-looking result and costs 4,220 credits. All are
refused before the call is made. Full table in [`docs/api-notes.md`](docs/api-notes.md).

| Request | What comes back |
|---|---|
| An area outside the US | zero tiles |
| A date before ~Q4 2021 | zero tiles — *the documented start date is out by a year* |
| Some sites on some dates | zero tiles — coverage is patchy per location too |
| Tomorrow's date | one flat value for the whole day |
| `exceedance` with no threshold | 24.0 hours, against a threshold nobody chose |
| A Fahrenheit threshold | 0.0 hours where the truth is 17.0 |

Also corrected against measurement: `filter_type=5` does not exist (HTTP 422); the AOI cap
is not enforced at 447 km²; cost is **flat per call**, not per tile; and **the API is
Celsius while the vendor's own client docstring says Fahrenheit**.

## Running it

```bash
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
pytest                    # offline, zero credits, no API key
streamlit run app.py      # offline by default, serves the committed fixtures
```

**Offline by default — you opt *in* to spending.** A deployed app that can reach the API
can be made to spend 4,220 credits per click. Live mode needs `HEATGUARD_ONLINE=1` and a
key in `.env`. See [`DEPLOY.md`](DEPLOY.md).

## Repository map

| Path | |
|---|---|
| `src/heatguard/router.py` | **the core IP** — the decision table |
| `docs/routing_spec.md` | that table, in prose, with the refusals |
| `docs/api-notes.md` | every measured API behaviour, `[VENDOR]` / `[LIVE]` / `[TRANSCRIPT]` |
| `docs/site_selection.md` | the twelve sites, the predictions, and how they did |
| `docs/impact-evidence.md` | harm, reach and cost — every figure with a source URL and a data year, and a list of what could not be sourced |
| `docs/practice-and-efficacy-evidence.md` | how supervisors decide today, and the evidence that no tool of this class has been shown to work |
| `data/evidence/claims.json` | the claim registry every `EV` marker resolves to |
| `docs/submission-summary.md` | the 500-word summary |
| `data/fixtures/` | every API response, committed — the demo's data source |
| `data/decisions.sample.jsonl` | a real generated sample of the audit trail — question, layer, rationale, action, refusals |
| `scripts/make_decisions_sample.py` | regenerates that sample offline, from the committed fixtures |

## AI disclosure

Built with **Claude Code (Claude Opus 5)** — code, tests, documentation, and API probing.
Disclosed per the hackathon rules; the pitch video is my own work.

Every claim here about the API was measured against it and is reproducible from the
committed fixtures without a key. Every claim about the world outside it carries an `EV`
marker, a source URL and the year the data refers to.

## Limitations, stated plainly

Naming these is not modesty. A judge finds them in the first minute, and being the one
who says them first is worth more than hoping nobody looks.

- **No tool of this class has ever been shown to reduce heat illness.** Not this one, and
  not anything it competes with. A scoping review of wearable heat monitors found **0 of 19
  studies measured a health outcome** — no RCTs, no controlled trials [[EV:EFF-01]]. The
  only US RCT of a worker heat decision-support app was **null** on physiological strain
  [[EV:EFF-02]]. The one strong positive result in the literature, a 2024 Italian study,
  came from a legally mandated work ban rather than from the forecasting platform that
  triggered it. OSHA is in the same position and says so in the rule text: it is
  **assuming** *"an effectiveness of 95 percent for fatalities and 65 percent of HRIs"*
  [[EV:EFF-03]]. The measurement gap is documented. Whether closing it changes outcomes is
  unmeasured.
- **Duration has not been shown to out-predict peak for worker harm. Nobody has tested
  it.** No occupational study uses hours-above-threshold as an exposure variable
  ([`docs/practice-and-efficacy-evidence.md` §5](docs/practice-and-efficacy-evidence.md#5-the-thesis-sentence-that-has-to-change)).
  The argument at the top of this file is about standards architecture — the limits are
  written as time at a condition — not about predictive power. That is a gap, not a
  finding.
- **Counter-evidence, named.** A contractor testified to OSHA that the free NWS forecast is
  *"all I need to change work hours, days off, job assignments, production, and
  timelines"*, and contractor use of mobile heat safety apps **fell from 35% to 22%**
  between the 2023 and 2025 survey waves [[EV:PRAC-04]] — the trend is away from tooling,
  not toward it. Both cut against this product, and neither is answered by building more
  of it.
- **No customer discovery has happened. Zero interviews.** The crew sizes, shift times and
  site roster are *plausible constructions*, not observed operations at a real contractor.
  What was read instead is the public record: named employers' sworn testimony from OSHA
  docket OSHA-2021-0009 — 12 hearing days, 16 Jun – 2 Jul 2025 — plus two contractor
  surveys, quoted in
  [`docs/practice-and-efficacy-evidence.md`](docs/practice-and-efficacy-evidence.md). That
  is a record of what employers say they do. It is not a record of anyone agreeing to buy
  this. The mechanism is measured; the demand is not. The next step is unchanged: five
  conversations with Phoenix safety supervisors, before another line of code.
- Heat index, **not WBGT** — the metric OSHA actually regulates against. The API returns
  `wet_bulb_temperature_celsius`, so a WBGT *estimate* is reachable. That is the top of
  the roadmap, not a footnote.
- **NOT BUILT — trigger on deviation from local normal, not an absolute band.** The router
  keys off absolute OSHA bands. Kwest Group's EHS manager testified that the operative
  signal is *"a significant change or deviation from what that normal heat index is in that
  location"* [[EV:PRAC-05]], and the Construction Industry Safety Coalition then formally
  proposed that same basis to OSHA, citing the urban heat island by name. A per-site
  historical API is the only thing that can compute a local normal per site. It is roadmap,
  not code.
- No modelling of crew acclimatisation or task intensity, both of which move OSHA's
  thresholds materially.
- Decision support only. Does not replace an employer's heat-illness prevention program.
