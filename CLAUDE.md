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
- **Dates 2021-01-01 → now.** Heatmap alone forecasts to **now + 12h**.
- **⚠ AOI ≤ 15 mi² (~38.8 km²), NOT 50 mi².** Fawad `[00:23:53]`–`[00:23:58]`: *"on this plan, I think we have the premium one for you. So the limit is about 15 miles square."* **This contradicts the handbook figure of ~130 km² / 50 mi² previously recorded here — by 3.4×.** Transcript is a live engineer reading the premium plan limit; handbook figure is unsourced. Treat **15 mi² as the working limit** and probe the real ceiling in T4. Getting this wrong sizes every AOI in the demo wrong.
- **Max 30 days of data returned per call.** Fawad `[00:19:53]`: *"we are giving you the opportunity to get as much as 30 days worth of data."* Caps any multi-week duration analysis at one call per month.
- `granularity`: **60 / 80 / 100 m** — smaller costs more credits.
- `filter_type`: **1** = single hour · **2** = hour range (+`end_time`) · **3** = entire day · **4** = day range · **5** = single month. Fawad enumerates all five, `[00:19:39]`: *"each of them like single hour, we have range of hours, we have a single day, we have a range of days and then we have a single month."* The vendor client documents only 1–4, so **5 exists per the engineer but is undocumented in code — still probe it in T4.**
- **Rate limit: ~100 requests/minute, capped hourly, no daily cap.** Fawad `[00:56:17]`–`[00:56:31]`: *"hourly, we have put a limit to it, not the daily one […] we're limiting it to not more than I think 100 requests per minute or something. But as such, there's no other limits."* Hedged ("I think", "or something") — treat as approximate. Host adds `[00:56:44]`: *"Let's not test the rate limits and reverse engineer it."*
- **Credits: 2,000,000 per API key.** Confirmed in both sessions. Real cost anchor from Fawad's own key `[00:22:50]`–`[00:23:08]`: **187,420 credits total** across the whole demo build, of which **72,000 for tile segmentation**. So a full worked case study costs <10% of one key. Budget anxiety is unwarranted; **but** `[00:47:06]` the organisers will top up if you exhaust it.

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

A judge is literally giving a talk called *"The Builder's Trap: escaping the hype."* Innovation is 15%; Impact is 40%. Do not add surface.

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
2. How does each constraint fail — status code, error shape, loud or silent? **Partly answered:** non-US fails *silently and bills you* (`[00:13:39]`). The rest still needs probing.
3. Does an inversion day exist? **Highest risk in the project — now substantially de-risked.** Fawad's own client case study shows a near-inversion: 0.7 °C peak spread across six parcels vs 19 h exceedance / 5 h persistence (`[00:36:14]`–`[00:37:23]`). See `docs/demo_day_candidates.md`.
4. ~~Does `env_params` return heat index directly?~~ **ANSWERED — yes.** Fawad `[00:27:45]`: *"here are these like the **heat index Celsius** […] apparent temperature Celsius."* Confirmed independently from the vendor client (`heat_index_celsius`).
5. **NEW — what is the real AOI ceiling?** Fawad says 15 mi²; the handbook figure was 50 mi². 3.4× apart. Probe before sizing demo AOIs.
6. **NEW — does `filter_type=5` (single month) work?** The engineer enumerates it; the vendor client does not document it.
