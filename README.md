# HeatGuard

Per-site outdoor-worker heat safety for Phoenix job sites, built on the FortyGuard
Temperature API®.

A safety manager with twelve Phoenix sites decides each morning where crews can work.
Today that decision comes from a single city-wide forecast high. HeatGuard answers
per-site and per-hour using ground-level temperature — and refuses to answer when the
data cannot support the call.

> **Stub.** Written properly at T12, after the Aug 27 freeze. Must cover: what it does,
> how to run it, architecture, the layer-selection decision table, and disclosed AI usage.

## Why duration, not peak

OSHA documents outdoor-worker heat-stroke deaths at a daily maximum heat index of only
86 °F — inside the "Caution" band. Peak temperature is a poor predictor of harm.
Duration above a threshold is the signal. Ask a duration question, answer it with a
single-hour query, and you get the opposite operational decision.

## Quick start

```bash
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # paste your FortyGuard key
pytest                        # router tests run offline, no credits
streamlit run app.py
```
