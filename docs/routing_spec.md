# Routing spec — the decision table

The implementable form of the router. Source of truth is
[`src/heatguard/router.py`](../src/heatguard/router.py) — `DECISION_TABLE` is a literal
dict, not a chain of `if` statements, so it can be read, diffed and tested directly.

**No LLM call exists in this module.** The agent parses intent and narrates; the router
decides. That makes layer selection auditable (this is a safety tool), reproducible (demo
takes must match exactly), and testable with zero credits and no network — 224 offline
tests, of which ~90 cover this file.

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
| 2 | `BEFORE_2021` | date < 2021-01-01, or unparseable | No record exists. Nothing to answer with. |
| 3 | `BEYOND_FORECAST` | date > now + 12 h | The heatmap is the only forecasting layer, and only 12 h out. Beyond that, any answer is a historical average dressed as a forecast. |
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

## Baseline for "unsafe exposure-hours avoided"

> **T7.** Not yet written. The counterfactual, the formula and its limitations go here.
> Without a stated baseline the headline number invites "avoided versus what?" and the
> 40% Impact criterion wobbles.
>
> Already settled in T2: the number must be reported at **both** 91 °F and 103 °F
> (`sensitivity_thresholds_f`). A result that only holds at one threshold is a result
> about the threshold.
