# HeatGuard — pitch video script

*FortyGuard Hackathon'26 · ~3:00 · screen capture + voiceover, delivered live by Gabriele
Desimini. No AI narration, no on-screen face required.*

**Every number below is taken verbatim from `README.md`, `docs/submission-summary.md`,
`docs/site_selection.md`, `docs/routing_spec.md`, `src/heatguard/charts.py` and `app.py`.
Nothing here was re-derived.** The one exception is flagged in *Notes for the other
session* at the bottom.

---

## Recording this in pieces

The script below is one continuous 3:00 run, but it is built to be shot as **nine separate
takes** — every boundary falls on a click, a scroll, or a scripted hold, so the joins are
invisible. If you want to record beat by beat rather than in one pass:

| | |
|---|---|
| [`video/recording-plan.md`](video/recording-plan.md) | the nine takes, what is in each, recorder settings, and the recording order that needs only two tab switches |
| [`video/rehearsal.html`](video/rehearsal.html) | timed teleprompter with the real app frames. <kbd>Space</kbd> to play; **Loop take** drills one take until it is clean |
| [`video/takes.txt`](video/takes.txt) · [`video/assemble.ps1`](video/assemble.ps1) | drop `T1.mp4 … T9.mp4` beside them, run `.\assemble.ps1`, get `heatguard-pitch.mp4` |

---

## How to read this

- **Pace target: 150 words per minute.** That is a confident, unhurried pitch pace, not a
  rush. Total speech below is **433 words = 173 s**, plus **~7 s of deliberate held
  silence** in beat 3. That lands at **3:00** exactly.
- Word counts are given per beat so you can check yourself against the clock on a first
  read-through.
- `[CLICK]` = a click the viewer sees. `[SCROLL]` = a scroll. `[HOLD]` = stop talking and
  let the picture sit. The holds are load-bearing — do not fill them.
- Say the numbers as words, not as digits read off a page. "Seven hundred and one",
  not "seven-oh-one".

---

## 1. The beat-by-beat script

### Beat 0 · 0:00–0:15 — Cold open, the measured result *(35 words · 14 s)*

> **Three alternative versions of this beat are in §4. This is Option A.**

**On screen:** The live app already loaded on **`📋 The morning call`**, scrolled so the
three metric cards — *City-wide figure · worker-hours* / *Scoped to real shifts ·
worker-hours* / *Over-count* — fill the frame. No cursor movement. Nothing else visible.

> Last July fifteenth, a Phoenix safety manager reading the city forecast would have shut
> down seven hundred and one worker-hours as unsafe.
>
> Six hundred and forty-three of those, nobody was standing in.
>
> That's the product.

---

### Beat 1 · 0:15–0:33 — Hero and pain *(44 words · 18 s)*

**On screen:** `[SCROLL]` up to the header blockquote — *"A safety manager with twelve
Phoenix sites decides each morning where crews can work…"* Let the OSHA line
(**86 °F**) be readable behind you.

> The hero is a safety supervisor at a Phoenix contractor with twelve job sites.
>
> Every morning, one call — who works, who rotates, who stops.
>
> Today he makes it from a single forecast high, measured at Sky Harbor airport, and
> applies it to all twelve.

---

### Beat 2 · 0:33–0:59 — The morning call, and what it costs *(62 words · 25 s)*

**On screen:** `[SCROLL]` back down to the three metric cards, then keep scrolling into
the **`What that is worth`** section as you reach "ninety-two percent" — the
`$55/hour` slider and the **`$35,363`** figure must both be in frame while you say the
number.

> Here's that day, measured per site from FortyGuard's temperature API. Every site peaked
> within one-point-nine-six degrees of every other — by peak, they're the same place.
>
> Apply the city-wide number: seven hundred and one unsafe worker-hours. Scope it to the
> shifts crews actually work: fifty-eight.
>
> Ninety-two percent over-count. At a fifty-five dollar loaded rate, that's thirty-five
> thousand dollars of stop-work. In one day.

**Say the rate out loud.** The slider is visible behind you, so naming the assumption
turns your softest number into your most defensible one. A dollar figure with no rate
attached is the thing a judge discounts.

