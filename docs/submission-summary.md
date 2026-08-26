# HeatGuard — written summary

*FortyGuard Hackathon'26 · Track 4 (Government & Environment) × Track 6 (Agentic)*

---

**Phoenix outdoor-crew supervisors struggle to decide which crews can safely work,
because the only heat signal they have is one city-wide forecast high applied to every
site, which results in 643 phantom worker-hours of "unsafe exposure" on a single measured
day — a 92% over-count that shuts down safe work while hiding the hour that actually
matters.**

**Hero.** The safety supervisor at a Phoenix contractor or municipal utility, making one
call each morning: who works, who rotates, who stops.

**Pain.** They read a daily forecast high — a *daytime maximum*, measured at Sky Harbor —
and apply it uniformly. It says nothing about a specific site, and nothing at all about a
21:00–05:30 night crew.

**Is AI generally required?** No — and that is the design. **HeatGuard's router is
deterministic**: a literal decision table maps question to analysis layer, states why, and
refuses when the data cannot answer. The model narrates; it never picks a layer,
threshold, or date. A test runs the same question with and without a model and asserts
every decisive field is identical. A safety tool whose recommendation depends on whether a
model was reachable is not a safety tool.

**Simplest version to prove the hypothesis in 24 hours.** One site, one date, two layers
side by side — the "⚠️ The trap" tab. It still runs.

## What it does

`/v1/heatmap` exposes `analytic_type`, and the choice is invisible. `tcm` (peak) and
`exceedance` (hours above threshold) are the **same endpoint, same `filter_type`, same
area — one optional string apart.** Ask "how long were they above the band", let the
default stand, and you get a well-formed peak-temperature map: opposite operational
decision, **no error raised**. HeatGuard picks that string before any call, and refuses
seven ways — including questions the API would answer, when the only layer that fits
would mislead.

**Endpoints:** `/v1/heatmap` (`tcm`, `exceedance`, `persistence`, `filter_type` 2/3),
`/v1/env_params` (humidity, for the heat-index → air-temperature conversion),
`/v1/status/{id}`, `/v1/system/fetch-api-key-usage`.

## Measured result

Twelve Phoenix sites, 2025-07-15, 107 workers, OSHA high-risk band:

| | |
|---|---|
| Peak spread across 11 sites | **1.96 °F** — indistinguishable |
| Duration spread | **2.62 h — 37%.** Duration discriminates **20× better** |
| City-wide figure applied uniformly | **701 unsafe worker-hours** |
| Scoped to shifts crews actually work | **58** |
| **Phantom exposure removed** | **643 worker-hours — 92%** |

The dangerous window ran 13:00–20:00; nearly every shift falls outside it. Eight sites tie
at 7.0 h — identical on any heat map. Scoped to shifts only four carry exposure, and the
worst is not the hottest site but the one with **22 people in that hour instead of 18**.

**What we got wrong, reported not buried:** our per-site predictions scored 2 of 11,
worse than chance — the API separates urban core from periphery, not surface type. Also
found: an unconverted Fahrenheit threshold returns **0.0 hours where the truth is 17.0** —
`Completed`, billed, silent. Five further silent-and-billed failure modes are documented
in `docs/api-notes.md`.

**AI disclosure:** built with Claude Code (Claude Opus 5) — code, tests, docs, API
probing. The pitch video is my own. Every finding was measured live and is reproducible
from committed fixtures.
