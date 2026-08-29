# Routing spec — the decision table

The implementable form of the router. Source of truth is
[`src/heatguard/router.py`](../src/heatguard/router.py) — `DECISION_TABLE` is a literal
dict, not a chain of `if` statements, so it can be read, diffed and tested directly.

**No LLM call exists in this module.** The agent parses intent and narrates; the router
decides. That makes layer selection auditable (this is a safety tool), reproducible (demo
takes must match exactly), and testable with zero credits and no network — **336 offline
tests, of which 123 cover this file** (`tests/test_router_table.py` 105 +
`tests/test_router.py` 18).

---

## What the two parameters actually do

This is the distinction the whole project turns on:

| parameter | selects | failure if wrong |
|---|---|---|
| `filter_type` | the **time window** — how much data | too little data to see the pattern |
| `analytic_type` | the **analysis layer** — what you ask of that data | **the wrong question answered, silently** |

`tcm` and `exceedance` are the *same endpoint*, the *same* `filter_type`, the *same* AOI —
one optional string apart. Ask "how long were they above the threshold", let
`analytic_type` default to `tcm`, and you get a well-formed map of aggregate temperature.
Same shape of output. Opposite operational decision. No error raised anywhere.

FortyGuard's own engineering lead demonstrates the inversion on their own client case
study (`02-temperature-api` `[00:36:14]`–`[00:37:23]`), six parcels over 28 Jul–3 Aug:

- Ranked by **peak** — hottest-to-coolest spread of **0.7 °C**. Operationally: "all six
  sites are the same."
- Ranked by **duration** — *"for more than 19 hours it stayed above, and then for five
  hours straight it was above the threshold."*

---

## The table

| # | Operator question | Type | Endpoint | `filter_type` | `analytic_type` | Wrong answer if answered as a snapshot |
|---|---|---|---|---|---|---|
| 1 | "Is it safe at site 3 right now?" | `SNAPSHOT` | `/v1/heatmap` | 1 · single hour | `tcm` | **None** — a snapshot is correct here. The only row where that is true. |
| 2 | "When should we start and stop today?" | `INTRADAY` | `/v1/heatmap` | 3 · entire day | `time_of_measure` | One number and no schedule. Cannot say *which hour* to avoid. |
| 3 | "Will we cross the threshold soon?" | `FORECAST` | `/v1/heatmap` | 2 · hour range | `tcm` | A historical average hides what today is doing. |
| 4 | "How long were they above the band?" | `DURATION` | `/v1/heatmap` | 3 · entire day | **`exceedance`** | A maximum says how hot. It can never say how long. |
| 5 | "Is site 3 chronically dangerous?" | `PERSISTENCE` | `/v1/heatmap` | 4 · day range | **`exceedance`** | One bad day looks structural; one good day looks safe. |
| 6 | "Which of our 12 sites is worst?" | `COMPARISON` | `/v1/heatmap` | 3 · entire day | **`exceedance`** | Ranks twelve sites by whichever hour you sampled — by the clock, not by heat. |

Granularity is **100 m on every row**, deliberately. Comparison ranks sites against each
other; varying resolution between them would rank them by resolution.

