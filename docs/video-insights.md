# Webinar insights — from the raw transcripts

Replaces every abstract-derived note about sessions 2, 3 and 4. Everything below is from
the Whisper transcripts in `../../`, with `[HH:MM:SS]` pointers into the `.mp4`s.

**Whisper reliability:** proper nouns and numbers are unreliable. "FortyGuard" is
transcribed at least nine ways across the four files (*40 guards, Forte Guard, Fort Guard,
4E Guard, 4reguard.com, FortiGuard, Fortygarde, 40 cars, Fodegaard's*). Every figure below
is quoted as spoken and marked where it is hedged or garbled. Nothing here is silently
corrected.

Sessions in descending value:

| # | File | Session | Speaker | Verdict |
|---|---|---|---|---|
| 2 | `02-temperature-api` | Building on the Temperature API | **Fawad Shah**, Software Engineering Lead | 🟢 High — rewrites the thesis |
| 3 | `03-heat-intelligence-cloud` | Heat Intelligence Cloud | **Aashan Javed**, AI/ML Engineer | 🟢 High — territory map + best quotes |
| 1 | `01-kickoff` | Onboarding & Kickoff | **Jay Sadiq** (CEO), **Snehil Ahuja** (Product Lead) | 🟡 Medium — rules, judging, mechanics |
| 4 | `04-autodesk-forma` | Breaking Silos with Autodesk | **Jordana Rosa**, Autodesk | 🔴 **Zero value. Do not rewatch.** |

---

## 0. THE HEADLINE — the founding quote is not real

**`fg.wronglayer.decoded` (medium confidence) is now RESOLVED, and the premise was wrong.**

The quote the whole submission was built around —

> ~~*"The API is asynchronous, and picking the wrong analysis layer will give you a confident wrong answer."*~~ — attributed to Fawad Shah

**does not exist.** In `02-temperature-api` the word **"layer" appears 0 times** and
**"confident" appears 0 times**. Nobody says it in any of the four sessions.

It looks like a conflation of three real fragments:

| Fragment | Speaker / TS | Verbatim |
|---|---|---|
| the async half | Fawad, `02` `[00:18:50]` | *"these analysis endpoints are asynchronous, which means they are non-blocking."* |
| the "go wrong" half | Fawad, `02` `[00:42:21]` | *"the plausible temperature and everything could go wrong."* — garbled slide read-out, **no elaboration follows**, he moves straight to budgeting |
| the "confident" half | **Aashan**, `03` `[00:19:07]` | *"if you have all the information but you are not able to present it in a way where a decision maker can take a decision **confidently**, then obviously it's of no use."* — **different person, different session, and about presentation, not layer choice** |

**Never put that sentence in the README or the video.** The judges include FortyGuard
people. Attributing an invented quote to their engineering lead is the single worst
unforced error available here.

### The thesis survives — and the real mechanism is better

`filter_type` was the wrong guess. The parameter that silently changes the answer is
**`analytic_type`**. Fawad, `[00:24:30]`–`[00:25:16]`:

> *"Then we have also the analytic type. So this is like basically the T same ["tcm"],
> this is just the simple snapshot. And then we have these other analysis thing like time
> of measure, exceedance persistence. So **exceedance** is something like for how many hours
> a certain value was above the threshold. […] And for **persistence**, it's quite similar
> but it gives you a continuous long run. Like for example, continuously it stayed above 35
> for six hours, seven hours."*

- `filter_type` = **which time window** (single hour / hour range / day / day range / month)
- `analytic_type` = **which question you ask of that window** (snapshot / time-of-measure / exceedance / persistence)

Same endpoint, same AOI, same `filter_type` — one optional string apart. That is a
*better* trap than the one originally imagined, because there is no shape change to tip
you off.

**Consequence, and it is not comfortable: duration above threshold is a native API
parameter.** HeatGuard does not compute it. The IP is not the metric — it is the
deterministic selection of `analytic_type` + `filter_type` per question, the stated
rationale, and the refusal. Rewrite any README sentence claiming HeatGuard "measures
exposure duration"; it *asks for* exposure duration, correctly, which is a different and
more honest claim.

---

## 1. Session 2 — Temperature API (Fawad Shah) 🟢

Technical detail lives in `api-notes.md` under **[TRANSCRIPT]**. This section covers what
happened in the room.

### Rewatch these three segments only

| TS | What | Why |
|---|---|---|
| **`[00:24:17]`–`[00:25:16]`** | `filter_type` + `analytic_type` definitions | The correction to the whole thesis. ~1 min. |
| **`[00:33:37]`–`[00:38:46]`** | The parcel case study, end to end | The inversion demo, using their data. ~5 min. |
| **`[00:53:14]`–`[00:53:38]`** | "clash with our products, it's fine" | Removes the competitive-overlap worry. ~25 s. |

### ⭐ The worked use case — and the inversion, handed over

`[00:33:37]`–`[00:38:46]`. A real client case study, shipped in the quickstart repo
(`[00:40:03]`: *"This is already shared within the API quick start guide as well"*).

Setup: six parcels, **17.38 acres** total, `granularity=80`, window **28 July – 3 August**
`[00:34:24]`–`[00:34:52]`. Parcels are clipped from a single tile.

Then the two rankings, in sequence:

**Ranked by peak temperature** `[00:36:14]`:
> *"So the hottest to coolest parcel, that's like **0.7 degrees Celsius**, South Campus
> edge versus the River North."*

Six sites. A 0.7 °C spread. Operationally that reads as *"they're all the same, send the
crew anywhere."*

**Ranked by duration** `[00:36:37]`–`[00:37:23]`:
> *"we are also giving the **exposure duration per parcel**. Like this is where the
> **exceedance and persistence** comes in. Like how much time the longest run was. Like for
> example, this is it remained persistent for above a certain point for **five straight
> hours**. So that's a lot of heat. […] Like for example, for **more than 19 hours**, it
> stayed above and then for **five hours straight**, it was above the threshold."*

**This is the demo.** Same six sites, same week, same API: peak says *indistinguishable*,
duration says *19 hours of exceedance and a 5-hour unbroken run*. It is FortyGuard's own
case study, presented by FortyGuard's own engineering lead, and it makes the argument
without HeatGuard having to assert anything.

Also in the run: `[00:35:24]` daily peak **36.3 °C**, average **24.2 °C**; `[00:35:51]`
*"it got over a reach around **98.5 Fahrenheit**, which is about 37 degrees"* — note they
present in °F while the API takes °C thresholds, exactly the unit trap in `api-notes.md`.

**→ `demo_day_candidates.md` risk is materially reduced.** The near-inversion exists in
their published fixture data. Worst case, that is the fallback demo.

### The six endpoints — deltas only

Nothing contradicts the endpoint table beyond what `api-notes.md` records. New colour:

- `[00:10:23]` *"majorly **six** end points. There could be many smaller ones as well, but
  all the things that you need are within these six end points."*
- `heatmap` `[00:17:20]`: *"returns the tile grid of surface temperature over an area […]
  It is basically **exceedance, persistence, time of measure**."*
- `env_params` `[00:17:44]`: *"apparent temperature, **heat indexing**, humidity"*; later
  `[00:27:45]` *"heat index Celsius […] apparent temperature Celsius"*, plus
  `[00:28:04]` *"CO2, methane and everything"*.
- `satellite` `[00:29:03]`: classifies *"a building, a route or road or a sidewalk or earth
  or maybe grass"*. Demo returned *"a building 100%"* `[00:29:43]`.
- `streetview` `[00:30:29]`: demo showed *"fountain covers 34.5, 4% of it, then tree, then
  sky and water and grass"*. Confirms the **Explicitly out** ruling — it is scenery.
- `heat_intelligence` `[00:31:01]`–`[00:33:26]`: 25-page PDF, five sections (geographic,
  environmental factors, urban factors, events/heat history, anthropogenic factors),
  2–3 minutes to generate. He claims accuracy *"close to 100%"* `[00:33:00]` — marketing,
  unfalsifiable, do not repeat.

### ❌ "The parts that trip people up" — this segment does not exist

The words *trip*, *gotcha*, *mistake*, *watch out* and *confus\** appear **nowhere** in the
transcript. There is no pitfalls segment. The session ran out of time twice and he says so:

- `[00:27:57]` *"due to the time restriction, I don't think I could go over everything in too much details"*
- `[00:33:26]` *"if I get to explain this, I think it's going to get over the time"*
- `[00:40:21]` *"the last part, I'm afraid I don't have enough time"*

Whatever promised that segment was an abstract, not the delivered session. **Delete the
expectation.** The nearest thing to a pitfall he actually gives is the non-US warning
(`[00:13:23]`, silent + billed) and the Celsius-thresholds line (`[00:13:45]`).

### Track 06 / agentic — thin, rushed, but usable

`[00:40:21]`–`[00:44:35]`, delivered in under four minutes with an apology. What he
actually recommends:

**Pick endpoints by question, not by inventory** `[00:40:53]`–`[00:41:33]`:
> *"it's really good to know that **which of the APIs are essential to you**. So which of
> these could give you a better answer to what you want to serve. So I would say that you
> could use, for example, might need four, just like in this one rank, **you can just rank
> the sites on duration** […] It's really important to know **what the use case you're
> serving** and you're using those APIs in that way."*

Garbled, but the shape is unmistakable — and *"might need four"* is almost certainly
`filter_type=4` (day range), which is exactly what the exceedance run uses at `[00:27:02]`.
**FortyGuard's engineering lead, describing the agentic track, spontaneously reaches for
"rank the sites on duration."** That is HeatGuard's core loop, endorsed in advance.

**The model matters more than the endpoint list** `[00:41:39]`:
> *"you just need to make sure that the model that you build, **it should be more relevant
> to you than the endpoint list**."*

**Don't over-commit to a framework** `[00:42:56]`: *"Don't stick to a particular framework,
I would say"* — and `[00:43:04]` he suggests *"a maybe cloud desktop or any LLM"*
(= Claude Desktop) driving the API directly.

**His three worked agent examples** `[00:43:16]`–`[00:44:10]`:
1. A **heat response agent** — *"you give it data and you ask it something and it analyzes it and it gives you a better result."*
2. A **bot that shows its reasoning** — *"the [terrace?] question that I asked and it gives you the **evidence to support it** and **the judges know that you can see the reasoning is there** as well."* ⭐ **He is telling you the judges look for visible reasoning.** HeatGuard's rationale string and `decisions.jsonl` are aimed straight at this.
3. An **alert automation engine** — *"you get alerts to an area that's being above 32 degrees."* ⚠ Immediately preceded by `[00:44:01]`: ***"This is something we are building ourselves."*** → see collisions, §3.

**Closing line, and the best quotable from this session** `[00:44:14]`:
> *"the agent AI, we're living in a world I think it's **more easy to build something and
> more difficult to understand the problem**. So I would assume that whatever you're
> building, try to understand what you're building, then go towards the development."*

---

## 2. Session 3 — Heat Intelligence Cloud (Aashan Javed) 🟢

### ⚠ Critical framing: these are not shipped products

Six "products" are demoed. They are **the presenter's own demo builds**, not FortyGuard
product. Stated explicitly at `[00:27:38]`: *"these are all like starters in terms of
ideas… These are like just brainstormers that he built in order to give you guys an idea, a
path"*, and `[00:07:34]` *"I've built each of this product myself."*

**That is worse, not better.** They are the reference implementations a mentor/judge built
and showed to every entrant — the mental template your submission gets compared against.

What FortyGuard genuinely ships is the API: four data domains, three main endpoints,
parcel granularity, 12 h forecast, history to 2021, hourly catalog refresh.

### The six demo products

| Product | Sector | TS |
|---|---|---|
| **CoolScope** | real estate — AOI temp, land-cover cause, cooling-intervention simulator, intervention efficiency ranking, heat-day projection, property uplift | `[00:11:27]`–`[00:14:26]` |
| **Cool Route** | cold-chain + delivery logistics — cooler-route optimisation, exposure scoring, comfort windows, per-cargo thresholds | `[00:14:31]`–`[00:17:05]` |
| **Grid Peak** | electric demand — peak/net demand forecasting, transformer load | `[00:17:05]`–`[00:19:07]` |
| **Thermal Grid** | data centres — heat prediction, PUE, carbon-aware scheduling, neighbourhood alerts | `[00:19:25]`–`[00:20:32]` |
| **Thermal Score** | insurance — heat risk index with triggers | `[00:20:32]`–`[00:21:44]` |
| **Carbon Lens** | ESG / air quality — AQI forecasting, vulnerability ranking | `[00:21:44]`–`[00:23:43]` |

---

## 3. 🔴 COLLISIONS — where FortyGuard already occupies HeatGuard's ground

Read this before writing a word of the README. Ordered by severity.

### C1 — Outdoor-worker heat stress is named as a solved, one-endpoint use case

Aashan, `[00:03:35]`:
> *"So you want to target the [cold] chain logistics, you have endpoint, you have to target
> **the outdoor worker heat stress, you have wet [bulb] for that**. So all of these things
> are available at your fingertip and you just have to call the endpoint."*

**HeatGuard's differentiation cannot be "we surface wet bulb for outdoor workers."** That
is a documented one-call answer.

### C2 — "Exposure score" and cumulative exposure along a route, demoed live

`[00:15:09]`–`[00:15:42]`:
> *"I'm routing them based on the cooler temperature. You can see the **overall distance
> exposure** as well. **You can define the exposure score** based on your particular, either
> scientific standard or your particular standard. […] wet bulb […] is the most important one
> here because you'll be using that **to measure the outdoor worker stress** as well."*

### C3 — "Comfort hours" and shift windows — the inverse of hours-above-threshold

`[00:15:45]`:
> *"So you can then **predict the comfort hours** as well. You can **predict the windows**
> as well where you think it will be most suitable **for the workers to deliver** […] You can
> pick out those windows."*

Restated in Q&A `[00:25:17]`: *"it's mostly for outdoor worker stress. And think about
**windows where the temperature is less** […] **Pick those windows.**"*

⚠ Note **"comfort analysis" is one of the four shipped API domains** (`[00:01:59]`) — so
this may be API-native, not demo-side. **Highest-probability pre-existing implementation of
HeatGuard's core metric. Probe it.**

### C4 — Extreme-heat-day counting (exceedance at day granularity)

`[00:13:44]`: *"You can **project heat days, extreme heat days** that are there. You can, for
example, take into historical data and then project heat days."* Plus `[00:13:58]`
*"your comfort [hours] as well within the day."*

### C5 — Per-category thresholds, already implemented — for cargo

`[00:16:41]`: *"for frozen items, there's a **different level of threshold** […] Similarly for
[pharma], for vaccines, for fresh produce […] for each category, you have a **different
threshold level** as well."*

Threshold-per-class exists. It is applied to **cargo, never to worker physiology.** That
gap is the opening — but the mechanism is not novel.

### C6 — Alert automation: FortyGuard says it is building this itself

Fawad, `02` `[00:43:59]`–`[00:44:10]`: *"the **alert automation engine** as well. **This is
something we are building ourselves.** So for example, you get alerts to an area that's
being above 32 degrees."*

Plus Aashan `[00:19:59]`: *"you can build **alert systems** around that. And if in a particular
neighborhood, you see that **in particular time windows**, the temperature is increasing […]
and it is affecting the health facilities there. So you can **link it back to health data**."*

→ **Do not position HeatGuard as an alerting product.** Position it as a *decision router
that refuses*. Alerting is their roadmap; refusal is not.

### C7 — The lane is explicitly, repeatedly predicted to be crowded

- `[00:05:10]` *"I'm sure most of you guys will be building products around this idea"*
- `[00:14:38]` *"I expect that a lot of you guys will build that"*
- `[00:24:47]` *"I am also predicting that most of you guys are building it"*

### ✅ The whitespace — what is absent from all 775 lines

Nothing in session 3 mentions: **refusal, abstention, "we can't answer that",
data-sufficiency checks, deterministic layer selection, uncertainty quantification,
OSHA/NIOSH, acclimatisation, work/rest ratios, or shift scheduling for humans.**

And the one piece of bad-data guidance is the **opposite** of refusal, `[00:36:03]`:
> *"the strategy to handle missing data is really simple. If you find some inconsistencies,
> you can rely on **interpolation** approaches. […] So you can interpolate it."*

⚠ **Use this carefully.** FortyGuard's stated default is *fill the gap and answer anyway*.
HeatGuard's refusal is the direct antithesis — which is genuine differentiation, but it is
a position the mentors have **not** endorsed. Argue *why* refusal beats interpolation for a
safety-critical decision; do not assume the judges already agree.

### And the release valve

`02-temperature-api` `[00:53:14]`: ***"Go ahead, clash it with our products. It's fine.
[…] you won't be hampered or you won't be penalized for it."***

Overlap is safe. Indistinguishability is not.

---

## 4. Session 1 — Kickoff (Jay Sadiq + Snehil Ahuja) 🟡

Judging weights and submission mechanics are folded into `CLAUDE.md`. What is left:

### Rules found here and in neither the summary nor the handbook

| Finding | Verbatim | TS |
|---|---|---|
| **Seven tracks**, never enumerated aloud | *"there are seven tracks that we have said"* | `[00:32:28]` |
| **Combining tracks is rewarded**, not merely allowed — it is the *Innovation* criterion | *"Or you combine two to three different tracks? We want to see how innovative your ideas are."* | `[00:36:02]` |
| **Pivoting from your registered idea is free** | *"There is nothing binding for you, whatever you were thinking about when registering to your final product. We want to see how you actually evolve"* | `[00:46:09]` |
| **Multiple projects allowed; only ONE is reviewed** | *"we're not going to review two applications for you. We're only going to review one. […] your previous applications get written over"* | `[00:54:29]` |
| **No 1:1 mentorship exists** | *"Are the mentorship sessions collective or individual? **These are collective.** […] treat it as a lecture"* | `[00:46:23]` |
| **Idea review by email is available** | `02` `[00:45:44]`: *"If you do have a developed idea and you do want reviews on that, you can email hackathon@…"* — but *"We can give you a general direction"* only | `02` `[00:45:44]` |
| **Two-stage screen** before judges | *"everything is ready for submission for the judges and the second layer of screening"* | `[00:24:51]` |
| **Prize: $6,000 + NVIDIA GPUs**, single overall top-three — **no per-track prizes mentioned** | *"there is $6,000 on the line, Nvidia GPUs as well"* / *"like winners, the top three"* | `[00:36:25]`, `[00:55:11]` |
| **Certificates**: completion + winning | | `[00:54:57]` |
| **Solo entrants file nothing** | *"solo members, you are good to go. You don't have to do anything. You don't have to fill any form."* | `[00:43:40]` |
| **Deadline 30 Aug 23:59 GST**, hard | *"this is a hard close on the deadline"* | `[00:40:39]` |
| **2 m above ground** confirmed | *"which gives you a two meter resolution from the ground"* | `[00:19:02]` |

### ⚠ Contradiction with the effective-deadline plan

`CLAUDE.md` sets an **effective deadline of Aug 29** because connectivity is lost Aug 30.
That is still correct for *submitting* — but the transcripts add a second, later
requirement nobody had recorded: **the live link must remain up until 16 September**, and
**API access is revoked when judging ends on the 16th** (`02` `[00:59:31]`, `[01:00:01]`).

→ The deploy must survive ~2.5 weeks unattended, then survive key revocation. Cached
fixtures are load-bearing for the *submission*, not just for tests.

### The one thing the organisers wanted said, and never finished saying

Snehil, `[00:14:34]`, cut off mid-sentence by a four-minute connection drop and never resumed:
> *"it measures above two meters above the ground. **Why does that matter?** If you open up
> your like your phone right now and open up the weather app itself, **you see just one
> temperature** and that is feels like, which is that?"*

That is the *one number for a whole city is wrong* argument — the pitch FortyGuard's own
product lead tried and failed to deliver. Finishing it for them in the video is a strong,
legitimate move.

---

## 5. Session 4 — Autodesk Forma (Jordana Rosa) 🔴 NOTHING HERE

**Verdict: no usable overlap. Do not rewatch. Do not cite.**

It is a vendor overview of Forma Site Design — early-phase building massing, feasibility,
and sun/daylight/wind/noise/carbon analysis for architects deciding **where to put a
building before the design is locked**. The persona is the designer, never anyone managing
people already working on a site.

**Zero mentions** of: construction workers, site workers, occupational safety, OSHA, heat
stress or heat illness in people, exposure duration, shade planning for people, or
time-above-threshold. "Construction" appears constantly but only as an industry vertical —
the C in AEC, i.e. the firms who buy Autodesk licences.

The closest citable line is `[00:51:29]` *"We care about the city, we care about comfort, we
care about the materials"* — design-stage site planning. **Citing it as persona validation
would be a visible stretch to any judge who watched the session.**

Jordana effectively gives permission to skip, `[00:36:02]`:
> *"let's say you are nothing correlated to construction, design, or making, then, yeah,
> maybe it's not the best way to go because **you should focus on a problem that you deeply
> understand**."*

Two facts worth keeping anyway:
- **Forma is optional.** Host, `[00:46:26]`: *"It's not. It's only compulsory to use
  [FortyGuard's] API, which is our temperature API."*
- One good line, on hackathon strategy generally, `[00:14:39]`: *"I would recommend you to
  **choose problems you deeply understand**."*

---

## 6. ⭐ QUOTABLE LINES — 5 candidates, verified verbatim

Ranked by usefulness for the README and the 3-minute video. **All five are real. The one
you were planning to use is not.**

### Q1 — Aashan Javed, `03-heat-intelligence-cloud` `[00:22:50]` ★★★ BEST
> *"you can just directly use that information and state pla[in] temperatures as well,
> pla[in] AQI values as well, **which gives no real information and no real value as well**."*

A FortyGuard engineer saying, to the entrants, that emitting a raw number **is a failure**.
This is the closest thing in 33,500 words to the quote you thought you had, and it is
better — it condemns exactly the output a wrong-layer query produces. **Lead with this.**

### Q2 — Aashan Javed, `03` `[00:19:07]` ★★★
> *"if you have all the information but you are not able to present it in a way where **a
> decision maker can take a decision confidently**, then obviously it's of no use."*

Almost certainly the true origin of the remembered word "confident". Use it for what it
actually says: the test is whether a supervisor can act, not whether the data was fetched.

### Q3 — Fawad Shah, `02-temperature-api` `[00:44:14]` ★★★
> *"we're living in a world I think it's **more easy to build something and more difficult
> to understand the problem**. So I would assume that whatever you're building, try to
> understand what you're building, then go towards the development."*

FortyGuard's engineering lead, closing the agentic segment. Pairs perfectly with a judge's
"The Builder's Trap" talk and with a project whose core IP is a decision table.

### Q4 — Fawad Shah, `02` `[00:24:47]` + `[00:25:05]` ★★ — the technical spine
> *"**exceedance** is something like for how many hours a certain value was above the
> threshold. […] And for **persistence**, it's quite similar but it gives you a continuous
> long run. Like for example, continuously it stayed above 35 for six hours, seven hours."*

Use when explaining *why* the layer choice matters — in his words, from the API's own docs
walkthrough.

### Q5 — Fawad Shah, `02` `[00:36:14]` + `[00:37:16]` ★★★ — the inversion, in his numbers
> *"the hottest to coolest parcel, that's like **0.7 degrees Celsius**"* … *"for **more than
> 19 hours**, it stayed above and then for **five hours straight**, it was above the threshold."*

Not rhetoric — his own client case study. Peak says the six sites are identical; duration
says they are not. **This is the strongest single artefact found. Build the demo on it.**

### Runners-up
- Jay Sadiq, `01` `[00:10:26]`: *"we don't just wanna build another demo. We don't just wanna build another MVP. What we really wanna build is something that the world cannot afford to ignore."*
- Jay Sadiq, `01` `[00:13:05]`: *"if you think your solution can **protect one asset or at least add a one operational layer** to our community"* — near-verbatim HeatGuard framing, from the CEO.
- Snehil Ahuja, `01` `[00:38:57]`: *"build something like **a real client would use** and aim for impact."*
- Aashan, `03` `[00:10:01]`: *"if you do great engineering, but your product doesn't answer a commercial question, it doesn't show value clearly […] then it will be of less use."*

---

## 7. 🚨 CONTRADICTIONS — flagged, not reconciled

| # | Believed | Transcript says | Severity |
|---|---|---|---|
| 1 | Fawad said *"picking the wrong analysis layer will give you a confident wrong answer"* | **Never said. By anyone. In any session.** | 🔴 **Critical** — would have been quoted to its own author |
| 2 | The wrong layer = `filter_type` | The layer selector is **`analytic_type`**; `filter_type` is the time window | 🔴 Critical — thesis mechanism |
| 3 | AOI ≤ ~130 km² / 50 mi² | *"the limit is about **15 miles square**"* `02` `[00:23:53]` | 🔴 High — 3.4×, sizes every demo AOI |
| 4 | Session 2 had a "parts that trip people up" segment | **No such segment.** Session over-ran; he apologises three times | 🟠 Medium — expectation deleted |
| 5 | Judging = 40 / 35 / 15 / 10 | **Only 40% and 10% are ever spoken.** 35% and 15% have no source in any transcript | 🟠 Medium — don't cite as fact |
| 6 | Written summary max 500 words | **No word limit stated anywhere in 33,500 words.** Source unknown | 🟠 Medium — keep as safe ceiling, not a rule |
| 7 | Failed tasks cost nothing → probe freely | True for *task failure*, but a **non-US AOI *"is just going to spend your credit"*** `[00:13:39]` | 🟠 Medium — guard before the call |
| 8 | Deadline Aug 30, effective Aug 29 | Still true — but **live link must survive to 16 Sept**, and **API key is revoked on the 16th** | 🟠 Medium — new operational requirement |
| 9 | Innovation is a risk area (15%, "don't add surface") | Innovation is scored partly as **combining tracks** — Track 4 × Track 6 *earns* the mark | 🟡 Low — reframes, doesn't contradict |
| 10 | `filter_type=5` unverified (vendor client omits it) | Fawad **enumerates all five** including *"a single month"* `[00:19:39]` | 🟡 Low — still probe |
| 11 | Overlapping FortyGuard's roadmap is a strategic risk | *"Go ahead, clash it with our products […] you won't be penalized for it"* `[00:53:14]` | 🟢 Resolved in our favour |

---

## 8. Still unknown after 33,500 words

- **The real AOI ceiling.** 15 mi² vs 50 mi², unresolved. Probe first.
- **Technical execution = 35%, Innovation = 15%.** Unsourced. May come from a handbook page not in this pack.
- **The 500-word summary limit.** Unsourced.
- **Where to submit.** No portal was ever announced — *"We will be sharing a link with you guys near the submission date"* `02` `[00:55:36]`.
- **The seven track names.** Never read aloud; they live at `fortyguard.com/hackathon26`.
- **Whether "comfort analysis" is an API-native comfort-hours metric** (C3) or demo-side computation. Material to differentiation.
- **Whether an inversion day exists in Phoenix specifically.** Fawad's case study proves the *pattern* exists in their data; it is not Phoenix and not our sites.
- **How each constraint actually fails.** Only non-US has even a hint, and that hint is "silently, and you pay."
