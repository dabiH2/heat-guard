# Decision log

Append-only. Newest first. One entry per decision that changes the build, the thesis, or
the submission. Reversals get their own entry rather than an edit.

---

## D-005 — 2026-08-21 — Adopt the judge's 4-point checklist as a submission gate

**Status:** decided
**Trigger:** `05-builders-trap` — **Ahmed Abdelkhalek (Google Cloud) is a judge**, and he
published the filter he runs ideas through `[00:26:44]`: *"one takeaway is this checklist.
So run every feature or project idea through this."*

**Decision.** The README and the 3-minute video must answer all four of his questions
explicitly, in his vocabulary, before anything else is said:

1. **Hero** — the exact person and role. Not "outdoor workers". A Phoenix crew supervisor deciding whether to pull a crew.
2. **Pain** — the manual/slow/expensive thing they do now: read a peak-temperature forecast and guess.
3. **AI justification** — *"Is AI **generally** required to solve this? Or are we just using it to earn high points at the expense of latency and cost?"* Answer: **no, and that is why the router is deterministic.** The LLM parses and narrates.
4. **Kill switch** — the 24-hour simplest version: one site, one date, two analysis layers side by side.

Also adopt his problem formula `[00:13:10]` as **the opening line of the 500-word summary**:
*"Specific user group struggles to perform a specific task because of this core obstacle,
which results in measurable negative outcome."* He gates code on it — *"If you cannot fill
out every variable cleanly, then we're not really ready to write a single line of code."*

⚠ **Caveat, do not overreach.** He presents the checklist as advice, and the host presents
him as a judge. We do **not** know it is the shared scoring instrument. Answer it because it
is good and because one judge demonstrably thinks in it — never claim in the submission that
it *is* the rubric.

**Consequence:** no code change. This is a submission-artefact gate. Add the four answers to
the README before the architecture section, and put item 3 in the video's first minute.

---

## D-004 — 2026-08-21 — The architecture rule is now externally validated; lead with it

**Status:** decided — **promotes an assumption in `CLAUDE.md` to a sourced fact**
**Trigger:** `05-builders-trap`.

### What changed

`CLAUDE.md`'s architecture rule closed with a guess: *"constraining the LLM to what it is
good at **reads as** maturity to a Google/NVIDIA panel."* The Google panelist has now said it
himself, unprompted, on camera:

> `[00:25:12]` *"please be responsible with your resource budget. There's nothing free in the
> world. **Traditional deterministic code is faster, cheaper and entirely predictable.**"*
> `[00:21:28]` *"**evaluate AI choices critically**, ensuring that we're **not introducing
> unnecessary latency and cost just for the hype**."*
> `[00:23:30]` *"It's incredibly powerful. But it's not a silver bullet for everything.
> **It could, but should it?**"*

### Decision

- **`router.py` stops being a choice we defend and becomes the headline.** It is the answer
  to checklist item 3, given before the question is asked.
- **Q0 replaces Q1 as the lead quote** in the README and video (`video-insights.md` §6).
  Ahmed's *"It could, but should it?"* outranks the FortyGuard engineer quotes because it
  endorses the *architecture*, not the metric — and D-003 already established that the metric
  is not ours to claim.
- **Say the cost/latency argument out loud**, not just the auditability one. His framing is
  economic (*"at what cost?"*), ours was correctness-first. Use both; his lands harder with him.
- **Mention `data/fixtures/` and the backoff in the video.** His Q&A instinct on rate limits
  was *"why are you getting into those limits? What are you trying to do?"* `[00:52:44]` —
  a demo that hammers the API invites that question. Pre-empt it.

### Rejected alternatives

| Option | Why not |
|---|---|
| Keep the architecture as a footnote and lead with the heat thesis | The thesis is FortyGuard's own metric (D-003). The architecture is genuinely ours, and a judge just described it as the correct instinct. Lead with what is both ours and endorsed. |
| Lead with "we use AI agents" to score the Agentic track | Directly inverts what this judge filters for. He mocks *"we're just using it to earn high points at the expense of latency and cost."* Track 6 is satisfied by the agent parsing and narrating; it does not require the LLM to make the safety decision. |
| Rewrite the architecture to use more LLM reasoning now that Innovation is 15% | No. Innovation is scored as **track combination** (`01` `[00:36:02]`), which Track 4 × Track 6 already earns. Adding LLM surface would cost on impact and on this judge's checklist simultaneously. |

**Confidence:** high. Verbatim, on camera, from a named judge, corroborated by his own worked
example (`[00:21:58]`–`[00:22:50]` — the Gemini image-resize story, *"why do you want AI to do that?"* at `[00:22:36]`).

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
