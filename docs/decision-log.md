# Decision log

Append-only. Newest first. One entry per decision that changes the build, the thesis, or
the submission. Reversals get their own entry rather than an edit.

---

## D-009 — 2026-08-29 — Two sourced claims are over-claims; correct the wording, keep the thesis

**Status:** decided — **narrows two high-confidence records without overturning either**
**Trigger:** parallel extraction, adversarial re-audit of `02` and first read of `13`.

**(a) "Analysis layer" is our coinage, not Fawad's.** Re-verified independently: `layer` = **0**
occurrences in `02-temperature-api` .txt and .srt, and every Whisper escape hatch (`lair`,
`leer`, `lawyer`, `later`) is accounted for. His nouns are *"the analytic type"* `[00:24:30]`
and *"these other analysis thing"* `[00:24:41]`. `api-notes.md` currently asserts *"`analytic_type`
— confirmed verbally, and it is the 'analysis layer'"*. The first half is true; the quotation
marks in the second half are not. **Decision:** keep the concept, drop the quotation marks,
never present it as his phrase.

**(b) Two further mechanism claims are unsourced from the webinar.** `default`=0, `optional`=0,
`omit`=0, HTTP `400`=0 — Fawad never says `analytic_type` is optional, never says `tcm` is the
default, never shows that omitting it errors. And *"one optional string apart"* is factually off:
his own live `exceedance` call carries **three** extra fields `[00:27:05]` (`analytic_type`,
`threshold`, `direction`). **Decision:** source the default to the vendor client explicitly, and
replace "one optional string apart" with the stronger accurate version — *on a defaulted
`analytic_type` the `threshold` and `direction` you passed are silently ignored.*

**(c) "20 m native resolution" is now contradicted on record.** FortyGuard's own invited mentor,
`13` `[00:16:56]`: *"The field resolves near one kilometer. So a street corner is below what we
can actually see."* `api-notes.md` logs the 20 m claim as *"not contradicted by any source | keep"*
— that row is stale. Reconciliation: 20 m / 60–80–100 m is the **delivery grid**; ~1 km is the
**effective resolving power**. Both can be true. **Decision:** qualify the README line, attribute
the 1 km figure to Stelfox and not to FortyGuard as a spec, and use it to reframe the confessed
2-of-11 failure from *"our hypothesis was wrong"* to *"the field cannot resolve this, and the
vendor's own mentor says so"* — corroborated by our own 200 m AOI returning stdev 0.0.

**Consequence:** wording only. The trap, the six-parcel case study, the Celsius-thresholds claim,
the rate-limit contradiction and the non-US billing claim are all transcript-solid and unchanged.

**Also settled:** a re-audit agent proposed overturning `fg.filter_type.five_exists` on transcript
evidence — Fawad does enumerate a fifth value `[00:19:46]`. **Rejected.** The live probe returns
`Input should be 1, 2, 3 or 4`. Standing rule reaffirmed: **for API behaviour trust the live probe
over the webinar; for intent, vocabulary and judging signal trust the webinar.**

---

## D-008 — 2026-08-29 — The demand gap is a named, quantified, missed bar; build the remedy, not the evidence

**Status:** decided
**Trigger:** `12-vc-decision` and `08-pmf`, independently.

Two sources, neither aware of the other, put a number on the thing the submission does not have.

> `12` `[00:25:59]`, **Vikram, principal at Kota Capital — a judge**, asked directly *"how would you
> judge our projects?"* and answering *"I think I laid out many of the criteria"* `[00:31:46]`:
> *"I don't expect you to have 100 customer interviews, but **having three, four, five potential
> users who you've spoken with** […] I think that's **number one, super important**."*

> `08` `[00:43:38]`, the invited PMF mentor, who explicitly disclaims being a judge:
> *"I would rather see someone come out of a hackathon with **i spoke to these five potential
> customers i learned x y and z** then i built this."*

HeatGuard has **zero**. And Vikram ranks demand above mechanism explicitly `[00:27:34]`:
*"there's some projects that might be technically very, very impressive. But if it's not solving a
big enough problem in a large enough market, it's not as valuable."*

### Decision

**The confession stays, and it gets its missing second half.** The bet that candour reads as
credibility is **validated** — `11` `[00:19:42]` *"you will get extra points for that for sure"*;
`12` `[00:35:07]` names **overselling**, not gap-admitting, as the tune-out. But the quote the bet
rests on has a second clause the submission currently forfeits: *"…but also aware of either **how
they can solve it** or are confident enough to **ask for help** in solving this"* `12` `[00:21:37]`.

