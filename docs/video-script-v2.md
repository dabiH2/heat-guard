# HeatGuard — pitch video script v2 *(user-centric)*

*FortyGuard Hackathon'26 · **3:00 hard maximum** · screen capture + live voiceover by
Gabriele Desimini. No AI narration, no face required.*

**What changed from v1.** v1 was a third-person pitch *about* the product. v2 is a
first-person walkthrough *as the user*: I state that I am impersonating a Phoenix safety
supervisor, show how I make the call today, then make it again with the app and name what
changed. The spine moves from the pre-computed morning-call report to the **`Ask a question`
tab**, because that is the only place a viewer watches the tool being *used* rather than
read.

**v1 is not deleted.** [`video-script.md`](video-script.md) and
[`video/recording-plan.md`](video/recording-plan.md) still describe the old cut. Nothing
below overwrites them.

> ⚠️ **Every number in v1 that came from the app has moved.** The `$55/hour` slider is now
> **`$51.23`** (BLS ECEC, sourced), the single `$35,363` is now a **range**, and the
> "peak is a poor predictor" line was withdrawn as unsupportable. **Do not record any v1
> beat verbatim.**

---

## The decision that shapes this cut

Three minutes is a hard ceiling and the Ask-tab interaction costs ~45 s. Something had to go,
and it is **the money**. v2 never says a dollar figure aloud.

