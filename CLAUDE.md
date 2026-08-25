# HeatGuard — project context for Claude Code

Read this first, every session. It is the verified ground truth; do not re-derive it.

## What this is

Solo entry for **FortyGuard Hackathon'26**, Track 4 (Government & Environment) × Track 6 (Agentic).

An outdoor-worker heat-safety agent for Phoenix job sites. It classifies each question against a decision table **before** calling the API, states which temperature analysis layer it chose and why, and **refuses** when the data cannot answer the question.

**Owner:** Gabriele Desimini · **Effective deadline: Aug 29 2026** (official is Aug 30 23:59 GST = 21:59 Rome, but connectivity is lost from Aug 30).

Strategy, rubric and rationale live one level up in `../08-spec-p3.md` and `../09-implementation-plan.md`. Read them once at the start of a session.

## The thesis

> **CORRECTED 2026-08-20 from the raw webinar transcripts. Read this whole section before quoting anyone.**

**The quote below is NOT real. Do not use it. It appears in no transcript.**
> ~~"The API is asynchronous, and picking the wrong analysis layer will give you a confident wrong answer."~~ — *not said by Fawad Shah, or anyone*

In `02-temperature-api` the word **"layer" appears zero times** and **"confident" appears zero times**. The fabrication appears to be a conflation of three real fragments:
- Fawad, `[00:18:50]`: *"these analysis endpoints are asynchronous, which means they are non-blocking."* — the async half is real.
- Fawad, `[00:42:21]`: *"the plausible temperature and everything could go wrong."* — Whisper-garbled slide read-out, no elaboration follows.
- Aashan Javed, `03-heat-intelligence-cloud` `[00:19:07]`: *"if you have all the information but you are not able to present it in a way where a decision maker can take a decision **confidently**, then obviously it's of no use."* — different speaker, different session, and about presentation, not layer choice.

**The thesis survives and gets stronger, because the real mechanism is `analytic_type`, not `filter_type`.**

`filter_type` selects the **time window** (how much data). `analytic_type` selects the **analysis layer** (what question you ask of that data). They are separate parameters and the second one is the one that silently changes the answer. Fawad, `[00:24:30]`–`[00:25:16]`:

> *"Then we have also the analytic type. So this is like basically the T same, this is just the simple snapshot. And then we have these other analysis thing like time of measure, exceedance persistence. So **exceedance** is something like for how many hours a certain value was above the threshold. […] And for **persistence**, it's quite similar but it gives you a continuous long run. Like for example, continuously it stayed above 35 for six hours, seven hours."*

So: **duration above threshold is a native API parameter, not something HeatGuard computes.** The IP cannot be "we measure duration." The IP is: *deterministically choosing `analytic_type` + `filter_type` per question, stating why, and refusing when the pair cannot answer it.*

OSHA documents outdoor-worker heat-stroke deaths at a daily maximum heat index of only **86 °F** (**30 °C** — the API takes Celsius, see below) — inside the "Caution" band. Peak temperature is a poor predictor of harm; duration above threshold is the real signal. Ask a duration question, answer it with `analytic_type=snapshot` + `filter_type=1`, and you get a plausible single temperature instead of "five straight hours above threshold" — same shape of output, opposite operational decision, **no error raised**.

**Fawad demonstrates the inversion himself, on FortyGuard's own client case study** (`[00:36:14]`–`[00:37:23]`), six parcels over 28 Jul–3 Aug:
- Ranked by **peak**: hottest-to-coolest spread is **0.7 °C** — *"South Campus edge versus the River North."* Operationally that reads as "all six sites are the same."
- Ranked by **duration**: *"for more than 19 hours, it stayed above and then for five hours straight, it was above the threshold."*

That is the demo, and it is theirs, not ours. Cite it.

## Judging

> ⚠ **"Weights are exact" was wrong.** Only **two** of the four weights are spoken in any
> recording. See **Judging — what is actually sourced** below for the verified table.
> Summary: **40% (impact) and 10% (communication) are verbatim-confirmed; 35% and 15% have
> no source in 33,500 words of transcript.** They may come from a handbook page not in this
> pack — but do not present them as quoted fact.

Handbook: *"Judges reward applied relevance over flashy demos."* A winning project needs the platform central not decorative, a clear problem and user, **a measurable outcome** (their example: "−7 °F on this route"), and a path to deployment.

