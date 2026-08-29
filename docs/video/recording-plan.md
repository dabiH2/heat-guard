# Recording plan — nine takes, stitched with one command

*Companion to [`../video-script.md`](../video-script.md). Rehearse against
[`rehearsal.html`](rehearsal.html) — press <kbd>Space</kbd>, and use **Loop take** to drill
one take until it is clean.*

---

## Why this splits cleanly

Every take boundary below falls on one of two things:

- **a click or a scroll** — the frame is moving, so a cut there reads as the cut you meant
  to make; or
- **a scripted hold** — the frame is frozen and you are silent, so the cut is literally
  invisible: the last frame of one take and the first frame of the next are the same pixels.

That is why the money shot can be three separate takes without looking like three takes.
T4, T5 and T6 all sit on the same untouched `the day, hour by hour` figure.

**Do not move the window, change zoom, or resize between takes.** Everything else is
recoverable; that is not.

---

## The nine takes

Times are from the rehearsal player, which is the authority. Total **180.2 s = 3:00**.

| Take | Beat | In → Out | Length | Screen state | Action during |
|---|---|---|---|---|---|
| **T1** | 0 | 0:00.0 → 0:14.0 | **14.0 s** | Morning call · the three metric cards | none — dead still |
| **T2** | 1 | 0:14.0 → 0:31.6 | **17.6 s** | Morning call · header quote (86 °F line) | scroll up, at the top |
| **T3** | 2 | 0:31.6 → 0:56.4 | **24.8 s** | Morning call · metrics → `What that is worth` | scroll down at head; scroll again at 0:49 so the **$55 slider and $35,363** are in frame |
| **T4** | 3a | 0:56.4 → 1:15.8 | **19.4 s** | Morning call · `the day, hour by hour` | scroll to the figure, then **freeze** |
| **T5** | 3b | 1:15.8 → 1:35.4 | **19.6 s** | *same frame, untouched* | none |
| **T6** | 3c | 1:35.4 → 1:47.8 | **12.4 s** | *same frame, untouched* | none |
| **T7** | 4 | 1:47.8 → 2:11.0 | **23.2 s** | `⚠️ The trap` · the unit-trap figure | click the tab at head |
| **T8** | 5 | 2:11.0 → 2:39.0 | **28.0 s** | `How it decides` · decision table | click the tab at head; scroll to *The LLM does not choose the layer*, then *Refusals* |
| **T9** | 6 | 2:39.0 → 3:00.2 | **21.2 s** | Morning call · predictions table | click the tab, scroll to `The twelve sites and their predictions` |

Each take ends either on a hold or on a beat end, so **let the recording run about one
second past your last word** and stop. That tail is your trim margin.

### What is inside T4 / T5 / T6

| | contains | why it ends there |
|---|---|---|
| **T4** | "This is why." → **HOLD 2 s** → "Each bar is one crew's shift…evening." → **HOLD 3 s** | ends mid-hold, frozen frame |
| **T5** | "Look how many shifts miss it…" → "Eight of eleven sites tie…" → **HOLD 2 s** | ends mid-hold, frozen frame |
| **T6** | "And the worst crew isn't at the hottest site…" → "Heat maps rank tiles. Crews are what get hurt." | ends the beat |

The holds are inside the takes, not between them. Record the silence — do not stop and
restart, or you lose the beat that makes the figure land.

---

## Record in this order, not in script order

Nine takes, but only **two tab switches** if you record by screen state:

```
1. T1   morning call · metrics
2. T2   morning call · header          (scroll up)
3. T3   morning call · metrics → cost  (scroll back down)
4. T4   morning call · the day
5. T5   morning call · the day         (do not touch anything)
6. T6   morning call · the day         (do not touch anything)
7. T9   morning call · predictions     ← out of script order, on purpose
   ── switch tab ──
8. T7   ⚠️ The trap
9. T8   How it decides
```

Name the files by **take**, not by recording order — `T1.mp4 … T9.mp4`. The concat list
puts them back in script order for you.

---

## Recorder settings

Whatever you use, the one rule that matters: **identical settings for all nine takes.**
Same tool, same session, same resolution, same frame rate. That is what lets the stitch be
a lossless copy instead of a re-encode.

| | Recommended |
|---|---|
| Tool | **OBS Studio** (free) — or Xbox Game Bar (<kbd>Win</kbd>+<kbd>G</kbd>), already on Windows 11 |
| Resolution | 1920×1080, window or display capture |
| Frame rate | **30 fps, constant** — in OBS: Settings → Video → Common FPS Values → 30 |
| Encoder | x264 or hardware, CBR, ~8–12 Mbps |
| Container | **MP4** |
| Audio | 48 kHz, one track. Mic only — mute desktop audio so no notification can land in a take |

**Before the first take:** browser at 100% zoom, light mode, bookmarks bar hidden, Do Not
Disturb on, all four tabs clicked once so Streamlit has them cached. No terminal, no
`.env`, no `.streamlit/secrets.toml` in frame at any point.

---

## Stitching — one command

Put `T1.mp4 … T9.mp4` next to [`takes.txt`](takes.txt) and [`assemble.ps1`](assemble.ps1),
then from PowerShell in that folder:

```powershell
.\assemble.ps1
```

It probes all nine files, warns if any of them disagree on codec, resolution or frame rate,
concatenates with `-c copy` (instant, lossless, no quality loss), checks the output duration
against the expected 180.2 s, and automatically re-encodes if the stream copy drifted.
Output: `heatguard-pitch.mp4`.

If you would rather run it by hand:

```powershell
ffmpeg -f concat -safe 0 -i takes.txt -c copy heatguard-pitch.mp4
```

**No ffmpeg, and you don't want to install it?** Windows 11 ships **Clipchamp** — import all
nine, drag them onto the timeline in T1→T9 order, export at 1080p30. Slower and it
re-encodes, but it needs nothing installed. Any editor works; the takes are built to
butt-join with no transitions, so there is nothing to adjust.

### If a take runs long

The concat is dumb — it plays whatever you give it. If your T5 runs 22 s instead of 19.6 s,
the finished video is 3:03, which is fine for a "~3 minute" video. If you want it exact, trim
that one take rather than re-recording:

```powershell
ffmpeg -i T5.mp4 -t 19.6 -c copy T5-trim.mp4
```

then point `takes.txt` at `T5-trim.mp4`. Because every take ends on a hold or a beat end,
trimming the tail costs you silence, not words.

---

## Order of operations

1. **Fix the two blank tabs first.** `⚠️ The trap` and `How it decides` currently render
   empty on the live app — see §5 of [`../video-script.md`](../video-script.md). T7 and T8
   cannot be recorded until that is resolved. Everything else can be shot today.
2. Rehearse in `rehearsal.html` with **Loop take** on, one take at a time.
3. Record T1–T6 and T9 in one sitting on the morning-call tab.
4. Record T7 and T8 once the tabs render.
5. `.\assemble.ps1`
6. Watch it once at full length before uploading. Check: no key or path in frame, the red
   band is legible, and the audio level is consistent across the tab switch — that is the
   one join where a level change would be audible.
