# Decision log

Append-only. Newest first. One entry per decision that changes the build, the thesis, or
the submission. Reversals get their own entry rather than an edit.

---

## D-003 — 2026-08-20 — Stop claiming HeatGuard "measures" exposure duration

**Status:** decided
**Trigger:** D-002 fallout.

`exceedance` and `persistence` are server-side API products (`api-notes.md` §1). HeatGuard
does not compute duration; it *requests* duration, correctly.

**Decision.** Every artefact — README, 500-word summary, video narration, docstrings —
claims only what is true: HeatGuard **selects the correct analysis layer for the question
asked, states why, and refuses when no layer can answer it.** The metric is FortyGuard's.
The routing, the rationale and the refusal are ours.

**Why this matters more than it sounds.** The judges include FortyGuard engineers who know
exactly which parameters exist. A claim to have built their `analytic_type=persistence` is
not a stretch, it is a visible error — and it invites the reviewer to conclude the entrant
did not read the docs. Understating here reads as competence.

**Consequence:** grep the repo for "compute", "calculate", "derive" near "duration" /
"exposure" before submission and rewrite each one.

---

## D-002 — 2026-08-20 — The analysis layer is `analytic_type`, not `filter_type`

**Status:** decided — **supersedes the `fg.wronglayer.decoded` inference (medium confidence)**
**Trigger:** first read of the raw webinar transcripts.

### What changed

`fg.wronglayer.decoded` recorded a *medium-confidence inference* that "the wrong analysis
layer" meant `filter_type` (1 = hour … 5 = month), possibly with `granularity` and endpoint
choice. Two things turned out to be wrong.

**1. The quote it was decoding does not exist.** *"The API is asynchronous, and picking the
wrong analysis layer will give you a confident wrong answer"* is said by nobody in any of
the four sessions. In `02-temperature-api` the word "layer" appears **0 times** and
"confident" appears **0 times**. It appears to be a conflation of Fawad's real
*"asynchronous […] non-blocking"* `[00:18:50]`, his garbled *"the plausible temperature and
everything could go wrong"* `[00:42:21]`, and Aashan's *"a decision maker can take a
decision **confidently**"* `03` `[00:19:07]` — a different speaker in a different session.

**2. The real layer selector is `analytic_type`.** Fawad, `02` `[00:24:30]`–`[00:25:16]`:
`tcm` (snapshot) · `time_of_measure` · `exceedance` (hours past threshold) · `persistence`
(longest continuous run). `filter_type` is the **time window**; `analytic_type` is the
**question asked of that window**. Independently confirmed against the vendor client.

### Decision

- **The thesis stands.** Do not pivot. The failure mode is real and now has a mechanism
  that is *harder* to catch than the one originally assumed: `tcm` and `exceedance` share
  an endpoint, an AOI and a `filter_type`, differing by one optional string, with no shape
  change to signal the substitution.
- **`router.py` selects `analytic_type` as its primary decision**, `filter_type` as
  secondary. Both go in the rationale string and both go in `decisions.jsonl`.
- **The invented quote is banned from every artefact.** Replace it with Q1/Q3/Q5 in
  `video-insights.md` §6 — all verified verbatim with timestamps.
- **The demo is Fawad's own case study**, not one we construct: six parcels, 28 Jul–3 Aug,
  **0.7 °C** peak spread vs **19 h exceedance / 5 h unbroken** (`02` `[00:36:14]`–`[00:37:23]`).

### Rejected alternatives

| Option | Why not |
|---|---|
| Keep `filter_type` as "the layer" and quote the sentence anyway | The sentence is fabricated and the judging panel includes its supposed author. Non-starter. |
| Abandon the thesis, since duration is a native parameter | The trap got *worse*, not weaker. Selecting between two indistinguishable-looking calls is a better problem than selecting between differently-shaped ones. |
| Reframe around the °C/°F `threshold` trap instead | Strong (an all-clear from a unit error is the worst possible output) — but it is a *bug class*, not a *decision architecture*. Keep it as the vivid example inside the layer thesis, not as the thesis. |

**Confidence:** high. Two independent sources agree (on-camera engineer + vendor client
source), and the negative finding — that the quote is absent — is mechanically verifiable
by grep.

---

## D-001 — 2026-08-20 — Overlap with FortyGuard's roadmap is not a risk to manage

**Status:** decided
**Trigger:** session 3 shows FortyGuard already demoing outdoor-worker heat stress, route
exposure scoring, comfort-hours windows and extreme-heat-day counts
(`video-insights.md` §3, C1–C7). Fawad also states the alert automation engine is
*"something we are building ourselves"* `02` `[00:44:01]`.

Asked directly in session 2 Q&A `[00:53:19]`–`[00:53:28]`:
> *"if it's clashing with [FortyGuard's] products, it's fine. **Go ahead, clash it with our
> products.** […] you won't be hampered or you won't be penalized for it. […] If we are
> building something and you can do it in a better way than us, I think we would appreciate it."*

**Decision.** Stop treating roadmap overlap as a scoring risk — it is explicitly permitted.
Keep treating **indistinguishability** as a risk, which is a different problem.

Defensible ground, none of which appears anywhere in session 3: **deterministic layer
selection · stated rationale · refusal on insufficient data · an auditable decision trail.**

⚠ One caution: FortyGuard's stated default for bad data is the opposite of ours —
*"you can interpolate it"* `03` `[00:36:25]`. Refusal must be **argued** as correct for a
safety-critical decision, not assumed to be self-evidently better.

**Do not** position HeatGuard as an alerting product (C6) or as a cool-routing product
(C7 — three separate predictions that the field will be crowded there).