## API — verified facts

Base `https://api.fortyguard.com` · header `api-key: <key>` · `Content-Type: application/json`

| Endpoint | Returns | Plan |
|---|---|---|
| `POST /v1/heatmap` | tile-by-tile thermal map over a polygon AOI | All |
| `POST /v1/env_params` | heat index, AQI, solar irradiance at a point | All |
| `POST /v1/satellite` | land-cover segmentation | Premium |
| `POST /v1/streetview` | ground-level segmentation | Premium |
| `POST /v1/heat_intelligence` | multi-dimensional analysis as a PDF | Premium |
| `POST /v1/system/fetch-api-key-usage` | plan + credit balance | All |
| `GET /v1/status/{activity_id}` | status / result of a submitted task | All |

**Async pattern:** POST → `activity_id` → poll `GET /v1/status/{activity_id}` until `succeeded`/`completed` (result in `data.result`) or `failed`/`error`. **Failed tasks cost nothing** — credits are deducted only on success, so probe freely.

**Hard constraints:**
- **US-only.** Non-US polygons error or return empty. Fawad `[00:13:14]`–`[00:13:39]`: *"this is only limited to the United States […] if you are going to set up the location to Dubai or Berlin […] I don't think it's going to work. And **it's just going to spend your credit**."* — so a non-US AOI is a *silent, billed* failure, not a clean error. Router must reject non-US before `tools.py`.
- **⚠ Dates: coverage starts ~Q4 2021, NOT 2021-01-01 — measured T8.** Probed on PHX-CHASE one date per quarter: `2021-07-15` and `2021-10-15` both returned `Completed` with **n_cells = 0** and were **billed 4,220 credits each**; `2022-01-15` onward returned 10 tiles. **The documented start date is out by about a year**, and a date inside the gap is a *silent, billed empty* — the same shape as a non-US AOI. Router refuses before `2022-01-01` (the conservative edge of the measured bracket).
- **⚠ Forward edge: "forecasts to now + 12h" is WRONG — measured T4.** The
  API accepts `start_date` up to **today + 1 day** (HTTP 400 beyond that, loud and free),
  but **tomorrow returns one flat value for the whole day** — measured 34.34 °C with
  min = avg = max, against 33.7–41.9 °C for today. No diurnal structure, so `exceedance`
  against it is exactly 0 h or exactly 24 h. Accepted ≠ answered, and it is billed.
  Router refuses past **today**: `MAX_FUTURE_DAYS_ACCEPTED=1`, `MAX_FUTURE_DAYS_USABLE=0`.
- ⚠ **A pre-2021 date fails SLOWLY** — accepted, `Processing` for >188 s, then `Failed`.
  Third failure mode: not loud, not silently wrong, just late. Free.