---

### Beat 3 · 0:59–1:49 — **THE MONEY SHOT: the day, hour by hour** *(111 words · 44 s + ~7 s held silence)*

**On screen:** `[SCROLL]` so **`#### The day, hour by hour`** and the full
`charts.the_day()` SVG fill the frame — all eleven rows, the red 13:00–20:00 band, and the
right-hand `no exposure` labels visible at once. **Do not scroll again until beat 4.**

> This is why.

`[HOLD — 2 s. Silence. Let the figure land.]`

> Each bar is one crew's shift, across a twenty-four hour day. The red band is the only
> window that was actually above OSHA's high-risk heat index — one o'clock to eight in the
> evening.

`[HOLD — 3 s. Say nothing. Let the viewer count the grey bars themselves.]`

> Look how many shifts miss it entirely. That's the ninety-two percent, in one picture.
>
> Eight of eleven sites tie at exactly seven hours above threshold — on a heat map they
> are the same colour. Scoped to shifts, only four carry any exposure at all.

`[HOLD — 2 s.]`

> And the worst crew isn't at the hottest site. It's the site with twenty-two people
> standing in that hour instead of eighteen.
>
> Heat maps rank tiles. Crews are what get hurt.

**Optional, only if you are running short:** `[SCROLL]` to
`#### What the city-wide figure claims, against what is real` and let `phantom_bars()`
sit silently for 2 s under the last line. It restates the same argument per site. It is
not needed.

---

### Beat 4 · 1:49–2:12 — The trap *(58 words · 23 s)*

**On screen:** `[CLICK]` the **`⚠️ The trap`** tab. Land on the `charts.unit_trap()`
figure — the `threshold = 35.00` / `threshold = 95` pair, with `status: Completed · 4,220
credits` on both rows.

> Two calls. Same endpoint, same area, same date, same parameters. The only difference is
> whether the threshold was converted from Fahrenheit.
>
> Converted: seventeen hours above the danger band. Unconverted: zero point zero.
>
> Both came back Completed. Both billed four thousand two hundred and twenty credits.
> Nothing was raised.
>
> Seventeen hours of dangerous exposure, reported as a clean all-clear.

---

### Beat 5 · 2:12–2:40 — How it decides *(70 words · 28 s)*

**On screen:** `[CLICK]` the **`How it decides`** tab. Land on the decision table.
`[SCROLL]` to `#### The LLM does not choose the layer` as you say "deterministic decision
table", then to `#### Refusals are a feature` on "refuses seven ways".

> So HeatGuard picks that string before any call is made — with no model at all.
>
> It could. It shouldn't.
>
> The router is a deterministic decision table: auditable, reproducible, testable at zero
> cost. A test runs the same question with and without a model and asserts every decisive
> field is identical.
>
> It refuses seven ways, and logs every question, layer and rationale. That log is what
> you hand an OSHA inspector.

---

### Beat 6 · 2:40–3:00 — What we got wrong, and close *(53 words · 21 s)*

**On screen:** `[CLICK]` back to **`📋 The morning call`**, `[SCROLL]` to
`#### The twelve sites and their predictions` — the roster table with the `Predicted`
column, and the bold line *"Two of eleven came true — worse than chance."* End on that
frame, or cut to a plain end card with the live URL and repo URL.

> One thing I'd rather not show you.
>
> Every site carried a prediction, written down before any data was fetched. Two of eleven
> came true — worse than chance. It's in the app, not buried.
>
> Track four crossed with track six. Built with Claude Code. The pitch is mine.
>
> Duration, not peak. Crews, not tiles.

---

## 2. Shot list — app states in order

Set up **before recording**, so nothing loads on camera. The app is offline by default
(`HEATGUARD_OFFLINE=1` unless `HEATGUARD_ONLINE=1` is set), so **no FortyGuard credits
are spent by any of this** — but do not set `HEATGUARD_ONLINE`, and do not open a terminal
or `.env` on camera.

