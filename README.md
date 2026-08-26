# 🌡️ HeatGuard

**Per-site outdoor-worker heat safety for Phoenix job sites, built on the FortyGuard
Temperature API®.**

*FortyGuard Hackathon'26 · Track 4 (Government & Environment) × Track 6 (Agentic)*

### ▶ **[Live demo](https://heat-fortyguard.streamlit.app/)**

*Runs entirely from committed fixtures — no API key, nothing to break when the FortyGuard key expires on 21 September.*

---

> A safety manager with twelve Phoenix sites decides each morning where crews can work.
> Today that decision comes from a single city-wide forecast high — a *daytime maximum*,
> measured at Sky Harbor. OSHA records outdoor-worker heat-stroke deaths at a daily
> maximum heat index of only **86 °F**, inside the "Caution" band.
>
> **Peak temperature is a poor predictor of harm. Duration above a threshold is the
> signal.**

## The measured result

Twelve Phoenix sites, 2025-07-15, 107 workers, at OSHA's high-risk band:

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

A pure safety pitch competes with a free National Weather Service forecast and loses.
Two arguments survive contact with a buyer, and both use numbers already measured above:

- **Over-warning is the expensive error, and nobody counts it.** 643 phantom worker-hours
  is roughly **$35,000** at a $55/h loaded rate — one day, one roster. The app exposes
  that rate as a slider rather than baking it in, because it is an assumption, not a
  finding, and a buyer who disagrees should be able to move it.
- **`data/decisions.jsonl` is the other product.** Every decision is logged: question,
  layer chosen, why, threshold, result, action, timestamp. In an OSHA citation or a
  workers'-compensation dispute, what protects a supervisor is evidence of a consistent,
  documented process. A screenshot of a weather app is not that.

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
pytest                    # 336 tests, offline, zero credits, no API key
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
| `docs/submission-summary.md` | the 500-word summary |
| `data/fixtures/` | every API response, committed — the demo's data source |
| `data/decisions.jsonl` | the audit trail: every question, layer, rationale, action |

## AI disclosure

Built with **Claude Code (Claude Opus 5)** — code, tests, documentation, and API probing.
Disclosed per the hackathon rules; the pitch video is my own work.

Every factual claim here was measured against the live API and is reproducible from the
committed fixtures without a key.

## Limitations, stated plainly

Naming these is not modesty. A judge finds them in the first minute, and being the one
who says them first is worth more than hoping nobody looks.

- **No customer discovery has happened.** Zero interviews. The crew sizes, shift times
  and site roster are *plausible constructions*, not observed operations at a real
  contractor. The mechanism is measured; the demand is not. The next step is five
  conversations with Phoenix safety supervisors, before another line of code.
- Heat index, **not WBGT** — the metric OSHA actually regulates against. The API returns
  `wet_bulb_temperature_celsius`, so a WBGT *estimate* is reachable. That is the top of
  the roadmap, not a footnote.
- No modelling of crew acclimatisation or task intensity, both of which move OSHA's
  thresholds materially.
- Decision support only. Does not replace an employer's heat-illness prevention program.
