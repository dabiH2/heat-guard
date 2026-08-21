# Webinar insights — from the raw transcripts

Replaces every abstract-derived note about sessions 2, 3 and 4. Everything below is from
the Whisper transcripts in `../../`, with `[HH:MM:SS]` pointers into the `.mp4`s.

**Whisper reliability:** proper nouns and numbers are unreliable. "FortyGuard" is
transcribed at least nine ways across the four files (*40 guards, Forte Guard, Fort Guard,
4E Guard, 4reguard.com, FortiGuard, Fortygarde, 40 cars, Fodegaard's*). Every figure below
is quoted as spoken and marked where it is hedged or garbled. Nothing here is silently
corrected.

**⚠ Speaker names in this document are NOT transcript-sourced.** They come from the file
manifest. The transcripts never spell any of them correctly:
- **Snehil Ahuja** → *Snehal* (×5), *Sneha* (×4), *Sinhaal*, *Steve*, *Nino*, and at
  `01` `[00:14:30]` **"The way *Jesus* described the temperature API"**
- **Fawad Shah** → *Fawada*, *Fawar*, and at `01` `[00:38:32]` **"Pawaj Shah"**
- **Aashan Javed** → *Ashon*, *Shahan*
- **Ahmed Abdelkhalek** → his own self-introduction transcribes as **"My name is Ahmed
  Abdul-Khalib"** `05` `[00:04:47]`; host says *"Ahmad"*. The spelling *Abdelkhalek* exists
  **only in the file's title header**, which is typed metadata, not audio.
- **Tarek Fouad** → the surname **never appears in the spoken transcript at all**. Body has
  only *"Tarek"*, plus *"starik"* `06` `[00:40:36]` and *"tico tarq"* `06` `[00:48:32]`.
  *Fouad* is header metadata only.

Same for the companies in session 6: the transcript says **"Sherouk"** (`[00:03:18]`, likely
*Shorooq*), **"Shera in Sharjah"** (`[00:03:51]`, likely *Sheraa*), **"Mozin"** (`[00:03:57]`,
likely *Mozn*), **"Hub 71"** (`[00:03:38]`, styled *Hub71*). None of the corrected spellings
appear anywhere in the audio.

So an attribution like "Fawad Shah, Software Engineering Lead" is a *reconciliation*, not a
quote. It is almost certainly right — `01` `[00:38:30]` introduces "our software
engineering lead" immediately before session 2, and `02` `[00:08:23]` confirms the role —
but **confirm the spelling from Slack or LinkedIn before putting a name on screen in the
video.** Misspelling a judge's colleague on camera is a cheap, avoidable own goal.

**Timestamp convention:** timestamps point at the cue where the quoted words *begin*.
Multi-cue quotes are given as a range. These were re-verified against the `.srt`s after
first draft; an earlier pass was consistently 3–18 s early. Sessions 5 and 6 were re-verified
the same way on 21 Aug — that pass found one **content** error ("genuinely" for "generally",
§9) and eleven anchor errors, all now corrected.

**⚠ Garbles are quoted literally — do not "fix" them downstream.** Several Whisper renderings
below are almost certainly wrong words, and are kept as-is on purpose. Where the intended word
is near-certain it appears in `[brackets]`. The known set:

| Transcript says | Almost certainly | Where |
|---|---|---|
| "programmatic **card rate**" | guardrail | `05` `[00:12:54]` |
| "**Regrics** versus LLMs" | regex | `05` `[00:25:48]` |
| "Second is **paint**" | pain | `05` `[00:27:07]` |
| "earn **high** points" | *possibly* hype points | `05` `[00:27:20]` |
| "the **T same**" | `tcm` | `02` `[00:24:35]` |
| "pitching to current **stores**" | stories | `06` `[00:36:39]` |
| "don't announce **me** it's better" | "don't announce, it's better" | `06` `[00:34:30]` |
| "emotions are the only **place**" | *possibly* the only way | `06` `[00:48:17]` |

Paraphrasing any of these into the corrected word and presenting it as a quote invents text
the source does not contain. Quote literally, gloss in brackets, say the clean word aloud.

Sessions in descending value:

| # | File | Session | Speaker | Verdict |
|---|---|---|---|---|
| **5** | `05-builders-trap` | **The Builder's Trap** | **Ahmed Abdelkhalek** ("A.K."), Google Cloud — **MENTOR & JUDGE** | 🟢🟢 **Highest. A judge publishing his own rubric.** |
| 2 | `02-temperature-api` | Building on the Temperature API | **Fawad Shah**, Software Engineering Lead | 🟢 High — rewrites the thesis |
| 3 | `03-heat-intelligence-cloud` | Heat Intelligence Cloud | **Aashan Javed**, AI/ML Engineer | 🟢 High — territory map + best quotes |
| **6** | `06-pr-and-media` | **From Headlines to Impact: PR & Media** | **Tarek Fouad**, Narrative One | 🟢 High — owns the 10% Communication mark |
| 1 | `01-kickoff` | Onboarding & Kickoff | **Jay Sadiq** (CEO), **Snehil Ahuja** (Product Lead) | 🟡 Medium — rules, judging, mechanics |
| 4 | `04-autodesk-forma` | Breaking Silos with Autodesk | **Jordana Rosa**, Autodesk | 🔴 **Zero value. Do not rewatch.** |

Sessions 5 and 6 added 2026-08-21. Session 5 is the single most consequential session of the
six: it is a judge stating, on camera, what he filters for — and what he filters for is the
architecture HeatGuard already has.

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
| **`[00:53:19]`–`[00:53:28]`** | "clash with our products, it's fine" | Removes the competitive-overlap worry. ~25 s. |

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

**Closing line, and the best quotable from this session** `[00:44:18]`:
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

And the one piece of bad-data guidance is the **opposite** of refusal, `[00:36:10]`:
> *"the strategy to handle missing data is really simple. If you find some inconsistencies,
> you can rely on **interpolation** approaches. […] So you can interpolate it."*

⚠ **Use this carefully.** FortyGuard's stated default is *fill the gap and answer anyway*.
HeatGuard's refusal is the direct antithesis — which is genuine differentiation, but it is
a position the mentors have **not** endorsed. Argue *why* refusal beats interpolation for a
safety-critical decision; do not assume the judges already agree.

### And the release valve

`02-temperature-api` `[00:53:19]`: ***"Go ahead, clash it with our products. It's fine.
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
**API access is revoked when judging ends on the 16th** (`02` `[00:59:31]`, `[00:57:16]`).

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

## 9. Session 5 — The Builder's Trap (Ahmed Abdelkhalek, Google Cloud) 🟢🟢 **A JUDGE**

*Added 2026-08-21. Numbered 9 to preserve the append-only ordering; read it first.*

**Who.** Ahmed Abdelkhalek, goes by **A.K.** `[00:04:47]`. Leads the startups & VC ecosystem
for **Google Cloud** across the UAE and North African Levant `[00:04:52]`. Whisper renders
him *"Ahmed Abdul-Khalib"*; the host says *"Ahmad"*. **Judge, not just mentor** — stated in
the file title and confirmed by the host at `[00:58:14]`–`[00:58:20]`: *"Ahmed right here is
**a judge** again in the hackathon itself. He's not just a mentor."*

Context worth knowing: **FortyGuard is itself in the Google for Startups programme**, and
**Jay Sadiq is a Google-appointed mentor for it** `[00:42:44]`–`[00:42:51]`. This judge is
not a neutral outsider; he is close to the company. Whisper: *"Jay Sardik"*.

### Rewatch these two segments

| TS | What | Why |
|---|---|---|
| **`[00:12:46]`–`[00:13:55]`** | The problem formula | The sentence he says you must fill before writing a line of code. ~1 min. |
| **`[00:26:11]`–`[00:27:34]`** | The 4-point checklist | His stated "one takeaway". This is a rubric. ~1.5 min. |

### 🎯 The thesis of the talk

**The trap is over-engineering.** `[00:05:02]`: *"The trap is over-engineering and we'll
discuss how to focus on real problems to secure your first-paying customer."*
`[00:07:00]`: *"you're basically built a **monument** over engineering, but not the actual
product that is required in the market."*
`[00:05:42]`: *"You can build the most beautiful code as much as you can, the most efficient
code. But it loses its impact if it doesn't solve and touch the business perspective with a
business problem."*

**Fall in love with the problem, not the tech.** `[00:08:36]`: *"you have to fall in love
with the problem. We all are in love with the tech. In every single era, there's a new piece
of tech that we fall in love with."*
`[00:07:48]`: *"we always start thinking about the solution before dreaming of the problem
statement."*
`[00:10:31]`: *"We forget to ask ourselves a question of **who's hurting and what causes
their pain**."*

### ⭐ The problem formula — `[00:12:46]`–`[00:13:55]`

> `[00:12:54]`–`[00:13:03]` *"That formula is what acts as your programmatic [guardrail]. **If you cannot
> fill out every variable cleanly, then we're not really ready to write a single line of
> code.** It's a simple one: **Specific user group struggles to perform a specific task
> because of this core obstacle, which results in measurable negative outcome.**"*

Four variables: stakeholder · task · obstacle · measurable outcome. Note **"measurable"** —
it echoes the handbook's demand for a measurable result and the *"−7 °F on this route"*
example. Our equivalent number is hours-above-threshold, not degrees.

### ⭐⭐ The 4-point checklist — `[00:26:11]`–`[00:27:34]`

He frames it as *"15 minutes before you build anything"* `[00:26:11]` and *"one takeaway is
this checklist. So run every feature or project idea through this. If it passes, you have a
lean targeted path forward to prove your hypothesis"* `[00:26:44]`.

1. **Hero** `[00:26:58]` — *"Who's the hero? Name the exact person, role, industry, who will actually use this."*
2. **Pain** `[00:27:07]` — *"What is the manual, slow or expensive thing they're doing right now."*
3. **AI justification** `[00:27:14]` — *"Is AI **generally** required to solve this? Or are we just using it to earn high points at the expense of latency and cost?"*
4. **Kill switch** `[00:27:20]` — *"What is the absolute simplest version of this product we can build to prove our hypothesis within the next 24 hours."*

**A judge published his filter. Answer all four explicitly.** See `CLAUDE.md` for HeatGuard's answers.

### ✅✅ Deterministic code, endorsed — the strategic headline

`[00:25:05]`–`[00:25:19]`:
> *"please be responsible with your resource budget. There's nothing free in the world.
> **Traditional deterministic code is faster, cheaper and entirely predictable.**"*

`[00:21:28]`:
> *"you need to **evaluate AI choices critically**, ensuring that we're **not introducing
> unnecessary latency and cost just for the hype**."*

`[00:23:05]`–`[00:23:36]`:
> *"AI can solve everything, in fact, to some extent. But **should** it be actually used to
> solve everything? And the follow-up question is **at what cost?** […] It's incredibly
> powerful. But it's not a silver bullet for everything. **It could, but should it?**"*

`[00:25:48]`–`[00:25:55]`: *"[Regex] versus LLMs, cognitive reasoning, autonomous action. You
know, it depends. Again, there's always the **quality to cost balance**."* (Whisper: *"Regrics"*.)

His worked example `[00:21:58]`–`[00:22:57]`: someone asked whether Gemini could resize
images at scale. `[00:22:36]` *"The question is, **why do you want AI to do that?**"* … `[00:22:41]`
*"Like, sure, yes, you can. **But should you? How much money is it going to cost you?**"* …
`[00:22:50]` *"Versus, you know, writing a couple of lines of a Python script."*

**Read that against HeatGuard's architecture rule.** The rule said constraining the LLM
"reads as maturity to a Google/NVIDIA panel" — that was a guess. The Google panelist says
it himself. `router.py` is not a defensive choice to be justified; it is the answer to his
checklist item 3.

### Scale, MVPs and iteration

- **Scale is not your problem yet.** `[00:14:36]`: *"Scale is a high-class problem to have later, not now. You don't have to build for 10 million users from day one because if you start building for 10 million users from day one, **the problem that you're solving becomes scale**, not the actual problem."* `[00:15:30]`: *"Stakeholder is 10 million users. **Today you have zero. You're solving the wrong problem at the wrong time.**"*
- **Validation over infrastructure.** `[00:15:49]`: *"your tech stack needs to **prioritize validation over perfect infrastructure**."*
- **MVP → MLP.** `[00:30:39]`: *"typically, people are used to MVPs, minimal viable products. From now on, we're going to use from an idea to a **minimum lovable product**."* `[00:16:26]`: to build the most lovable product *"you need to be aware of the problem, the stakeholder, the obstacle, and the measurable negative outcome."*
- **Optimise for learning speed.** `[00:17:00]`: *"Do not hesitate to use **unscalable manual processes** to test hypothesis quickly. Speed to market and speed of learning are everything."* `[00:20:00]`: *"you'd need to **optimize your product to learn speed, don't perfect it from day one**."*
- **Not UI, not the database.** `[00:21:00]`: *"you're not building, you know, because you're using the best database, your product is not successful because **it uses, it has** the best UI UX. **Because it solves a problem, very simply.**"*

### His three Google examples — all usable as framing

| Example | TS | Point |
|---|---|---|
| **Google Classroom** | `[00:11:03]`–`[00:12:30]` | The product team *"were students, parents, and teachers"* `[00:11:44]` — the people with the problem. Know your three stakeholder groups and what each one's problem is. ⚠ **He contradicts himself 30 s later**: at `[00:12:13]`–`[00:12:25]` the three stakeholders become students, teachers, and *"staff and administrators"* — parents drop out. Don't cite "parents" as a fixed fact; cite the principle. |
| **Google Cardboard** | `[00:17:14]`–`[00:19:47]` | Everyone else built $1–2k headsets; Google folded a piece of cardboard around a phone. *"you didn't spend time building hardware and iterations and a lot of investments in order to go to market."* Cheap validation beats expensive perfection. |
| **google.com** | `[00:55:19]`–`[00:56:33]` | *"**Before AI mode came to Google**, you land on Google.com, you land on a white page. It's a white screen with one box, very basic, nothing fancy, very simple. **But the engineering behind that one box is the problem that you're trying to solve for.**"* ⭐ This is the best available description of HeatGuard's own shape: a plain interface over a hard decision. |

### Q&A — the one that touches our build

**Q: "If our agent uses multiple APIs or LLM services, how should we manage failures when
one API becomes unavailable or reaches its rate limit?"** (asked by "Gopi", named at `[00:51:14]` — he adds *"if I'm pronouncing the name correctly"*) `[00:51:01]`

His answer `[00:51:29]`–`[00:52:48]` is thin on mechanics — *"there's a bunch of ways you can
do that in terms of fallbacks […] it's not things that are unheard of"* — and then pivots to
the characteristic move:

> `[00:52:39]` *"when someone comes and asks me that, I always again, the boring
> question,"* … `[00:52:44]` *"**why are you getting into those limits? What are you trying to
> do?** What is it that you're building? Is there a different way where you can approach the
> solution for that?"*

Also `[00:52:09]`: *"there's **no AI without API**."* And `[00:53:27]` on efficiency: *"how do
you rely less on GPUs and more on CPUs back to the old days? How do you build efficient LLMs
that can actually run and do the same thing on CPUs?"*

**Read this as a warning.** If the demo hammers the API, this judge's first question is not
"how did you handle the retry" — it is "why are you making that many calls at all?" Our
fixture cache and 3→6→12 backoff answer him, and the `data/fixtures/` convention should be
mentioned out loud rather than left in the repo.

Two more Q&A items, lower value:
- **Facebook/monetisation** `[00:43:34]`–`[00:47:49]`: *"don't worry about making money out of the product until you figure out whether this is the real problem statement."*
- **What makes a product win — UI or performance?** `[00:55:19]`: *"boring answer. Here's the problem that you're solving."*

### The Google for Startups Cloud Program (second half — not hackathon-relevant, recorded for completeness)

Two tiers `[00:29:23]`: **start** (pre-funding) and **scale** (pre-seed → Series A).
- start: **$2,000** credits year 1 `[00:36:01]`. His point: that is plenty — *"have a single virtual machine, Linux, open source databases […] **that shouldn't cost you more than $70 a month**"* `[00:37:14]`.
- scale: up to **$100,000** year 1, plus 20% of usage up to another $100k in year 2 `[00:38:11]`–`[00:38:19]`.
- **AI-first + institutionally funded: $250,000** year 1 `[00:39:41]`.
- Four pillars: financial, technical, business, community `[00:31:37]`. He volunteers that **financial is his least favourite and business his most** `[00:32:40]`: *"any credits that you get on any platform, they're not forever. But any relationship you build through the business side will last forever."*

---

## 10. Session 6 — PR & Media (Tarek Fouad, Narrative One) 🟢

*Added 2026-08-21. This session owns the **10% Communication** mark and the 3-minute video —
the one artefact organisers said judges will **100%** open.*

**Who.** Tarek Fouad, founder/CEO of **Narrative One**, a comms partner for investment firms
and tech founders across MENA. Previously CCO at **Shorooq** (Whisper: *"Sherouk"*),
founding team at **Hub71** Abu Dhabi, built **Sheraa** in Sharjah (Whisper: *"Shera"*).

The host ties it to the submission explicitly `[00:57:34]`–`[00:58:19]`:
> *"building something great is only half the battle […] when you submit you've got a demo,
> you've got a three minute video that you need to submit, you have a description that you
> need to write to make your work land in front of the judges and **that's the storytelling
> part** […] the way you **frame the problem, show the impact and make people care** […]
> that's what turns a good project into one that stands out to the judges."*

### ⭐ The line to run the whole submission on — `[00:38:25]`–`[00:39:06]`

> *"remember **you don't need to be loud you need to be clear**. **Clarity beats creativity
> anytime.** I see a lot of founders investing time on building great decks, they look
> amazing, their social media looks amazing, the graphics is so inspirational and
> motivational, but reality is you look at what they're trying to say and **it's not clear**
> […] you don't have to look loud, you don't have to look impressive, **you have to be
> clear**."*

For a project whose headline feature is *the system sometimes refuses to answer*, "clear over
impressive" is not a stylistic preference — it is the pitch.

### The attention math — `[00:26:35]`–`[00:27:34]`

> *"The headline unfortunately is what **90% of the time** what people will read. **10%** will
> read the body. **2%** will most likely understand the key messages out of it."*
> *"if you're going to invest in a press release make sure that you **invest 80% of your time
> on the headline** and then the other 20% on crafting a great story […] because guess what,
> the 2% that read it and will understand the key messages from it are **the most important
> people that you will need**."*

**Applied:** the first sentence of the 500-word summary and the first ten seconds of the video
carry almost all the weight. Spend disproportionate time there. Everything about the router,
the fixtures and the backoff belongs in the 20%.

### Lead with the *why*, never the title — `[00:41:56]`–`[00:44:21]`

> `[00:41:56]` *"unfortunately a lot of us go into 'oh, I'm a founder of X Y and Z, I do this
> and that' […] while it's true, you certainly have **missed inspiring them**."*
> `[00:42:47]` ***"start with something that they will remember and most likely that is your why."***
> `[00:43:21]` *"**iterate on it until it becomes 'well that's intriguing, tell me more'**."*

His own worked examples of the form: *"I'm helping governments or organizations plan for the
next urban development by…"* `[00:43:01]`; *"I'm a founder that helps energy companies figure
out where the next oil rig location is"* `[00:43:33]`.

**Applied — the opening line is not "HeatGuard is an agentic heat-safety tool."** It is
closer to: *"I'm trying to stop crews being sent out on the days that look safe."*

### ⭐⭐ He builds a temperature-product story angle, live — `[00:36:39]`–`[00:37:49]`

Genuinely uncanny: his improvised worked example is a temperature-monitoring product.

> *"if you're building the next app or product towards **temperature monitoring** for example,
> **why is it important today? what's happening around us today? what is the media talking
> about today?** […] can you craft a story about what's happening around them and the effect
> of what's happening on temperature […] and then because it's affecting temperature, **if we
> don't monitor temperature there's a big issue here** […] but **there are no tools out there
> monitoring temperature — then that becomes your story angle.** All of a sudden the story is
> far more than just fundraising."*

The reusable chain: **something people already care about → its link to temperature → what
breaks if temperature is measured wrongly → therefore you need this → nothing existing does
it → that's the angle.** For HeatGuard the middle link is the strong one: *heat deaths happen
on days that don't look dangerous.*

### Trust, flaws and numbers — directly usable for the refusal feature

**Flaws are survivable; hype is not.** `[00:25:30]`–`[00:26:10]`:
> *"the currency in communications, PR, media, even your pitch decks that you're going to
> design and even the products that you're going to end up designing **is trust**. **You might
> have some flaws. The product might have issues and bugs**, but at the end, at a level, **I
> need to feel I can trust you** and the trust element is very important to come out every
> single time."*

**Don't make a claim you can't put a number on.** `[00:34:10]`–`[00:34:43]`:
> *"it's quite difficult to put a fundraising announcement without numbers. **You might get
> some pick up from the media but it becomes fluff.** Then it's not a fundraising announcement
> if you're not going to give me a number […] then you know what **don't announce me it's
> better** […] put a number even if it's small, it doesn't matter. What matters is the story
> behind the why."*
>
> *(Literal: "don't announce me it's better" — Whisper. Keep the concession clause; deleting
> it hardens his position beyond what he said.)*

**These two together are the argument for refusal as a feature.** A tool that declines to
answer rather than emitting an unbacked number is doing exactly what he tells founders to do.
Frame refusal as *the visible evidence of trustworthiness*, not as a missing capability.

### Don't sound like a machine — corroborates the kickoff's "we don't want AI"

`[00:24:09]`–`[00:24:50]`:
> *"saying something like 'we're thrilled to freaking announce. We are changing how the world
> is going to look at us. This is the next AI', you name it, and throw in all the buzzwords
> […] **It lacks your natural voice. Nobody speaks like this.** You need to put your natural
> voice out."*

`[00:25:04]`–`[00:25:24]`:
> *"AI is a great productivity tool, but if you're not going to train it to be voiced like you
> and to write like you […] then chances are"* `[00:25:19]` *"**you will look like a machine and
> you'll sound like a machine**."*

`[00:48:17]`: *"it's quite important to **put faces out** because **emotions are the only place
I can build trust around. No AI can do that.**"*

This independently reinforces `01-kickoff` `[00:50:58]`–`[00:51:07]` (*"We want a raw video
technically […] We don't want AI"*). **Two separate mentors, same instruction: present it
yourself, in your own voice, on camera.** Treat that as settled.

### Press-release framework — `[00:29:09]`–`[00:32:40]`

Lower relevance (we are not issuing a press release), but the *ordering* maps onto the 500-word summary:

1. Strong headline `[00:29:09]`
2. Sub-headline that **adds context, doesn't repeat the headline** — carrying *"one very important key message that you want the media and the people to remember"* `[00:29:17]`
3. **The news, straightforward** `[00:29:33]`
4. What you do / what market / what challenges you solve `[00:29:46]`
5. **Quotes** — *"a press release is not a press release without quotes"* `[00:29:59]`
6. **What's next** — *"the piece that I see a lot of press releases not covering enough"* `[00:30:37]`

Note (5): our quotes are Fawad's and Aashan's, already collected in §6.

### Other applicable do/don'ts

- `[00:33:26]` Ask the reader's question: *"why should I care, what's in it for me? Start asking this question."*
- `[00:35:58]` *"pitching the right beats and the right stories to the right people in the right time."*
- `[00:22:19]` *"please do invest in taking professional pictures. Don't send media your Instagram picture."* → applies to the demo's visual quality.
- `[00:39:42]` Don't fixate on one platform / outlet.
- `[00:20:22]` *"if you don't invest in putting the story out, nobody will find you, but **also just winging it is the same result**."*

### Not in this session

Nothing on video length, camera setup, on-camera delivery mechanics, or written-summary word
limits. The 3-minute video and description are raised only by the host at the close. **The
500-word limit remains unsourced across all six sessions.**

---

## 6. ⭐ QUOTABLE LINES — verified verbatim

Ranked by usefulness for the README and the 3-minute video. **All are real. The one you were
planning to use is not.**

> **Q0 supersedes Q1 as the lead quote (added 2026-08-21).** Q1–Q5 below are FortyGuard
> engineers. Q0 is **a judge**, and it endorses the architecture rather than the metric.

### Q0 — Ahmed Abdelkhalek, Google Cloud, **JUDGE**, `05-builders-trap` `[00:23:05]`–`[00:23:36]` ★★★★ **LEAD WITH THIS**
> *"AI can solve everything, in fact, to some extent. But **should** it be actually used to
> solve everything? And the follow-up question is **at what cost?** […] It's incredibly
> powerful. But it's not a silver bullet for everything. **It could, but should it?**"*

Paired with `[00:25:12]`: *"**Traditional deterministic code is faster, cheaper and entirely
predictable.**"*

A judge on the panel, from Google Cloud, stating the exact principle `router.py` is built on.
Quoting him back — by name, on his own checklist item — is stronger than any FortyGuard quote,
because it answers *"is AI generally required?"* before it is asked.

### Q0b — Ahmed Abdelkhalek, `05` `[00:55:56]`–`[00:56:24]` ★★★ — the shape of the product
> *"It's as simple as possible as Google.com. **Before AI mode came to Google**, you land on
> Google.com, you land on a white page. It's a white screen with one box, very basic, nothing
> fancy, very simple. **But the engineering behind that one box is the problem that you're
> trying to solve for.**"*

The best one-line description of HeatGuard available: a plain surface over a hard decision.

### Q0c — Tarek Fouad, `06-pr-and-media` `[00:38:25]`–`[00:38:41]` ★★★ — the delivery rule
> *"remember **you don't need to be loud you need to be clear. Clarity beats creativity
> anytime.**"*



### Q1 — Aashan Javed, `03-heat-intelligence-cloud` `[00:22:50]`–`[00:22:59]` ★★★ BEST
> *"So you can make good use of it as well by combining it or thinking about creative ways,
> **or you can just directly use that information and state pla[i]ne temperatures as well,
> pla[i]ne AQI values as well, which gives no real information and no real value as well**."*

A FortyGuard engineer saying, to the entrants, that emitting a raw number **is a failure**.
This is the closest thing in 33,500 words to the quote you thought you had, and it is
better — it condemns exactly the output a wrong-layer query produces. **Lead with this.**

⚠ **Two fidelity notes before you quote it.** Whisper writes **"plane"**, not "plain",
both times — "plain" is an editorial reading, near-certain but still a reading; say
*"plain"* aloud and don't put brackets on screen. And keep the **"or you can just"**
lead-in: the full sentence is a caution about *how you use* the data (combine it, or
dump it raw and get nothing), not a blanket verdict that the data is worthless. Quoting
from "which gives no real information" alone would misrepresent him.

### Q2 — Aashan Javed, `03` `[00:19:07]` ★★★
> *"if you have all the information but you are not able to present it in a way where **a
> decision maker can take a decision confidently**, then obviously it's of no use."*

Almost certainly the true origin of the remembered word "confident". Use it for what it
actually says: the test is whether a supervisor can act, not whether the data was fetched.

### Q3 — Fawad Shah, `02-temperature-api` `[00:44:18]` ★★★
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
| 3 | AOI ≤ ~130 km² / 50 mi² | *"the limit is about **15 miles square**"* `02` `[00:23:58]` | 🔴 High — 3.4×, sizes every demo AOI |
| 4 | Session 2 had a "parts that trip people up" segment | **No such segment.** Session over-ran; he apologises three times | 🟠 Medium — expectation deleted |
| 5 | Judging = 40 / 35 / 15 / 10 | **Only 40% and 10% are ever spoken.** 35% and 15% have no source in any transcript | 🟠 Medium — don't cite as fact |
| 6 | Written summary max 500 words | **No word limit stated anywhere in 33,500 words.** Source unknown | 🟠 Medium — keep as safe ceiling, not a rule |
| 7 | Failed tasks cost nothing → probe freely | True for *task failure*, but a **non-US AOI *"is just going to spend your credit"*** `[00:13:39]` | 🟠 Medium — guard before the call |
| 8 | Deadline Aug 30, effective Aug 29 | Still true — but **live link must survive to 16 Sept**, and **API key is revoked on the 16th** | 🟠 Medium — new operational requirement |
| 9 | Innovation is a risk area (15%, "don't add surface") | Innovation is scored partly as **combining tracks** — Track 4 × Track 6 *earns* the mark | 🟡 Low — reframes, doesn't contradict |
| 10 | `filter_type=5` unverified (vendor client omits it) | Fawad **enumerates all five** including *"a single month"* `[00:19:39]` | 🟡 Low — still probe |
| 11 | Overlapping FortyGuard's roadmap is a strategic risk | *"Go ahead, clash it with our products […] you won't be penalized for it"* `[00:53:19]`–`[00:53:28]` | 🟢 Resolved in our favour |
| 12 | *(added 21 Aug)* Constraining the LLM "**reads as** maturity to a Google/NVIDIA panel" — an assumption | The Google judge says it outright: *"**Traditional deterministic code is faster, cheaper and entirely predictable**"* `05` `[00:25:12]`, and asks *"Is AI generally required to solve this?"* `05` `[00:27:14]` | 🟢 **Resolved emphatically in our favour.** Not a contradiction — an assumption promoted to fact. |
| 13 | *(added 21 Aug)* Kickoff: *"We don't want an MVP. We want something which is usable right now"* `01` `[00:34:58]` | Judge: *"What is the **absolute simplest version** of this product we can build to prove our hypothesis **within the next 24 hours**"* `05` `[00:27:20]`, and *"prioritize validation over perfect infrastructure"* `[00:15:49]` | 🟠 **Genuine tension.** Organisers want *live and usable*; the judge wants *minimal and problem-shaped*. Resolution: **narrow scope, fully working** — not broad scope, half working. This is an argument for the existing scope-discipline table, not against it. |
| 14 | *(added 21 Aug)* MVP is the target | Judge replaces it: *"people are used to MVPs, minimal viable products. From now on we're going to use from an idea to a **minimum lovable product**"* `05` `[00:30:39]` | 🟡 Low — vocabulary. Use "lovable" framing if the word comes up; don't force it. |

---

## 8. Still unknown after 49,900 words (six sessions)

- **The real AOI ceiling.** 15 mi² vs 50 mi², unresolved. Probe first.
- **Technical execution = 35%, Innovation = 15%.** Unsourced. May come from a handbook page not in this pack.
- **The 500-word summary limit.** Unsourced.
- **Where to submit.** No portal was ever announced — *"We will be sharing a link with you guys near the submission date"* `02` `[00:55:36]`.
- **The seven track names.** Never read aloud; they live at `fortyguard.com/hackathon26`.
- **Whether "comfort analysis" is an API-native comfort-hours metric** (C3) or demo-side computation. Material to differentiation.
- **Whether an inversion day exists in Phoenix specifically.** Fawad's case study proves the *pattern* exists in their data; it is not Phoenix and not our sites.
- **How each constraint actually fails.** Only non-US has even a hint, and that hint is "silently, and you pay."

*Re-checked against sessions 5 and 6 (21 Aug) — none of the above were resolved. Sessions 5
and 6 are strategy and communication; neither touches the API. Two items got worse:*
- **The 500-word summary limit is now unsourced across all six sessions**, including the one
  session explicitly about how to write the submission description. If it were a real rule,
  session 6 was where it would have been said. Treat it as a self-imposed ceiling.
- **The 35% / 15% weights are still unsourced across all six sessions.** Two judges' sessions
  have now passed without either number being stated.

*New unknowns from sessions 5 and 6:*
- **How many judges there are and who else is on the panel.** We now know one by name (Ahmed
  Abdelkhalek, Google Cloud). `01-kickoff` said judges were still being added.
- **Whether Ahmed's 4-point checklist is his personal filter or a shared scoring instrument.**
  He presents it as advice; the host presents him as a judge. Answering all four costs nothing
  either way — but do not claim in the submission that it *is* the rubric.
- **Whether Tarek's deck was ever circulated.** He offers it at `06` `[00:40:28]`: *"I'll drop
  this deck to [Snehil] afterwards for you guys."* Worth checking Slack `#announcements`.
