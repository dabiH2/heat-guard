"""
app.py — the live surface.

The submission gates on "a live demo link — your working project", explicitly not a
prototype. An MCP server is not a live URL.

DEPLOY A SKELETON EARLY (T10, Aug 24) with a hardcoded result, then keep shipping to
the same URL. Deploying early turns a cliff into a slope.

Minimum viable surface:
  - pick a site, pick a date
  - hourly heat-index profile, hours above threshold, and the work/rotate/stop call
  - WHICH layer the router chose and WHY
  - a refusal, shown as a first-class outcome rather than an error

API KEY STAYS SERVER-SIDE. Never in client code, never in a video frame.
"""

import streamlit as st

st.set_page_config(page_title="HeatGuard", page_icon="🌡️", layout="wide")
st.title("🌡️ HeatGuard")
st.caption("Per-site outdoor-worker heat safety · FortyGuard Temperature API®")
st.info("Skeleton. T10 wires this to the router.")
