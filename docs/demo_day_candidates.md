# Demo day candidates

> Stub. T8. **Highest risk in the project.**

Need one historical date (2021→now) where two sites *invert*: one higher peak, the
other far longer above the danger band.

| Rank | Date | Why distinctive | Likely inverting pair | Confirmed? |
|---|---|---|---|---|

## Hypothesis to test
Monsoon days (Jul–Sep) carry humidity that keeps the *heat index* elevated for long
stretches even when the raw temperature peak is unremarkable; dry pre-monsoon June days
spike higher and fall away faster. If it holds, monsoon days are where site-level
duration differences should be widest. Verify before relying on it.

## Fallback
If no two-site inversion exists, contrast the *same* site under two layers — peak hour
vs full day. Weaker, but still a real and honest contrast.

## ⭐ Better fallback — FortyGuard's own case study already contains a near-inversion

**Added 2026-08-20 from `02-temperature-api` `[00:33:37]`–`[00:38:46]`. This materially
reduces the "highest risk in the project" rating above.**

Fawad Shah's client case study — six parcels, 17.38 acres, `granularity=80`, window
**28 Jul – 3 Aug** — ranks the same parcels two ways in the same demo:

- **By peak temperature** `[00:36:14]`: *"the hottest to coolest parcel, that's like **0.7
  degrees Celsius**, South Campus edge versus the River North."* → six sites,
  indistinguishable.
- **By duration** `[00:37:16]`: *"for **more than 19 hours**, it stayed above and then for
  **five hours straight**, it was above the threshold."* → clearly separated.

It ships in the quickstart repo (`[00:40:03]`) with cached results, so it runs **without
spending a credit or having network** (`02` `[00:48:18]`: *"there are cash [cached] results
as well. If you don't have the API access right now, you can use the cash results"*).

**Why this is strong:** it is FortyGuard's own data, presented by FortyGuard's own
engineering lead, to an audience that includes the judges. The inversion argument does not
have to be asserted — it can be *cited*.

**Why it is still only a fallback:** it is not Phoenix, not our sites, and not an
outdoor-worker context. Keep hunting for a real Phoenix inversion day; but the project no
longer fails if that hunt comes up empty.

⚠ Note the threshold unit when reproducing: the API takes **°C** (`[00:13:45]`,
`[00:24:57]` uses *"above 35 degrees Celsius"*) while `tcm` tiles read back in °F.