So: append to *"The mechanism is measured; the demand is not"* the specific first three calls in
order, and one explicit ask of the reviewer. Nothing more.

⚠ **Do not manufacture the evidence.** The PMF mentor lowers the realistic bar to *"one or two"*
`[00:43:20]` and counts non-response as data `[00:39:10]`, which makes a genuine send-log with real
timestamps worth having if there is time. A decorative or fabricated log inverts the exact
credibility bet the submission is making and is worse than the honest confession it replaces.

**Also decided:** name the decision log as the *compounding* asset (`12` `[00:08:24]` — defensibility
*"should have some sort of compounding factor"*; routing logic does not compound, an accumulating
decision trail does), phrased as **designed to accumulate**, not *already accumulating*. And state
the *"becomes a feature at FortyGuard"* roadmap line — `12` `[00:26:49]` blesses it by name, which
materially reduces thin-wrapper exposure. **Confidence:** high; two independent sources, one a judge.

---

## D-007 — 2026-08-29 — Stop conceding "the agent does not decide"; the decision table *is* the guardrail

**Status:** decided — **reverses a wording choice made under D-004, not the architecture**
**Trigger:** `10-physical-ai`. The speaker is **Professor Jonathan Reichental — a judge**
(*"our mentor and judge today"* `[00:00:20]`) **and an advisor to FortyGuard** who *"helped us shape
FortyGuard as what you're seeing right now, starting from the dashboard"* `[00:01:45]`.

He defines the track's own term, `[00:48:29]`:
> *"**agentic AI** means that not only does AI complete a function for us, but it also **makes
> decisions on our behalf**. **We create guardrails. We define the conditions**, then it makes a
> decision on our behalf."*

Read literally against that definition, the submission's current line — *the agent parses and
narrates but does not decide* — describes a **non-agentic** system, in a track scored on agency.
That is the one scoring risk this session exposes, and the same sentence supplies the fix.

**Decision.** Reword to: *the decision table is the guardrail; the system decides layer, threshold
and refusal inside human-authored conditions — the LLM does not.* **Text only. The behaviour does
not change and the determinism test must still pass unmodified.**

### The deterministic bet is now backed by two judges on independent grounds

D-004 justified it on Abdelkhalek's economics. Reichental adds safety, `[00:48:58]`:
> *"there should be **humans in the loop** […] where it comes to human safety. That would be a good
> one, I think, a good criteria. **Can humans get hurt?**"*

HeatGuard's domain is human thermal harm, so it sits inside his own test. He also names
*"governance […] that there is **recourse**? How do we have **oversight**?"* `[00:42:07]` — the exact
vocabulary the refusal path and the with/without-model equality test answer. **Say both.**

⚠ One maximalist line exists — *"Everything that can be autonomous will be autonomous"* `[00:44:04]`
— but it is his **early-2030s forecast**, bounded four minutes later by the humans-can-get-hurt test.
**Rejected:** adding LLM decision surface. It would break the determinism test, which is the
submission's single strongest artefact, and move *away* from this judge's stated criterion.

---

## D-006 — 2026-08-29 — All four judging weights are now sourced; 75% of the score is Impact + Technical execution

**Status:** decided — **supersedes `fg.judging.weights_partial` and half of `fg.unsourced.reconfirmed_after_six_sessions`**
**Trigger:** `09-dashboard-walkthrough` `[00:59:30]`–`[00:59:36]`, spoken by a FortyGuard organiser,
unhedged, all four in one breath:

> *"So **impact and relevance, 40%**. **Technical execution coming up to 35%**. **Innovation is 15%**
> and then **communication is 10%**."*

For six sessions the pack recorded that only Impact (40) and Communication (10) were ever spoken,
both hedged with *"like"*, and instructed: *"Do not present 35/15 as sourced fact."* **That
instruction is now retired.** Communication = 10% is independently restated in `11` `[00:50:38]`.

### Consequence — where the remaining hours go

**Impact 40 + Technical execution 35 = 75%**, and both are judged from the **description, the repo
and the video** — not from clicking around the app. Communication is 10%, so narrative polish is
capped at a tenth of the score and must not crowd out the measured numbers.