| # | Beat | Tab | Scroll position / element | Action |
|---|---|---|---|---|
| 1 | 0 | `📋 The morning call` | The three `st.metric` cards, filling frame | none — already loaded |
| 2 | 1 | same | Header blockquote (the OSHA **86 °F** line) | `[SCROLL]` up |
| 3 | 2 | same | Metric cards → green `st.success` callout | `[SCROLL]` down |
| 4 | **3** | same | **`#### The day, hour by hour`** + full `the_day()` SVG, all 11 rows visible | `[SCROLL]` — then **freeze** |
| 5 | 3 *(optional)* | same | `#### What the city-wide figure claims…` (`phantom_bars()`) | `[SCROLL]`, 2 s, silent |
| 6 | 4 | `⚠️ The trap` | `unit_trap()` figure — both rows and both `4,220 credits` labels in frame | `[CLICK]` tab |
| 7 | 5 | `How it decides` | The decision table | `[CLICK]` tab |
| 8 | 5 | same | `#### The LLM does not choose the layer` | `[SCROLL]` |
| 9 | 5 | same | `#### Refusals are a feature` — the seven `RefusalReason` bullets | `[SCROLL]` |
| 10 | 6 | `📋 The morning call` | `#### The twelve sites and their predictions` — roster table + the "two of eleven" line | `[CLICK]` tab, `[SCROLL]` |
| 11 | — | end card | Live URL + repo URL + *"Built with Claude Code (Claude Opus 5)"* | hold 2 s |

**Deliberately not shown:** the `Ask a question` tab. It is the strongest interactive
demo in the app, but it costs 20–25 s to set up on camera and the routing argument is made
faster and more legibly by the static decision table in `How it decides`. Keep it as your
answer if a judge asks "can I drive it myself?" — the live link does that job.

### Pre-record checklist

- Browser at **100% zoom**, window wide enough that the `the_day()` SVG renders at full
  width and the right-hand `no exposure` labels are not clipped.
- **Light mode.** Both figures ship a dark palette that works, but the red 13:00–20:00
  band reads strongest on `#fcfcfb`.
- All four tabs clicked once before recording so Streamlit has cached them — tab switches
  must be instant on camera.
- No terminal, no `.env`, no `.streamlit/secrets.toml`, no API key anywhere in frame at
  any point. **Keys in frame are an explicit disqualifier.**
- Hide bookmarks bar and any browser extension that could show a notification.

### One thing to be ready for

The morning-call tab renders its subheader as **"11 sites, 107 workers"**, not twelve —
one site returned no tiles for the demo day, so it drops out of the rollup. The roster in
`docs/site_selection.md` is twelve sites and 125 workers. Your script says "twelve job
sites" in beat 1 (correct — that is the roster) and never states a headcount, so there is
no contradiction on camera. If a judge asks: *"Twelve on the roster; eleven returned data
for that date. Patchy per-location coverage is one of the six silent failure modes we
document, and dropping the site is why the rollup says eleven."*

---

## 3. If I run long — cut candidates, ranked

Cut in this order. Each is scored by damage-per-second-saved, and each is a clean lift —
no rewriting of adjacent lines needed.

### Cut 1 — Compress beat 1 to a single sentence · saves ~9 s

Replace the whole of beat 1 with:

> The hero is a safety supervisor at a Phoenix contractor with twelve job sites, making
> that call from one forecast high measured at Sky Harbor.

**Why this goes first:** the cold open already established who is harmed and how much it
costs. Beat 1 is doing confirmation, not work. You lose the OSHA 86 °F beat — acceptable,
because it is a supporting statistic for a claim the 92% already proves.

### Cut 2 — Drop the peak-spread sentence in beat 2 · saves ~7 s

Delete: *"Every site peaked within one-point-nine-six degrees of every other — by peak,
they're the same place."* Open beat 2 straight on *"Here's that day, measured per site from
FortyGuard's temperature API. Apply the city-wide number…"*

**Why second:** the 701 → 58 collapse carries the argument on its own, and the
indistinguishable-by-peak point gets made visually anyway when eight bars tie at seven
hours in beat 3. You are cutting a restatement, not a claim.

