# HeatGuard — written summary

*FortyGuard Hackathon'26 · Track 4 (Government & Environment) × Track 6 (Agentic)*

**Live demo: https://heat-fortyguard.streamlit.app/** · **Repo: github.com/dabiH2/heat-guard**

---

**Phoenix outdoor-crew supervisors decide who works from one city-wide forecast high. One
measured day: 643 phantom worker-hours of "unsafe exposure", a 92% over-count worth
≈$4,118/day as mandated rest alone [[EV:COST-02]] [[EV:COST-01]] to ≈$32,941/day as idle
labour [[EV:COST-01]].**

**Hero.** A Phoenix contractor's safety supervisor: one morning call — who works, who rotates,
who stops.

**Stakes.** 48 US workers died of environmental heat in 2024, 40 outdoors [[EV:HARM-01]]
[[EV:HARM-02]] — undercounted by OSHA's own factor of 14 [[EV:HARM-03]].

**Reach.** 154,320 outdoor workers in the Phoenix MSA [[EV:REACH-01]], 1,364,770 across 16 US
Sun Belt metros [[EV:REACH-02]] — bottom-up from BLS OEWS May 2025, arithmetic in
`docs/impact-evidence.md` §4. Jobs, not customers.

**Pain.** 87% of US contractors decide from forecasts, 13% from WBGT [[EV:PRAC-01]]
[[EV:PRAC-03]]. The free incumbent OSHA-NIOSH Heat Safety Tool identified 0% of high or extreme
risk against on-site WBGT [[EV:CTR-01]]. Nothing reports duration above a threshold, per site.

**Why duration.** Every occupational heat limit in force is defined as time at a condition
[[EV:NIOSH-01]] [[EV:ISO-01]]; NIOSH removed its peak-temperature ceiling in 2016
[[EV:NIOSH-02]]. A daily peak cannot be compared against any of them.

**Is AI required?** No. A **deterministic** decision table maps question to layer, states why,
and refuses when data cannot answer. The model narrates; it never picks layer, threshold or
date.

## The trap

`tcm` (peak) and `exceedance` are the **same endpoint, same `filter_type`, one optional string
apart.** Ask for hours above the band, leave the default, get a peak map: opposite decision,
**no error raised**. HeatGuard sets that string before any call.

## Measured result — this project's own

2025-07-15, OSHA high-risk band. One of twelve sites returned zero tiles (silent failure):
**11 sites, 107 workers**.

| | |
|---|---|
| Peak spread | **1.96 °F** — indistinguishable |
| Duration spread | **2.62 h** — **20× better** |
| City-wide, uniform | **701 worker-hours** |
| Scoped to real shifts | **58** |
| **Phantom exposure** | **643 — 92%** |
| Dangerous window | **13:00–20:00** — most shifts miss it |
| Worst site | not the hottest — **22 in that hour, not 18** |

## Built to be checked

**472 tests run offline — no key, no network** — against committed fixtures, so every number
above reproduces from a clean clone; the deployed app outlives the 21 September key expiry.
Six ways this API fails silently *while billing* are refused before the call.

**Over-warning is the expensive error and nobody counts it.** Every decision and refusal is
logged to `decisions.jsonl`; in an OSHA citation that record is the product.

**What is not proven. No customer discovery has happened.** Instead: named employers' sworn
testimony, OSHA docket OSHA-2021-0009 (12 hearing days, 2025), and two contractor surveys —
`docs/practice-and-efficacy-evidence.md`. The roster is constructed, not observed. No tool of
this class has been shown to reduce heat illness [[EV:EFF-01]] [[EV:EFF-02]]; OSHA is in the
same position — it states it is assuming its own 95%/65% figures [[EV:EFF-03]]. Per-site
prediction scored 2 of 11, worse than chance: the API separates urban core from periphery, not
surface type.

**AI disclosure.** Claude Code (Claude Opus 5) wrote code, tests and docs, ran the API probing.
I set the thesis, chose sites and thresholds, made every scoping call. The pitch video is mine.
