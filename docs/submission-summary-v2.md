# HeatGuard — written summary

*FortyGuard Hackathon'26 · Track 4 (Government & Environment) × Track 6 (Agentic)*

**Live demo: https://heat-fortyguard.streamlit.app/** · **Repo: github.com/dabiH2/heat-guard**
(`Hackathon-FG` added as collaborator, accepted 24 Aug)

---

**Phoenix outdoor-crew supervisors struggle to decide which crews can safely work, because
their only heat signal is one city-wide forecast high applied to every site, which results
in 643 phantom worker-hours of "unsafe exposure" on a single measured day: a 92% over-count
worth roughly $35,000 of unnecessary stop-work.**

**Hero.** The safety supervisor at a Phoenix contractor or municipal utility, making one call
each morning: who works, who rotates, who stops.

**Pain.** They read a daily forecast high, a *daytime maximum* measured at Sky Harbor, and
apply it uniformly. It says nothing about a specific site, and nothing about a 21:00–05:30
night crew. Nothing they use today reports duration above a threshold, per site.

**Is AI required?** No, and that is the design. The router is **deterministic**: a decision
table maps question to analysis layer, states why, and refuses when the data cannot answer.
The model narrates; it never picks a layer, threshold or date.

## The trap it exists to catch

`tcm` (peak) and `exceedance` (hours above threshold) are the **same endpoint, same
`filter_type`, same area, one optional string apart.** Ask "how long were they above the
band", let the default stand, and you get a well-formed peak-temperature map: opposite
operational decision, **no error raised**. HeatGuard picks that string before any call.

**Endpoints:** `/v1/heatmap` (`tcm`, `exceedance`, `persistence`, `filter_type` 2/3),
`/v1/env_params`, `/v1/status/{id}`, `/v1/system/fetch-api-key-usage`.

## Measured result

2025-07-15, OSHA high-risk band. Twelve sites, 115 workers; one returned zero tiles, a
documented silent failure, so figures are over **11 sites, 107 workers**:

| | |
|---|---|
| Peak spread, 11 sites | **1.96 °F** — indistinguishable |
| Duration spread | **2.62 h** — discriminates **20× better** |
| City-wide figure applied uniformly | **701 worker-hours** |
| Scoped to shifts crews actually work | **58** |
| **Phantom exposure removed** | **643 — 92%, ≈ $35k/day** |

The dangerous window ran 13:00–20:00; nearly every shift misses it. Eight sites tie at 7.0 h,
identical on any heat map. The worst site is not the hottest but the one with **22 people in
that hour instead of 18**.

## Built to be checked

**336 tests run offline, no API key, no network**, against committed fixtures, so every number
above reproduces from a clean clone. Six ways this API fails silently *while still billing*
are refused before the call, not handled after it. Every threshold crossing the API boundary
is unit-suffixed and converted in exactly one function, because an unconverted Fahrenheit
threshold returns **0.0 hours where the truth is 17.0**: `Completed`, billed, silent. The
deployed app serves those fixtures, so it still works after the key expires on 21 September.

**Why anyone would pay.** Over-warning is the expensive error and nobody counts it. Every
decision and refusal is logged to `decisions.jsonl`; in an OSHA citation that record is the
product. The method is not Phoenix-specific: the same calls run in any US metro the API
covers, against any roster with sites, shifts and headcount.

**What is not proven.** **No customer discovery has happened.** The roster is constructed, not
observed; the next step is five conversations with Phoenix safety supervisors before another
line of code. Per-site predictions also scored 2 of 11, worse than chance: the API separates
urban core from periphery, not surface type. The mechanism is measured; the demand is not.

**AI disclosure.** Claude Code (Claude Opus 5) wrote code, tests and documentation and ran the
API probing. I set the thesis, chose the sites and thresholds, and made every scoping call.
The pitch video is my own.