`fg.judging.definitions_differ` still holds and now matters more: *"technical execution"* is defined
largely as **AI-tool disclosure**, and *"innovation"* as **track combination** — Track 4 × Track 6
already earns it. The organiser also tells judges to ask *"Have you just hard coded values into it?"*
`09` `[00:58:46]`, which is precisely how a hostile skim misreads a deterministic rule engine.
**Decision:** ship a threshold-provenance block in the README naming the authority behind every
number (OSHA / NWS HeatRisk), and label any genuinely arbitrary value as a configurable default
rather than inventing a citation. This is the cheapest available defence of the 35%.

**Still unsourced after thirteen sessions and 107,000 words:** the 500-word summary limit. Keep 500
as a self-imposed ceiling; never cite it as a rule.

---

## D-006 · 2026-08-29 · The rubric is settled, and two of our criterion definitions were wrong

**Status:** decided
**Trigger:** Participant Handbook p17 ("11. JUDGING & SUBMISSION") and the `#announcements` Slack
canvas, both obtained 29 Aug. Plus transcripts `07` to `13`, which completed the corpus.

### What changed

**All four weights are confirmed.** 40 / 35 / 15 / 10, from the handbook, with per-criterion
wording. The long-running warning in `CLAUDE.md` that 35% and 15% were unsourced is closed. That
file predicted they would turn out to live in a handbook page. They did.

**Two definitions we were working from were wrong**, and both errors came from treating the
kickoff's spoken introduction as if it were the rubric:

| We believed | Handbook p17 actually says |
|---|---|
| "Technical execution" is mostly **AI-tool disclosure**, not code quality | *"It works, the build is sound, data handled well; deployable, client-grade quality"* |
| "Innovation" is **track behaviour** | *"Original approach or a fresh combination of ideas"* |

### Decision

1. **Promote the engineering work to the front of the technical story.** We were treating the 35%
   criterion as a paperwork item to satisfy with a disclosure line. It is the engineering-quality
   criterion. The 336 offline tests, the committed fixtures, the guards placed before the call, and
   a demo that runs with no API key are scoring on its main axis. Say that plainly rather than
   burying it under the router narrative.
2. **Keep the router as the Innovation claim, and reframe it.** Track 4 × Track 6 still earns
   "fresh combination", but the stronger argument is now a judge's own gloss on originality:
   Vikram Venkat, `12-vc-decision` `[00:31:59]`, *"the best solutions have some sort of trick. It's
   not about brute force solving a problem."* A deterministic decision table in place of an LLM
   call **is** the trick. That framing beats "we combined two tracks".
3. **Name the zero-customer-conversations gap first, not last.** Venkat states the evidence bar for
   a two-week build at `12` `[00:25:55]`: *"having three, four, five potential users who you've
   spoken with."* We have none. It is on the 40% criterion. The README already discloses it; move
   it earlier and pair it with the specific next step, because a judge who finds it himself scores
   it worse than a judge who is handed it.
4. **Restructure the video opening.** Venkat wants, in the first 60 to 90 seconds, *"what you're
   doing, why you're doing it, and who you are"* `[00:34:38]`, with **value before mechanism**
   `[00:36:35]`. He tunes out on buzzwords, vagueness, and overselling `[00:34:22]`. And the video
   is a **gate**: `[00:35:31]` *"we will [...] start fiddling around with the project [...] unless
   you have done something very wrong in your video."* A weak opening does not cost 10% of the
   score, it costs the demo visit where the other 90% is evidenced.
5. **Apply the 10-minute time-to-value test to the app before submitting.** `12` `[00:33:25]`: *"If
   I can get the value within the first 10 minutes of having the product in my hands, I already
   like it."* No rulebook, no explanation needed. The landing tab must carry the headline number
   before any interaction.
6. **Fix the cold start.** Measured 29 Aug: the Streamlit demo served an empty shell for roughly 40
   seconds on a cold open. `keep-alive.yml` exists; verify it is actually firing, because the live
   link is the artifact organisers say judges will 100% open.

### Not changed

The thesis, the architecture rule, and the scope-discipline table all stand. D-004's finding that
the Google judge endorses deterministic code is reinforced, not weakened, by Venkat's independent
"not brute force" line: two of the four judges now say versions of the same thing.

**Confidence:** high on the rubric (authoritative document, three corroborating sources). High on
the judge quotes (verbatim, on camera, from named judges answering direct questions about judging).

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