- **AOI: 15 mi² (~38.85 km²) stated — but NOT ENFORCED, measured T4.** A polygon scaled to **~447 km², 11.5× the stated cap, was accepted** and returned 44,690 tiles for the same flat credit cost. Fawad `[00:23:53]`: *"the limit is about 15 miles square."* The handbook said ~130 km²/50 mi². We keep **15 mi² as a self-imposed limit** — an unenforced limit is still a documented one, and tile count drives response size even when it does not drive price.
- **Max 30 days of data returned per call.** Fawad `[00:19:53]`: *"as much as 30 days worth of data."* ⚠ **Measured T4: a 61-day range returns HTTP 500 with a non-JSON body** — a server fault, not a clean rejection. The router refuses before submitting rather than relying on it.
- `granularity`: **60 / 80 / 100 m** only (HTTP 422 otherwise, loud and free). ⚠ **"Smaller costs more credits" is WRONG — measured T4: cost is flat per call regardless of tile count.** Finer granularity is free; it only costs response size. Note the data is measured at **20 m** native resolution, so 60 m is the finest the API will resample to.
- `filter_type`: **1** = single hour · **2** = hour range (+`end_time`) · **3** = entire day · **4** = day range. ⚠ **`5` DOES NOT EXIST — measured T4.** The API returns HTTP 422 `Field 'date_time.filter_type' is invalid: Input should be 1, 2, 3 or 4`. Fawad enumerates five on camera `[00:19:39]` (*"…and then we have a single month"*); the vendor client documents four. **The client was right and the transcript was wrong** — a useful calibration on which source to trust for what.
- **Rate limit: ~100 requests/minute, capped hourly, no daily cap.** Fawad `[00:56:17]`–`[00:56:31]`: *"hourly, we have put a limit to it, not the daily one […] we're limiting it to not more than I think 100 requests per minute or something. But as such, there's no other limits."* Hedged ("I think", "or something") — treat as approximate. Host adds `[00:56:44]`: *"Let's not test the rate limits and reverse engineer it."*
- **Credits: 2,000,000 per API key — confirmed live.** Plan name is literally `Hackathon`; billing period **Aug 17 – Sep 21 2026**; **key expires `2026-09-21T19:04:29Z`**, five days after judging ends.
  ⚠ **MEASURED COST: 4,220 credits per heatmap call, FLAT — per call, not per tile.** A 3-tile AOI and a 44,690-tile AOI cost exactly the same. So granularity and AOI size are effectively free and **the number of calls is the budget**: `2,000,000 / 4,220 = ~474 heatmap calls` for the whole hackathon. One demo day across 12 sites at two analytic types is 24 calls ≈ 5% of budget; a 30-day sweep of all 12 sites would be 360 calls ≈ 76%. **Budget T8's search deliberately.**
  **Failed tasks cost nothing — confirmed** (7 tasks accepted, 1 failed, exactly 6 billed: 25,320 = 6 × 4,220). **But a task that "succeeds" with an empty result IS billed** — the non-US probe returned `Completed` with zero tiles and cost 4,220.

**`analytic_type` on `/v1/heatmap` — was missing from this file, and it is load-bearing:**

| value | returns | units |
|---|---|---|
| `tcm` (default) | snapshot temperature per tile | °F |
| `time_of_measure` | UTC hour-of-day of each cell's peak | 0–23 |
| **`exceedance`** | **hours each cell spends past `threshold`** | hour |
| **`persistence`** | **longest continuous run of such hours** | hour |

The duration metric this project is built on is a first-class API product, not something
we derive. `exceedance`/`persistence` require `threshold` **and** `direction`.

This makes the layer trap *worse*, which is good for the pitch: `tcm` and `exceedance` are
the same endpoint, same `filter_type`, same AOI — one optional string apart. So the router
selects `analytic_type` too, and that is its highest-value decision.

**⚠ UNIT TRAP — `threshold` is in °C while `tcm` tiles are in °F.** Pass `threshold=91`
meaning °F and the API reads 91 °C = 195.8 °F: exceedance returns **0 hours everywhere**,
status `succeeded`, credit spent, and the tool reports "no unsafe exposure at any site".
A confidently-formatted **all-clear** — the worst wrong answer a safety tool can give.
Conversion happens in `tools.py` and nowhere else; every signature is unit-suffixed
(`threshold_c`, `heat_index_f`). A bare `threshold` must not exist in our code.

**`env_params` returns `heat_index_celsius`** (open question #4: answered — directly, but
in °C), plus `wet_bulb_temperature_celsius`, humidity, six AQI series, solar irradiance,
and 24 **local-time** timestamps. Phoenix is MST year-round, so shift windows — including
ones wrapping past midnight — map straight onto them.
- Data is measured **2 m above ground** at **20 m spatial resolution**. Do not claim 2 m spatial resolution.

**The quickstart repo ships a Python client that already does auth and submit-then-poll. Wrap it. Do not rebuild it.** It accepts `wait=False` to return the `activity_id` for agent-driven polling.

Located and vendored: **`github.com/FortyGuard-Tech/temperature-api-quickstart`** @ `f6de12d`
(MIT). Four files, unmodified, in `vendor/fortyguard/` — see `vendor/NOTICE.md`. Its bundled
sample responses are offline fixtures in `data/fixtures/vendor_samples/`, which is how
`docs/api-notes.md` got filled in before a credit was spent.

Also from the client, and not obvious: **`GET /v1/status/{id}` 404s for a short window right
after submit** — eventual consistency, not failure. A naive poller treats that 404 as an
error and discards a task that was fine.

## Scope discipline

| Tier | What |
|---|---|
| Load-bearing | `heatmap`, `env_params`, status polling |
| One addition | `satellite` — answers *why* a site is hot (land cover) |
| Stretch only | `heat_intelligence` PDF as a compliance artefact |
| Explicitly out | `streetview` — pretty, changes no decision |