### Cut 3 — Drop the model-parity test sentence in beat 5 · saves ~8 s

Delete: *"A test runs the same question with and without a model and asserts every
decisive field is identical."*

**Why third, and why it hurts most:** this is the single hardest piece of evidence that
the deterministic claim is real rather than asserted, and it directly answers the "is AI
generally required?" question in the judge's own terms. Cut it only if you are still over
after cuts 1 and 2, and only because it is in `README.md`, `docs/submission-summary.md`
and the `How it decides` tab — a judge who cares will find it. Everything else in beat 5
must stay.

### Do not cut, under any circumstances

- The **13:00–20:00 red band** and the held silences around it. It is the only moment in
  three minutes where the viewer derives the conclusion instead of being told it.
- **17.0 h vs 0.0 h**, both `Completed`, both billed.
- **"It could. It shouldn't."** — twelve words, answers the AI-justification question, and
  it is the judge's own framing.
- **"Two of eleven came true — worse than chance."** Reporting a failed hypothesis
  unprompted is worth more than any additional feature you could show in its place.

**If you are still long after all three cuts:** drop the optional `phantom_bars()` scroll
in beat 3 (it is already marked optional and buys 2 s), then take the "Duration, not peak.
Crews, not tiles." tag off the end and let the end card carry it silently.

---

## 4. The opening fifteen seconds — three ways

All three lead with the measured result and frame it as cost, not safety. All three fit
the 15 s slot at 150 wpm. Record all three and pick in the edit — it costs you four
minutes. **B and C run ~2 s longer than A**; if you use either, take that 2 s out of the
optional `phantom_bars()` scroll in beat 3.

### Option A — The over-count *(35 words · 14 s · recommended)*

**On screen:** the three metric cards, static.

> Last July fifteenth, a Phoenix safety manager reading the city forecast would have shut
> down seven hundred and one worker-hours as unsafe.
>
> Six hundred and forty-three of those, nobody was standing in.
>
> That's the product.

**Why it is the default:** it puts a measured number in the first five seconds, the drop
from 701 to 643 does the persuading, and *"That's the product"* is a promise the next 2:45
keeps exactly. It also matches the metric cards frame-for-frame, so the viewer's eye
verifies you while you speak.

**Risk:** "worker-hours" is a unit the viewer meets for the first time in your opening
sentence. It survives because the number is large and the sentence is short.

### Option B — The money *(40 words · 16 s)*

**On screen:** the three metric cards, static — same frame as A.

> This is thirty-five thousand dollars of stop-work that didn't need to happen. One
> contractor, twelve Phoenix sites, one day in July.
>
> The forecast said the city was dangerous. Ninety-two percent of that danger was in hours
> nobody was outside.

**Why you would pick it:** impact and relevance is the only weight confirmed verbatim at
40%, and this is the version that speaks in the judges' scoring language from word one. A
dollar figure is the fastest possible way to establish that this is cost avoidance and not
a weather app.

**Risk:** the dollar figure is an inference from a loaded labour rate, not an API
measurement, and you have led on your softest number. If you use B, name the rate in the
same breath — *"six hundred and forty-three worker-hours at fifty-five dollars an hour;
the hours are measured, the rate is the assumption, and it's a slider"* — and make sure
the `What that is worth` section is the frame you open on, so the slider is visible while
you say it.

### Option C — The contrarian *(41 words · 16 s)*

**On screen:** the `the_day()` figure, already on screen at 0:00, **before** you cut back
to the metric cards at 0:15.

> Your scheduling already works. That's the finding.
>
> On a measured Phoenix day, ninety-two percent of the unsafe exposure a city forecast
> reports is in hours no crew was outside.
>
> There is one window that isn't — and almost every shift misses it.

**Why you would pick it:** it is the most memorable of the three, because it opens by
conceding the thing every competing entry is about to claim. A judge who has watched six
heat-safety pitches in a row will sit up. It also puts the money shot on screen at second
zero and gives it a second viewing later, which is a real advantage for the one figure
that has to land.