The hours (701 → 58) are *measured from the API*. The dollars are an assumption layered on
top — now a defensible range rather than a point, but a range is a bad thing to say out loud
("between four and thirty-three thousand" sounds like you don't know). The `What that is
worth` section stays on screen during T2 for anyone who pauses; you just don't narrate it.

**If a judge asks about money in Q&A:** *"Six hundred and forty-three worker-hours. At the
BLS construction rate of fifty-one twenty-three, the floor is the mandated rest you owe even
while working — about four thousand a day — and the ceiling, if you actually stop, is about
thirty-three. The hours are measured; the rate is sourced; the range is honest."*

---

## How to read this

- **Pace: 150 wpm.** Speech below is **423 words ≈ 169 s**, plus **5 s of scripted hold** =
  **174 s**. The nine slots are cut to **177 s (2:57)**, so every take carries a little air
  and the finished video sits **3 s under the 3:00 ceiling**. Re-measured 29 Aug.
- `[CLICK]` = a click the viewer sees · `[SCROLL]` = a scroll ·
  `[HOLD]` = stop talking, let the frame sit.
- Say numbers as words. "Seven hundred and one", not "seven-oh-one".
- **Never state a headcount.** The roster is twelve sites; the app's roll-up says eleven
  sites and 107 workers because one site returned no tiles. Say "twelve job sites" and stop.

---

## 1. The script

### T1 · 0:00–0:16 — Who I am *(39 words · 16 s)*

**Screen:** `📋 The morning call`, scrolled to the header blockquote. The **86 °F** line and
the OSHA *"do not rely solely on the Heat Index"* quote both readable. Cursor still.

> I'm going to do this as a user, not a demo.
>
> For the next three minutes I'm the safety supervisor at a Phoenix contractor, with twelve
> outdoor job sites.
>
> Every morning, one call: who works, who rotates, who stops.

---

### T2 · 0:16–0:37 — How I do it today *(53 words · 21 s)*

**Screen:** `[SCROLL]` down to the three metric cards. The `What that is worth` section may
enter frame at the tail — do not narrate it.

> Today I make that call from one number. The forecast high for Phoenix, measured at Sky
> Harbor airport, applied to all twelve sites.
>
> OSHA's own guidance says don't do that. Outdoor workers have died of heatstroke when the
> day's maximum heat index was eighty-six.
>
> Here is what that one number costs me.

---

### T3 · 0:37–1:00 — What it costs *(49 words · 23 s + 3 s hold)*

**Screen:** metric cards in frame, then `[SCROLL]` to `#### The day, hour by hour` — all
eleven rows, the red 13:00–20:00 band, and the right-hand `no exposure` labels visible at
once. **Then freeze.**

> Seven hundred and one worker-hours flagged unsafe. Scoped to the shifts my crews actually
> work — fifty-eight.

`[HOLD — 3 s. Say nothing.]`

> Each bar is one crew's shift. The red band is the only window that was genuinely dangerous,
> one o'clock to eight in the evening. Look how many shifts miss it entirely.

---

> ⚠️ **T4–T8 were rewritten on 29 Aug** after the Ask tab was rebuilt. The six-preset
> dropdown **no longer exists** — the tab is now a crew multi-select, a free-text question
> box, and four example chips. Anything describing a preset menu is dead.

### T4 · 1:00–1:13 — The crews I'm worried about *(32 words · 13 s)*

**Screen:** `[CLICK]` the **`Ask a question`** tab. It opens on three crews already selected
in the **Crews** multi-select, each reading *name · N crew · shift window*, and **Chase Tower
carries the 🌙 night flag**. Do not change the selection — the default is the shot.

> That's the roll-up. Now the three crews I'm actually worried about.
>
> Each one is a crew, not a map tile — headcount, shift window, and whether these are the
> people working nights.

---

### T5 · 1:13–1:37 — I ask it the way I'd really ask it *(60 words · 24 s)*

**Screen:** `[CLICK]` the **`Right now`** chip. The box fills with *"How hot is it at this
crew's site right now?"*, the 🧭 readout reads `snapshot → analytic_type=tcm`, then
`[CLICK]` **`Ask HeatGuard`** → a **ranked table, hottest first**.

> First I ask it the way I'd say it out loud: *how hot is it right now?*
>
> Before it fetches anything it tells me how it read that — a snapshot, one reading, one
> moment. Ranked that way, Chase Tower is my worst crew.
>
> And every one of them is a hundred and four degrees. By peak, they're the same place.

---

### T6 · 1:37–2:02 — The same crews, asked properly *(57 words · 25 s + 2 s hold)*

**Screen:** `[CLICK]` the **`Hours above`** chip → readout changes to
`duration → analytic_type=exceedance` → `[CLICK]` **`Ask HeatGuard`**. **The table
re-orders: 27th Avenue takes the top row.**

> So I ask what I actually meant. *How many hours were they above the threshold?*
>
> Same crews, same day, same screen. Watch the order.

`[HOLD — 2 s.]`

> It re-ranks. My worst crew is now the one with twenty-two people in it, not the one that
> was a hundredth of a degree hotter. Peak ranked tiles. This ranks crews.

---

### T7 · 2:02–2:23 — Why it changed *(51 words · 21 s)*

**Screen:** `[CLICK]` the **`⚙ Mechanism`** expander directly under the table. It opens on a
step-by-step table: the layer, why, `endpoint / filter_type / analytic_type / granularity`,
and what the other layer would have said.

> And this is the part I'd have to defend. It shows me which layer it used and why, in one
> place, next to the answer.
>
> Those two questions are one optional string apart in the same API call. Same endpoint, same
> parameters, no error either way — and the opposite operational decision.

---

### T8 · 2:23–2:39 — It refuses *(38 words · 16 s)*

**Screen:** `[CLICK]` the fourth example chip — it is labelled **`Start and stop · refuses`**,
so the demo is built into the control. The 🧭 readout is replaced by the 🚫 warning
*"Reads as **intraday** → **refused** (`wrong_layer_would_mislead`). No call would be made."*
**No button press needed — the refusal happens in the readout, before any call.**

> And when I ask something the data can't answer, it says so, and makes no call at all.
>
> It doesn't guess. Every question, every layer, every refusal gets logged — and that log is
> what I hand an inspector.

---

### T9 · 2:39–2:57 — What I actually get *(44 words · 18 s)*

**Screen:** `[CLICK]` back to `📋 The morning call`, `[SCROLL]` to
`#### The twelve sites and their predictions` — the `Predicted` column and the *"Two of
eleven came true"* line in frame. End there.

> What I get is a defensible morning. The same fifteen minutes, but a decision per crew
> instead of one number for a city.
>
> One thing I'd rather not show you: twelve predictions written down first. Two came true.
> It's in the app, not buried.

---

## 2. Take table

Total **2:57**. One tab switch out, one back.

| Take | Beat | In → Out | Length | Screen state | Action during |
|---|---|---|---|---|---|
| **T1** | who I am | 0:00 → 0:16 | 16.0 s | Morning call · header quote | none — dead still |
| **T2** | today's method | 0:16 → 0:37 | 21.0 s | Morning call · → metric cards | `[SCROLL]` down at head |
| **T3** | what it costs | 0:37 → 1:00 | 23.0 s | Morning call · `the day, hour by hour` | `[SCROLL]` at head, then **freeze**; 3 s hold inside |
| **T4** | the crews | 1:00 → 1:13 | 13.0 s | **`Ask a question`** · 3 crews selected | `[CLICK]` tab only — **do not change the default selection** |
| **T5** | ask naturally | 1:13 → 1:37 | 24.0 s | Ask · ranked by peak | `[CLICK]` **`Right now`** chip, then **Ask HeatGuard** |
| **T6** | ask properly | 1:37 → 2:02 | 25.0 s | Ask · **table re-orders** | `[CLICK]` **`Hours above`** chip, then **Ask HeatGuard**; 2 s hold |
| **T7** | why it changed | 2:02 → 2:23 | 21.0 s | Ask · **`⚙ Mechanism`** open | `[CLICK]` the Mechanism expander |
| **T8** | it refuses | 2:23 → 2:39 | 16.0 s | Ask · 🚫 refusal in the readout | `[CLICK]` **`Start and stop · refuses`** chip — no button press |
| **T9** | net benefit | 2:39 → 2:57 | 18.0 s | Morning call · predictions table | `[CLICK]` tab, `[SCROLL]` |

*Slot lengths were re-measured against the actual narration on 29 Aug at 150 wpm and now
match it take by take. Speech plus scripted holds totals **174.2 s**, so every slot carries a
little air and the finished cut sits **5.8 s under the 3:00 ceiling**.*

**Record in this order** — three screen states, not nine:

```
1. T1  morning call · header
2. T2  morning call · metrics
3. T3  morning call · the day
4. T9  morning call · predictions     ← out of script order, on purpose
   ── switch tab ──
5. T4  Ask · site selected
6. T5  Ask · snapshot badge
7. T6  Ask · duration badge
8. T7  Ask · answer panel
9. T8  Ask · refusal
```

Name files `T1.mp4 … T9.mp4`. Let each recording run ~1 s past your last word — that tail is
your trim margin.

---

## 3. Rehearse these four things before you record

**1. The refusal (T8) — now built into the UI, nothing to hunt for.** The fourth example chip
is labelled **`Start and stop · refuses`**. Three of the six question shapes now refuse:
`intraday`, `forecast` and `persistence`. Measured across the whole surface: 12 crews × 6
question shapes × 2 thresholds = **144 paths, 72 answered, 72 refused, zero errors**.

Half the app refuses, on purpose, because half the questions cannot be answered honestly from
this API. That is the strongest single thing you can say in T8.

**2. ⚠️ The T6 re-order is real but SUBTLE — narrate it correctly or it reads as a bug.**
Verified on the three default crews at 103 °F:

| Crew | peak | hours above, whole day | in-shift hours | crew |
|---|---|---|---|---|
| Chase Tower | 104.435 °F | 7.0 | 0.0 | 6 |
| 27th Avenue | 104.431 °F | 7.0 | 1.0 | 22 |
| Union Hills | 102.580 °F | 4.4 | 0.0 | 9 |

Chase leads on peak by **0.004 °F**, and both top crews tie at **exactly 7.0 hours** — eight
of eleven sites do, which is the project's own published finding. So the re-order is decided
by the tie-break (in-shift hours, then headcount), **not** by a visible gap in the numbers.

On camera both peaks render as **104 °F**. If you say "look, a different number", a judge sees
two identical numbers and distrusts the tool. **Say what is actually true and it becomes your
strongest line:** *"every one of them is a hundred and four degrees — by peak they're the same
place"*, then *"it re-ranks on the one with twenty-two people in it."* That is the thesis, not
a workaround.

**2. The badge is the shot in T5 and T6.** Before recording, confirm the 🧭 info box is
inside the frame at your window width. If the left column is narrow the badge can sit below
the fold. Widen the window until badge and text box are visible together, then **do not
resize again for the rest of the session.**

**3. Use the chips, not the keyboard.** Each example chip writes its text into the question box
and re-renders the 🧭 readout in **one click** — no typing, no Enter, no lag. That is why every
question change in T5, T6 and T8 is a chip click. **If you'd rather type**, know that the
readout only updates on Enter or when the box loses focus, and typing on camera is slower and
much easier to fumble.

**4. Pick your T4 site deliberately.** Choose one with `night_shift = True` so the caption
shows 🌙 **night** — it earns the "whether these are the people working nights" line and
sets up why a daytime forecast high is the wrong instrument. Note the site name; you'll want
it if a judge asks.

---

## 4. Pre-record checklist

Unchanged from v1 except where noted.

- App **offline by default** — `HEATGUARD_OFFLINE=1`. **Do not set `HEATGUARD_ONLINE`.** No
  credits are spent by any of this.
- **No terminal, no `.env`, no `.streamlit/secrets.toml`, no API key in frame at any point.
  Keys in frame are an explicit disqualifier.**
- Browser at **100% zoom**, **light mode**, bookmarks bar hidden, Do Not Disturb on.
- **Click all four tabs once** before recording so Streamlit has them cached — tab switches
  must be instant on camera.
- **New for v2:** in the Ask tab, click all four example chips once and press *Ask HeatGuard*
  on each answerable one before recording, so every routing preview and every table is warm.
  Then reload so the tab is back on its three default crews before T4.
- **Do not move the window, change zoom, or resize between takes.** Everything else is
  recoverable; that is not.

**Recorder settings — identical for all nine takes:** OBS or Xbox Game Bar, 1920×1080,
**30 fps constant**, MP4, CBR ~8–12 Mbps, mic only with desktop audio muted.

---

## 5. Stitching

`assemble.ps1` is already parameterised, so v1 and v2 can coexist. Put `T1.mp4 … T9.mp4`
beside it and run:

```powershell
.\assemble.ps1 -ListFile takes-v2.txt -Out heatguard-demo.mp4
```

It probes all nine, warns on codec/resolution/fps mismatch, concatenates with `-c copy`
(lossless, instant), checks the duration against the expected 177 s, and re-encodes
automatically if the stream copy drifted.

By hand:

```powershell
ffmpeg -f concat -safe 0 -i takes-v2.txt -c copy heatguard-demo.mp4
```

**If a take runs long**, trim the tail rather than re-recording — every take ends on a hold
or a beat end, so you lose silence, not words:

```powershell
ffmpeg -i T6.mp4 -t 24.0 -c copy T6-trim.mp4
```

then point `takes-v2.txt` at the trimmed file.

---

## 6. If you run long — cut in this order

You have 3 s of margin. If a take overruns, cut here before you re-record anything.

| # | Cut | Saves | Cost |
|---|---|---|---|
| 1 | T2's OSHA sentence — *"OSHA's own guidance says don't… eighty-six."* | ~9 s | The 86 °F stat is supporting evidence for a claim T3 proves visually. Lowest damage. |
| 2 | T7's second sentence — *"Those two questions are one optional string apart… opposite operational decision."* | ~9 s | The re-ordered table in T6 already made the point visually. Keep the first sentence: the audit trail is the part a buyer pays for. |
| 3 | T4's second sentence, keeping *"Now the site I'm actually worried about."* | ~9 s | Loses the night-shift setup. Only if still long after 1 and 2. |

**Do not cut, under any circumstances:**

- **The T5 → T6 badge change.** It is the entire product, shown rather than claimed, and it
  is the only moment where the viewer watches the tool make a decision.
- **The 3-second hold in T3.** The one moment the viewer derives the conclusion instead of
  being told it.
- **T8, the refusal.** A tool that declines to answer is the most credible thing in the video.
- ***"Two came true."*** Reporting a failed hypothesis unprompted is worth more than any
  feature you could show instead.

---

## 7. What v2 deliberately does not show

- **The `⚠️ The trap` tab and the unit trap.** It is the strongest *engineering* argument in
  the project and it does not survive translation into first person — a supervisor does not
  care that a Fahrenheit threshold returns 0.0 hours. The argument still reaches a judge
  through the README and the tab itself. **Have it ready as your first Q&A answer.**
- **`How it decides`.** Same reason. T5–T7 demonstrate the router's behaviour from outside;
  the tab explains it from inside.
- **Dollars.** See the top of this file.
- **The evidence registry and source links.** They are visible in the app for anyone who
  looks, and they are what a judge will find when they check your claims — but narrating
  citations burns seconds and reads as defensive. Let them be discovered.