A judge is literally giving a talk called *"The Builder's Trap."* Innovation is 15%; Impact is 40%. Do not add surface.

**We now have that talk. The judge is Ahmed Abdelkhalek (goes by "A.K."), Google Cloud — startups & VC ecosystem lead for UAE / North African Levant.** Host confirms `05` `[00:58:14]`–`[00:58:20]`: *"Ahmed right here is **a judge** again in the hackathon itself. He's not just a mentor."* Full extract in `docs/video-insights.md` §9.

**The trap is over-engineering** `[00:05:02]`: *"The trap is over-engineering and we'll discuss how to focus on real problems to secure your first-paying customer."* And `[00:07:00]`: *"you're basically built a **monument** over engineering, but not the actual product that is required in the market."*

### ⭐ His 4-point pre-build checklist — treat this as a scoring rubric

`05` `[00:26:52]`–`[00:27:34]`. He calls it *"one takeaway"* and *"run every feature or project idea through this."* A judge published his own filter. **Answer all four, in these words, in the README and the video.**

| # | His question, verbatim | HeatGuard's answer |
|---|---|---|
| 1 | **Hero** — *"Who's the hero? Name the exact person, role, industry, who will actually use this."* | Phoenix outdoor-crew supervisor deciding whether to pull a crew. Name a role, not "workers". |
| 2 | **Pain** — *"What is the manual, slow or expensive thing they're doing right now."* | Reading a peak-temperature forecast and guessing. |
| 3 | **AI justification** — *"Is AI **generally** required to solve this? Or are we just using it to earn high points at the expense of latency and cost?"* | **The router is deterministic precisely because AI is not required for the decision.** The LLM parses and narrates only. |
| 4 | **Kill switch** — *"What is the absolute simplest version of this product we can build to prove our hypothesis within the next 24 hours?"* | One site, one date, two layers, side by side. |

His problem formula, `[00:13:10]`, which at `[00:12:54]` he calls a *"programmatic [guardrail]"* — *"If you cannot fill out every variable cleanly, then we're not really ready to write a single line of code"*:

> *"**Specific user group** struggles to perform a **specific task** because of this **core obstacle**, which results in **measurable negative outcome**."*

Fill that sentence in exactly once, and make it the first line of the 500-word summary.

**Competing with FortyGuard's own roadmap is explicitly permitted — stop worrying about it.** Asked directly in the API session Q&A, `02-temperature-api` `[00:53:19]`–`[00:53:28]`:

> *"I did see one question like if it's clashing with 40 guys [FortyGuard] products, it's fine. **Go ahead, clash it with our products.** It's fine. If you can make something better out of it, you're all means go with all means and you're up for it. It's not, **you won't be hampered or you won't be penalized for it.** We respect the idea that you are bringing in and we will account that as well. […] If we are building something and you can do it in a better way than us, I think we would appreciate it."*

This matters because the territory is crowded (see `docs/video-insights.md` §3). It removes the strategic reason to avoid overlap — but not the *differentiation* reason. Overlap is safe; being indistinguishable is not.

## Architecture rule — non-negotiable

```
app.py     Streamlit surface
  ↓
agent.py   LLM: parses intent, narrates. NEVER picks the layer.
  ↓
router.py  ** CORE IP ** deterministic. question → layer → params + rationale + refusal
  ↓
tools.py   typed wrappers + cache keyed (endpoint, aoi_hash, date, time, filter_type, granularity)
  ↓
vendor quickstart client (auth + poll)

bands.py   leaf. heat index → NWS band + OSHA action, from config/thresholds.yaml.
           Imported by router.py and metrics.py; imports nothing of ours. Total
           functions — band_for/action_for never return None. (Added T2.)
```

The LLM does not choose the analysis layer. `router.py` does, deterministically. Reasons: **auditable** (safety tool), **reproducible** (demo takes must match), **testable with zero credits and no network**. Say this out loud in the video — constraining the LLM to what it is good at reads as maturity to a Google/NVIDIA panel.

### ✅ That last sentence was a guess. It is now confirmed by the Google judge, almost verbatim.

Ahmed Abdelkhalek, `05-builders-trap` `[00:25:12]`:

> *"please be responsible with your resource budget. There's nothing free in the world. **Traditional deterministic code is faster, cheaper and entirely predictable.**"*

And `[00:21:28]`:

> *"you need to **evaluate AI choices critically**, ensuring that we're **not introducing unnecessary latency and cost just for the hype**."*

And the line to build the video around, `[00:23:05]`–`[00:23:36]`:

> *"AI can solve everything, in fact, to some extent. But **should** it be actually used to solve everything? And the follow-up question is **at what cost?** […] It's incredibly powerful. But it's not a silver bullet for everything. **It could, but should it?**"*

At `[00:25:48]`–`[00:25:55]` he lists the trade-off as *"[regex] versus LLMs, cognitive reasoning, autonomous action […] there's always the quality to cost balance."* ("Regrics" in the transcript — Whisper, almost certainly *regex*.)

**This is the strongest strategic finding in six sessions.** The architecture rule is no longer a defensible choice we have to justify — it is the exact thing a judge stands on stage and asks for. Checklist item 3 (*"Is AI generally required?"*) is answered by the design itself.

**Consequence for the video:** do not bury this. State plainly that the layer decision is deterministic *because* an LLM is the wrong tool for it — auditable, reproducible, testable at zero cost — and that the LLM is confined to parsing and narration. Use his framing, not ours: *it could, but should it?*

## Conventions

- Secrets in `.env` only (`FORTYGUARD_API_KEY`). Never in code, never committed, never in client-side output, never visible in a demo video frame. **Keys in repos are an explicit disqualifier.**
- Cache every API result to `data/fixtures/` — tests run offline, and credits are never spent twice.
- Poll with backoff 3s → 6s → 12s.
- Append every agent decision to `data/decisions.jsonl` — site, date, question, layer, rationale, result, action. This is the compliance audit trail and the evidence the system works.
- Validate on a tiny polygon and a single timestamp before batching.

## Submission requirements

- **Live demo link — and it must stay up until 16 September.** `[00:59:31]`: *"Make sure it is live until the judging period has ended, which is **16th of September**. Make sure you have it up until one or two more days because the judges will take their time to review it."* Deadline is 30 Aug; **judging runs ~2.5 weeks past it.** Free-tier hosting that sleeps will fail silently during judging.
- **⚠ API access is REVOKED when judging ends (16 Sept)** `[00:57:16]`: *"the API access will end after the submission, like when the judging date has ended, which is 16th, and the API access will be revoked since this is an enterprise level API key."* Anything live after that must serve from cached fixtures or it dies. Another reason `data/fixtures/` is not optional.
- **The live link matters more than the repo** `[00:59:19]`: *"the judges won't be opening the GitHub repositories that often. You can expect them to open it. You can expect not to open them, but **what they will 100% open is your pitch, the live link.**"*
- **Add `Hackathon-FG` as a GitHub collaborator — hard prerequisite, not a nicety.** `[00:50:29]`–`[00:50:47]`: *"If it's not added as a collaborator on the GitHub or your repo and we don't have access to your code to see how you have utilized the Fortiguard API, that is like we can't move forward with the judging criteria for you. So the submissions that we send to the judges, **this submission would not be counted.**"* Required for public repos too `[00:59:51]`. Do this now, before the build is finished.
- ~3-minute demo video. **Do not AI-generate the pitch.** `01-kickoff` `[00:50:58]`–`[00:51:07]`, Snehil: *"We want a raw video technically so that we see what you have actually built rather than something which has been uplifted by AI. **We don't want AI.** AI can help you code. AI can help you get in the ideas as well. The pitch is where we want you guys to shine."* Jay softens it `[00:50:02]` (*"If you use an AI tool, we're not gonna limit you"*) — so it is a strong preference, not a rule. Present it yourself. No on-screen face required `[00:33:54]`.
- **Written summary, max 500 words** — ⚠ *unverified.* **No word limit is stated in any of the four transcripts.** Source unknown. Keep to 500 as a safe ceiling but do not treat it as a quoted rule.
- Disclose AI tool usage — required, explicitly **not** penalised. `[00:39:35]`: *"disclose any AI tools you use. I have already said it and **you will not be penalized for it.**"*
- **One submission only.** `[00:54:29]`: *"we're not going to review two applications for you. We're only going to review one. […] your previous applications get written over."* Resubmission before the deadline is fine; the latest overwrites.
- Submission portal was **not announced** in any session — *"We will be sharing a link with you guys near the submission date"* `[00:55:36]`. Watch Slack `#announcements` and email.