**Risk:** it is the highest-wire option. "Your scheduling already works" can read as "so
you don't need this" if the next sentence doesn't arrive fast and clean. Only use C if
you can deliver the turn on *"There is one window that isn't"* without hesitating. If
there is any doubt in the take, use A.

---

## 5. Notes for the other session — things I did not change

Per the file lock I created only this file. Verified against the live deployment on
2026-08-28. Six things I would otherwise have raised as edits:

0. **🚨 BLOCKER — `⚠️ The trap` and `How it decides` render completely blank on the live
   app.** Both tab panels return zero characters after a hard reload, with no Python
   exception surfaced; the tab labels are correct and the first two tabs are fine. That is
   **beats 4 and 5 — fifty of the hundred and eighty seconds**, and it is also the tab
   FortyGuard's own guidance says judges will open. Nothing else on this list matters until
   this is fixed. Re-check by loading the app and clicking straight to the third tab.

1. **The dollar figure is now settled, and the script has been changed to match the app.**
   The deployed `What that is worth` section shows **\$35,363 at \$55/h**, on a \$25–100
   slider, alongside "cost of being wrong the other way: one heat-illness claim". Beat 2
   used to say "\$29k–42k" from the brief; it now says **thirty-five thousand at a
   fifty-five dollar loaded rate**, which is both correct and more defensible because the
   slider is on screen. **Neither `README.md` nor `docs/submission-summary.md` carries the
   dollar figure yet** — if the live link shows it and the written entry does not, they
   disagree on the number that carries the 40% weight.

2. **Test-count drift.** `docs/routing_spec.md` says *"224 offline tests"*; `README.md` and
   the `How it decides` tab both say *"336 tests"*. The script deliberately says neither
   number aloud, so the video is safe either way — but a judge reading both files will see
   the mismatch. `routing_spec.md` is the stale one.

3. **Peak-spread drift.** `README.md` and `docs/submission-summary.md` say **1.96 °F**;
   `app.py`'s morning-call copy says *"a spread of **1.9 °F**"* and *"102.6 and 104.5 °F"*
   (which is 1.9 °F). Beat 2 says "one-point-nine-six" to match the written summary. Either
   is defensible, but they should be the same string in both places.

4. **Silent-failure count drift.** `README.md` heads its table *"Six ways the API fails
   silently"* and lists six rows, including *"Some sites on some dates — zero tiles"*. The
   `⚠️ The trap` tab shows the unit trap plus *"Four more failures that look like answers"*
   — five total, missing the patchy-per-location row. That missing row is exactly the one
   that explains why the rollup says eleven sites and not twelve (see §2), so it is worth
   adding to the trap table rather than dropping from the README.

5. **`charts.py`'s `unit_trap()` clips its own label.** The top row's
   `status: Completed · 4,220 credits` text is placed at `x = left + max(w,22) + 78`, which
   for the 17-hour bar is **x = 858 inside a 940-wide viewBox** — the string is ~180 px
   long, so it runs off the right edge. That is beat 4's only frame. Either widen the
   viewBox or move the status label under the bar.

6. **`docs/site_selection.md` says "125 workers across 12 sites"; the twelve crew sizes sum
   to 115.** (14+22+8+6+5+4+5+6+18+11+7+9.) The live app's 107 is 115 minus the dropped
   Deer Valley site's 8, which reconciles exactly — so the roster and the rollup agree and
   only the stated total is wrong. The "33 of them work nights" figure checks out
   (6+5+4+18). Worth fixing, because a judge who adds the column will find it.

**Also worth knowing before you record:** `docs/routing_spec.md` gives the seven refusal
reasons as `OUTSIDE_US`, `BEFORE_2021`, `BEYOND_FORECAST`, `EXCEEDS_30_DAY_WINDOW`,
`AOI_TOO_LARGE`, `GRANULARITY_TOO_FINE`, and `WRONG_LAYER_WOULD_MISLEAD`. If a judge asks
which refusal is the differentiator, it is the seventh — refusing a well-formed question
the API would happily answer, because the only layer that fits the requested scope would
produce a confident wrong answer. One sentence, and it is the strongest thing in the
router.