> **Name collision, deliberately namespaced.** `QuestionType.PERSISTENCE` ("is this site
> *chronically* dangerous?" — across many **days**) and `AnalyticType.PERSISTENCE`
> (longest continuous run of **hours** above threshold) are different things. A chronic
> question is answered with a day *range*, not with that analytic type. They compose;
> they are not synonyms.

---

## The duration-marker rule, and why it overrides the classifier

TASKS.md states it absolutely: any question containing *how long*, *chronically*,
*typically*, *this summer* or *worst* is a duration question and must **never** be
answered with `filter_type=1`.

So `DURATION_MARKERS` is **authoritative over the classifier**, and where they disagree,
the marker wins. This is not belt-and-braces — it caught a real gap during T6. *"Tell me
about the worst at this site"* carries the marker `worst` but matches none of the
comparison phrasings, so it fell through to `SNAPSHOT` and would have been answered with
a single hour of aggregate temperature.

Two different failures, two different responses:

| what went wrong | response | why |
|---|---|---|
| the **classifier** missed a phrasing | **escalate** to `DURATION`, and record it in `escalated_from` + the rationale | a legitimate question, not a code bug. Being wrong toward the broader layer costs a credit; being wrong toward the narrower one costs a wrong operational decision. |
| the **table** maps a type to a bad layer | **raise `RouterInvariantError`** | a programming error. A safety tool must crash rather than emit a layer it has already determined cannot answer the question. |

Escalation is always recorded, never silent — an audit trail that quietly rewrote its own
question is not an audit trail.

---

## Refusals

Priority is **fixed and documented** so the same input always produces the same refusal:
coverage first, then time, then request shape, then — last — the question/layer mismatch,
which is only meaningful once the request is otherwise valid.

| # | Reason | Trigger | Why it is a refusal and not an error |
|---|---|---|---|
| 1 | `OUTSIDE_US` | point outside the US coverage boxes | **A non-US AOI does not raise. It returns an empty-looking result and still spends the credit** (`[00:13:39]`: *"it's just going to spend your credit"*). This refusal is a cost control. |
| 2 | `BEFORE_2021` | date < **2022-01-01**, or unparseable | The documented start is 2021-01-01; **measured, coverage begins a year later**. 2021-07-15 and 2021-10-15 both returned `Completed` with zero tiles and were billed 4,220 credits each. *(The enum name predates the measurement and is kept only to avoid churning tests.)* |
| 3 | `BEYOND_FORECAST` | date > **today** | ⚠ **"Forecasts to now + 12 h" was measured wrong.** The API accepts `start_date` up to **today + 1 day** (HTTP 400 beyond, loud and free) — but **tomorrow returns one flat value for the whole day**: 34.34 °C with min = avg = max, against 33.7–41.9 °C for today. No diurnal structure, so `exceedance` against it is exactly 0 h or exactly 24 h. **The boundary is where the profile stops, not where the API stops accepting** — `MAX_FUTURE_DAYS_ACCEPTED=1`, `MAX_FUTURE_DAYS_USABLE=0`. Accepted ≠ answered, and it is billed. |
| 4 | `EXCEEDS_30_DAY_WINDOW` | span > 30 days | Returns **quietly truncated**. The caller is told to split it, with the number of calls. |
| 5 | `AOI_TOO_LARGE` | area > 15 mi² (38.85 km²) | Plan limit. |
| 6 | `GRANULARITY_TOO_FINE` | not one of 60/80/100 m | Data is 2 m above ground at **20 m** spatial resolution. There is no street-level detail to return. |
| 7 | `WRONG_LAYER_WOULD_MISLEAD` | see below | **The differentiator.** |

### `WRONG_LAYER_WOULD_MISLEAD` — the one that matters

Refusing a **well-formed question that the API would happily answer**, because the only
layer that fits the requested scope would produce a confident wrong answer. Two triggers:

**A chronic question scoped to a single day.**
> *"You asked whether this site is chronically dangerous, but gave me a single day. I can
> answer it, and the answer would be worthless: one bad day looks structural and one good
> day looks safe. Give me an end date — two weeks of the same month is enough."*

**A duration question scoped to a single hour.**
> *"You asked how long the site was above the threshold, but scoped it to a single hour.
> Duration cannot be measured in an instant. Ask about the day, or ask what the
> temperature was at that hour."*

Every refusal happens **before any call is made**, so no credit is spent, and every
refusal carries a message an operator can read. A refusal the operator cannot read is a
bug, and there is a test asserting exactly that.

---

## Unit discipline — the router never emits a bare `threshold`

The router emits `threshold_f` (heat index, **Fahrenheit**, because OSHA and NWS are
Fahrenheit and the users are US supervisors) plus `threshold_basis` recording what that
number is measured against. `params` carries the key `threshold_f_unresolved` — **not**
`threshold` — so a caller that passes `params` straight to the API gets a `KeyError`
instead of a wrong answer.

Resolving it is [`tools.py`](../src/heatguard/tools.py)'s job and nowhere else's, because
it needs live humidity. Two conversions, both silent killers:

1. **°F → °C.** Pass 91 meaning °F and the API reads 91 °C = 195.8 °F. Exceedance returns
   **0 hours at every cell**, status `succeeded`, credit spent, and the tool reports a
   confident all-clear across all twelve sites.
2. **Heat index → air temperature.** `exceedance` thresholds the *temperature* field;
   OSHA bands are *heat index*. In dry Phoenix air the heat index runs **below** air
   temperature, so the equivalent air temperature is **higher** than 91 °F. Under monsoon
   humidity it runs above, so the equivalent is **lower**. Same OSHA threshold, different
   air temperature, depending on the day — which is also the quantified form of the
   monsoon hypothesis in T8.

---

## Baseline for the headline metric — T7

Implemented in [`src/heatguard/metrics.py`](../src/heatguard/metrics.py).

### "Unsafe exposure-hours avoided" is not the metric

The proposal was `avoided = hours implied by the city-wide number − hours in the per-site
profile`. It was pressure-tested and replaced. Four problems, one fatal:

1. **A forecast high is a scalar.** It does not imply a number of hours. Turning it into
   hours requires assuming a diurnal shape — the exact thing the product exists to
   supply. The baseline would have to invent what it is being compared against.

2. **FATAL — the sign flips on the best case.** For the Chase Tower night crew, the
   city-wide *daytime* high implies roughly zero relevant hours across a 21:00–05:30
   shift, while the real profile shows several. The formula returns a **negative number
   for the single strongest case in the project.** The tool did not *avoid* those hours,
   it **revealed** them, and revealing them is the whole point.

3. **"Avoided" claims credit for a behavioural change that has not happened.** Hours are
   only avoided if a supervisor acts.

4. **It sums two opposite-signed wins that cancel.** Over-warning corrected (site cooler
   than the city figure → work proceeds) and under-warning corrected (site hotter or
   hotter for longer → work stops) are both wins, with opposite signs. Across twelve
   sites the tool can be right twelve times and net to roughly zero.

### What is measured instead — three numbers, none of which cancel

| metric | meaning | owner |
|---|---|---|
| `unsafe_worker_hours_caught` | crew-hours scheduled into hours the site was above threshold **and the city-wide figure said it was not** | safety officer |
| `productive_worker_hours_recovered` | crew-hours the city-wide figure would have shut down at sites that were actually below threshold | operations |
| `decisions_changed` | how many (site, shift) pairs got a different call — the honest denominator | both |

Both counters are floored at zero, so for any given site exactly one of them is non-zero.
That is what stops correct calls from cancelling.

Counted in **worker-hours**, not clock-hours — a 22-person crew and a 4-person crew are
not the same exposure — and **only inside the crew's shift window**, because hours nobody
was standing in are not exposure. That is the same correction that put night crews in the
roster in T1.

### The baseline is not a proxy — it is the actual number

**The official temperature for Phoenix is observed at KPHX: Phoenix Sky Harbor
International Airport.** When a supervisor hears "Phoenix hit 112 today", that figure came
from Sky Harbor.

Sky Harbor is **PHX-SKY in our roster** — square kilometres of unshaded concrete,
predicted `high_peak_long_tail`. So the counterfactual is not modelled or assumed. It is
one of the twelve sites we already measure, and it is structurally one of the hottest.
Applying it uniformly over-warns the irrigated sites and, for a night crew, describes a
shift that had already ended.

The scalar is applied **flat across every hour** of the shift. That is deliberately crude
and faithful: a supervisor holding one daily high has no shape to apply, so the call is
binary and covers the whole shift. Assuming anything richer would flatter the baseline
with information it does not have.

> **Verify in T4:** that PHX-SKY is the station the public Phoenix figure comes from is
> well-established but has not been confirmed against a source in this repo. It is
> load-bearing for the entire metric.

### Two implementation details that were quietly wrong

- **Fractional boundary hours.** A 05:00–13:30 shift is 8.5 hours long but contains
  **nine** hourly readings, because the 13:00 reading covers 13:00–14:00 and only half of
  it is in the shift. Counting readings as hours inflated every day shift by ~6%, silently
  and in the direction that flatters the product. Readings are now weighted by their
  overlap with the shift window, so the count can never exceed the shift length.
- **Night shifts need two calendar days.** A 21:00–05:30 shift reads hours 21–23 from day
  D and 00–05 from D+1. Given only one day, `metrics` **raises** rather than returning 3
  instead of 8.5 — a two-thirds undercount landing on the lead demo site.

### Sensitivity

Per T2, the rollup is reported at **both 91 °F and 103 °F** (`sensitivity_thresholds_f`).
Neither is neutral: at 91 °F a Phoenix summer *day* shift saturates while *night* shifts
differentiate sharply; at 103 °F the reverse. A result that only holds at one threshold is
a result about the threshold. `rollup()` refuses to sum comparisons made at different
thresholds or on different dates.