## Judging — what is actually sourced

| Criterion | Weight | Status |
|---|---|---|
| Impact & relevance | **40%** | ✅ **Verified verbatim.** `01-kickoff` `[00:39:02]`: *"impact and relevance holds for like 40% of the whole project."* |
| Technical execution | 35% | ⚠ **Never stated in any transcript.** Weight is unsourced. |
| Innovation | 15% | ⚠ **Never stated in any transcript.** Weight is unsourced. |
| Communication | **10%** | ✅ **Verified twice.** `01-kickoff` `[00:37:39]`: *"that actually holds like 10% of your whole criteria."* `02-temperature-api` `[00:57:56]`: *"10% goes into like communication."* |

Both spoken weights are hedged ("holds *like* 10%"). The 40/10 pair is real; the 35/15 split has no spoken source. **The four criteria and their order are confirmed** (`01-kickoff` `[00:35:11]`–`[00:36:21]`), only two of the four weights are.

Two definitions that differ from the obvious reading, and change what to emphasise:
- **"Technical execution" is defined almost entirely as AI-tool disclosure**, not code quality — `[00:35:34]`–`[00:35:53]`.
- **"Innovation" is defined as track behaviour**: *"did you pick up a track or did you make your own track? Or did you take that track and build it into something else? Or you combine two to three different tracks?"* `[00:35:55]`–`[00:36:04]`. **Combining tracks scores *for* you.** Track 4 × Track 6 is therefore rewarded, not a hedge. Say so in the summary.

There is a **two-stage screen** before judges see anything — an internal FortyGuard screening department, then the judges `[00:24:37]`–`[00:25:07]`.

## Open questions to resolve by probing, not assuming

1. ~~Is the key on Premium?~~ **ANSWERED — yes, and better than Premium.** Fawad `[00:14:24]`–`[00:14:42]`: *"this is the **most premium API key** that we are heading to you guys […] it has all those limit. And actually **the limit is double than what we are normally giving.**"* All five analysis endpoints — including `satellite`, `streetview`, `heat_intelligence` — were demoed live on the hackathon key. Nothing is gated.
2. ~~How does each constraint fail?~~ **ANSWERED — T4, all nine probed.** Full table in `docs/api-notes.md`. **Three silent failures, all billed:** non-US (`Completed`, 0 tiles), tomorrow's date (`Completed`, one flat value for the whole day), and `exceedance` with no `threshold` (`Completed`, defaults to 30 °C, returns 24 h). Loud and free: future dates (400), `filter_type=5` (422), bad granularity (422). Slow: pre-2021 sits in `Processing` >188 s then `Failed`.
3. Does an inversion day exist? **Highest risk in the project — now substantially de-risked.** Fawad's own client case study shows a near-inversion: 0.7 °C peak spread across six parcels vs 19 h exceedance / 5 h persistence (`[00:36:14]`–`[00:37:23]`). See `docs/demo_day_candidates.md`.
4. ~~Does `env_params` return heat index directly?~~ **ANSWERED — yes.** Fawad `[00:27:45]`: *"here are these like the **heat index Celsius** […] apparent temperature Celsius."* Confirmed independently from the vendor client (`heat_index_celsius`).
5. ~~What is the real AOI ceiling?~~ **ANSWERED — T4: not enforced at 447 km².** 11.5× the stated 15 mi² cap was accepted, 44,690 tiles, same flat cost. Ours stays self-imposed.
6. ~~Does `filter_type=5` (single month) work?~~ **ANSWERED — NO.** HTTP 422, `Input should be 1, 2, 3 or 4`. The vendor client was right; the transcript was wrong.
7. **NEW — the vendor client docstring says `tcm` tiles are °F. They are °C.** Measured live: Encanto Park 2025-07-15 returned min 32.72 / avg 36.92 / max 40.20, which is 91–104 °F as Celsius and an impossible hard freeze as Fahrenheit. `env_params` likewise returns `heat_index_celsius`. **Treat the whole API as Celsius**; the docstring is the outlier. Worth one line in the pitch — finding a unit error in the vendor's own client is exactly the kind of thing this project claims to catch.
