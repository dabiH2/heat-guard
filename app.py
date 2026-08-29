"""
app.py — the live surface.

The submission gates on a live demo link, and FortyGuard were explicit that it is what
judges actually open: *"the judges won't be opening the GitHub repositories that often
[…] what they will 100% open is your pitch, the live link."*

RUNS OFFLINE IN PRODUCTION. `HEATGUARD_OFFLINE=1` makes the deployed app serve entirely
from the committed fixture cache. That is not a degraded mode — it is the point:

  * the FortyGuard key expires 2026-09-21, judging runs to 2026-09-16, and a demo that
    dies with the key is a demo that dies during judging;
  * an offline app needs no API key at all, so there is no secret to leak into a public
    Streamlit deployment, and no key visible in a demo video frame.

The layout follows the argument rather than the data model. A judge should be able to see,
without reading any code: which layer was chosen, why that one, what the alternative would
have said, and what the supervisor should do.

API KEY STAYS SERVER-SIDE. Never in client code, never in a video frame.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date as _date
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

# ---------------------------------------------------------------------------
# OFFLINE BY DEFAULT. Opt IN to spending money, never opt out.
# ---------------------------------------------------------------------------
# A deployed app that can reach the API is a deployed app that can be made to spend
# 4,220 credits per click. Twelve sites and a few dates of idle clicking by a judge would
# be tens of thousands of credits, and there is no rate limit between them and the budget.
#
# So the default is offline, and going online requires setting HEATGUARD_ONLINE=1
# explicitly — which only ever happens on a developer machine. The deployed instance
# therefore needs no API key at all: nothing to leak, nothing to appear in a video frame,
# and nothing that breaks when the key expires on 2026-09-21.
if os.environ.get("HEATGUARD_ONLINE", "").strip().lower() not in ("1", "true", "yes"):
    os.environ["HEATGUARD_OFFLINE"] = "1"

from heatguard import tools                                    # noqa: E402
from heatguard import agent                                    # noqa: E402
from heatguard import ask                                      # noqa: E402
from heatguard.agent import answer, load_sites                 # noqa: E402
from heatguard import charts                                  # noqa: E402
# `band_for` / `action_for` are no longer imported here. The Ask tab used to key its
# heading on `action_for(peak_f)` and disagree with the morning sheet about the same crew
# on the same day; band and action selection now happens in `heatguard.ask`, which is pure
# and testable, and this file only renders what it returns.
from heatguard.bands import load_thresholds                    # noqa: E402
from heatguard import evidence                                 # noqa: E402
from heatguard import theme                                    # noqa: E402
from heatguard.router import AnalyticType, RefusalReason, route       # noqa: E402

#: Nine real records, generated offline and committed, so the audit-trail view is
#: never empty on a cold container.
DECISIONS_SAMPLE = Path(__file__).resolve().parent / "data" / "decisions.sample.jsonl"

st.set_page_config(page_title="HeatGuard", page_icon="🌡️", layout="wide")
theme.inject(st)

# ---------------------------------------------------------------------------
# EVERY EXTERNAL FIGURE ON THIS PAGE ARRIVES THROUGH HERE.
# ---------------------------------------------------------------------------
# Streamlit re-executes this file top to bottom on every interaction, so this is a FRESH
# log per pass. That is what lets the Sources block at the foot list exactly the claims
# the reader is looking at rather than the whole thirty-claim registry.
#
# The distinction it enforces is the one this project cares about most: a figure with a
# source link belongs to somebody else's document, and a figure with no link was measured
# here from the committed fixtures. Nothing measured borrows an external citation, and
# nothing external is presented as measured.
SOURCES = evidence.CitationLog()

#: COST-01 — BLS Employer Costs for Employee Compensation, construction industry, total
#: compensation per hour worked (wages $35.54 + benefits $15.69), March 2026. It stays a
#: SLIDER: a published default is worth more than an invented one, and a buyer who
#: disagrees should be able to move it and watch the number change.
DEFAULT_LOADED_RATE_USD_PER_HOUR = 51.23

#: COST-02 — the share of paid time owed as mandated rest at OSHA's PROPOSED high heat
#: trigger: 15 minutes per 120 = 12.5%. Arithmetic on the proposed regulatory text, not a
#: published figure, and the underlying break provision is NOT IN FORCE (REG-02).
MANDATED_REST_FRACTION = 0.125

# The demo day and the sites whose data is committed to the cache. Anything outside this
# set cannot be answered offline, so the UI does not offer it.
DEMO_DATE = "2025-07-15"

# Reported at both, because the number changes materially between them. The labels are
# deliberately short: this is a control in a working form, not a place to teach OSHA.
THRESHOLD_CHOICES = {
    "91 °F · OSHA moderate": 91.0,
    "103 °F · OSHA high": 103.0,
}
#: 103 °F. It is the threshold `data/fixtures/t8/shift_exposure_*.json` was measured at,
#: so it is the only one where hours INSIDE a crew's shift are a measurement rather than
#: a pigeonhole floor — and a default that lands on the weaker of two available answers
#: teaches the tool is weaker than it is.
DEFAULT_THRESHOLD_INDEX = 1


@st.cache_data
def sites():
    return load_sites()


@st.cache_data
def cached_dates() -> list[str]:
    """Dates the fixture cache can answer END TO END, newest first.

    Not every date present in the index is a date the app can be *asked about*.
    2025-07-16 appears only as the post-midnight tail of night shifts that START on the
    15th: five `exceedance` calls with `filter_type=2`, and no `env_params` at all. It is
    an artefact of a window wrapping past midnight, not a demo day.

    Offering it in the Date box meant the first question a judge would ask — "how hot is
    it right now" — routed to the snapshot layer, found no heat index in the cache, and
    killed the app with a KeyError. Reported live.

    So a date is offered only when the cache holds BOTH endpoints the question set needs.
    Presence in the index is not the same as answerability, and the dropdown is a promise.
    """
    combos = tools.cached_combinations()
    with_env = {p["date"] for p in combos
                if p.get("date") and p.get("endpoint") == "/v1/env_params"}
    with_map = {p["date"] for p in combos
                if p.get("date") and p.get("endpoint") == "/v1/heatmap"}
    return sorted(with_env & with_map, reverse=True)


def _decision_files() -> list[Path]:
    """The live log first, then the committed sample.

    The live file is gitignored and the deployed container's copy is ephemeral, so on a
    cold Streamlit Cloud boot it does not exist at all. The sample is nine real records
    generated offline and committed precisely so the tab is never empty for a judge who
    arrives before clicking anything.
    """
    return [p for p in (agent.DECISIONS_LOG, DECISIONS_SAMPLE) if p.exists()]


def recent_decisions(limit: int = 25) -> list[dict]:
    """Most recent first. Deliberately NOT cached — the whole point is that a question
    asked ten seconds ago shows up."""
    rows: list[dict] = []
    for path in _decision_files():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue          # a half-written final line is not worth a crash
        if rows:
            break                 # the live log wins outright when it has anything
    return list(reversed(rows))[:limit]


def decisions_bytes() -> bytes:
    for path in _decision_files():
        raw = path.read_bytes()
        if raw.strip():
            return raw
    return b""


def offline() -> bool:
    return tools.offline()


# ============================================================================ header

st.title("🌡️ HeatGuard")
st.caption(
    "Per-site outdoor-worker heat safety for Phoenix job sites · "
    "built on the FortyGuard Temperature API®"
)

if offline():
    st.info(
        "**Serving from the cached fixture set.** The FortyGuard hackathon key expires "
        "21 September and judging runs to the 16th, so every result shown here was "
        "captured live and committed to the repository. Nothing on this page depends on "
        "the API still being reachable.",
        icon="📦",
    )

# ---------------------------------------------------------------------------
# THE THESIS. It used to read "Peak temperature is a poor predictor of harm. Duration
# above a threshold is the signal." That was not supportable and it is now gone: no
# occupational study has ever used hours-above-threshold as an exposure variable, the one
# worker study testing hourly WBGT was null, and the largest US intensity-vs-duration test
# found intensity significant and duration not. Asserting it in front of a judge who knows
# the literature loses more than the sentence was ever worth.
#
# What replaces it is a claim about the ARCHITECTURE OF THE STANDARDS, not about
# epidemiology — and that claim is airtight, because the limits say so in their own text.
# Every one of them is written as time at a condition, and the peak limit that a daily
# maximum could have been compared against was withdrawn in 2016.
st.markdown(
    f"> **A safety manager with twelve Phoenix sites decides each morning where crews can "
    f"work.** Today that decision comes from a single city-wide forecast high. "
    f"OSHA records outdoor-worker heat-stroke deaths at a daily maximum heat index of "
    f"only **86 °F** — inside the *Caution* band ({SOURCES.link('HARM-04')}). OSHA's own "
    f"instruction on that forecast is blunt: *do not rely solely on the Heat Index "
    f"reported by weather forecasts for your safety at work, as it may underestimate your "
    f"actual risk* ({SOURCES.link('CTR-06')})."
)
st.markdown(
    f"> **Every occupational heat limit in force is defined as *time at a condition*, not "
    f"as a peak.** NIOSH's Recommended Alert Limit and Recommended Exposure Limit are "
    f"expressed as one-hour time-weighted averages and published for 60, 45, 30 and 15 "
    f"minute work periods ({SOURCES.link('NIOSH-01')}). ACGIH's TLV has the same shape — "
    f"work allocated per hour at a given WBGT ({SOURCES.link('ACGIH-01')}) — "
    f"and ISO 7933's output is a maximum allowable exposure *time* rather than a "
    f"temperature ceiling ({SOURCES.link('ISO-01')}). NIOSH removed its ceiling limit "
    f"recommendations in 2016 ({SOURCES.link('NIOSH-02')}), so there is no peak limit left "
    f"to compare a daily maximum against at all. **A daily peak cannot be checked against "
    f"any of them. Hours above a threshold can.**"
)

# The colour key for the whole app, shown ONCE, above the tabs, next to the sentence it
# proves. Two jobs, and it would not be worth the pixels for either alone:
#   1. It defines the vocabulary. Every severity chip below uses these colours and no
#      others, so a reader learns the language here and never needs a legend again.
#   2. It makes the argument visible. The claim is that people die at 86 °F. Seeing that
#      86 falls in the SECOND of five bands -- amber, nowhere near the red end -- lands
#      faster than the sentence does.
st.markdown(theme.heat_scale_legend(), unsafe_allow_html=True)

# The second legend on the page, and it does the same job for evidence that the colour key
# does for severity: it defines the vocabulary once, so no figure below needs a footnote.
# Blurring the two kinds of number is the easiest way for a project like this to overclaim
# — a measured result quietly wearing somebody else's authority — so the distinction is
# stated up front and then held to everywhere.
st.caption(
    "**Two kinds of number appear below, and they are marked differently.** A figure "
    "carrying a **source link** is somebody else's published work, and the link goes to "
    "it. A figure with **no link** was measured by this project from its own committed "
    "fixtures — the peak spread, the worker-hours, the 92%, the 17 hours in the unit trap, "
    "the credits per call. Nothing measured here borrows an external citation, and nothing "
    "external is presented as measured. Every linked claim is listed with its data year "
    "under **Sources**, at the foot of the page."
)

today_tab, decision_tab, trap_tab, method_tab = st.tabs(
    ["📋 The morning call", "Ask a question", "⚠️ The trap", "How it decides"]
)


@st.cache_data
def shift_exposure(date: str) -> dict | None:
    path = (Path(__file__).parent / "data" / "fixtures" / "t8"
            / f"shift_exposure_{date}.json")
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data
def day_analysis(date: str) -> dict | None:
    """The whole-day companion to shift_exposure(): peaks and 91 °F hours per site.

    Separate fixture because it answers a different question. shift_exposure knows what
    happened INSIDE each crew's hours; this knows what happened across the whole day, and
    the call sheet needs both to show that they disagree.
    """
    path = (Path(__file__).parent / "data" / "fixtures" / "t8"
            / f"analysis_{date}.json")
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


#: OSHA's rungs in the words a foreman uses. The raw enum (`rest_breaks_50_10`) is a
#: database value, not an instruction, and a plan that goes to a crew has to be readable
#: by the crew.
CALL_TEXT = {
    "rest_breaks_50_10": "50:10 work/rest",
    "rest_breaks_55_5": "55:5 work/rest",
    "no_reading": "NO READING",
}


def _measured_window(shift: str, night: bool) -> tuple[str, float, float]:
    """What was actually measured, against what was rostered.

    `scripts/build_shift_exposure.py:hhmm` floors BOTH shift edges to the hour, because
    the API takes whole hours. Its docstring says it rounds "outward so exposure is never
    under-counted" — it does not; both branches floor, so a shift ENDING at 13:30 was
    measured to 13:00 and the last half hour was never looked at.

    That matters more than it sounds. For the day crews the lost sliver sits at the END of
    the shift, which on a Phoenix July day is the hottest part of it. So this returns the
    unmeasured remainder explicitly and the UI prints it, because the alternative is a
    sheet that silently reports a shift it did not fully measure.

    Returns (human label, measured hours, unmeasured hours).
    """
    start, end = shift.split("-")

    def floor(t: str) -> tuple[int, int]:
        h, m = (int(x) for x in t.split(":"))
        return h, m

    sh, sm = floor(start)
    eh, em = floor(end)

    if night:
        # Two calls: start→23:00 on the date, then 00:00→end on the following day. The
        # 23:00–00:00 hour is in neither, which is why these lose more than a day shift.
        measured = (23 - sh) + eh
        rostered = ((24 - sh - sm / 60) + (eh + em / 60))
        label = f"{sh:02d}:00–23:00 + 00:00–{eh:02d}:00"
    else:
        measured = eh - sh
        rostered = (eh + em / 60) - (sh + sm / 60)
        label = f"{sh:02d}:00–{eh:02d}:00"

    unmeasured = max(0.0, rostered - measured)
    label += (" · covers the shift" if unmeasured < 0.01
              else f" · {unmeasured:.1f} h unmeasured")
    return label, float(measured), float(unmeasured)


def _bound_91(shift_hours: float, hours_91: float, night: bool) -> float | None:
    """A FLOOR on hours above 91 °F inside the shift, by pigeonhole. Not a measurement.

    If a site was above 91 °F for H of 24 hours, a shift of length L must overlap at
    least L - (24 - H) of them, whatever order the hours came in. That is arithmetic on a
    measured total, so it is honest — but it is a lower bound and every rendering of it
    says "at least".

    Returns None for night shifts. The bound needs the whole-day total for the SAME 24
    hours the shift spans, and a shift crossing midnight spans two dates. The cache holds
    16 July only as the post-midnight tail of these very shifts, so there is no whole-day
    figure for it. Printing a number here would mean extending a 15 July measurement
    across a day nobody measured.
    """
    if night:
        return None
    return max(0.0, shift_hours - (24.0 - hours_91))


def _call_for(row: dict, analysis_row: dict | None) -> tuple[str, str]:
    """The verdict for one crew. The ONLY place a call is decided.

    Keyed on hours above threshold INSIDE the crew's own shift window — deliberately not
    on `action_for(peak_f)`. Ten of the twelve sites peak within 1.9 °F of one another, so
    a peak-driven ladder returns the same rung for almost every crew and the sheet
    degenerates into one call printed twelve times. Which is exactly the failure this
    whole project is an argument against: the peak does not separate these sites, and the
    hours inside the shift do.
    """
    if analysis_row is None or analysis_row.get("empty") or row["whole_day_hours"] <= 0:
        return "no_reading", CALL_TEXT["no_reading"]
    if row["in_shift_hours"] > 0:
        return "rest_breaks_50_10", CALL_TEXT["rest_breaks_50_10"]
    return "rest_breaks_55_5", CALL_TEXT["rest_breaks_55_5"]



def plan_text(date: str, sheet: list[dict], threshold_f: float) -> str:
    """The one-page dated shift plan. Pure string builder — no Streamlit, so it is
    testable, and identical whether it is downloaded or printed.

    This is the object that LEAVES the browser. Everything else on the page argues; this
    is what a foreman reads at 05:00 and what sits in the file if an inspector ever asks
    what the employer knew and when. So it carries the calls, the measurement behind each
    one, the method, and — the part most tools omit — what was NOT measured.
    """
    fifty = [r for r in sheet if r["call_id"] == "rest_breaks_50_10"]
    fives = [r for r in sheet if r["call_id"] == "rest_breaks_55_5"]
    none_ = [r for r in sheet if r["call_id"] == "no_reading"]
    width = 78

    out = [
        "=" * width,
        f"HEAT EXPOSURE SHIFT PLAN — {date}",
        "Phoenix, Arizona · prepared by HeatGuard",
        "=" * width,
        "",
        f"DECISION THRESHOLD: {threshold_f:.0f} °F heat index, measured inside each",
        "crew's own shift window — not the day's peak, and not a city-wide forecast.",
        "",
        f"{len(fifty)} crew(s) on 50:10 work/rest · {len(fives)} on 55:5 · "
        f"{len(none_)} with no reading",
        "",
        "-" * width,
        "THE CALLS",
        "-" * width,
    ]

    for r in sheet:
        out += [
            "",
            f"  {r['Crew']}",
            f"    Call ................ {r['Call today']}",
            f"    Crew size ........... {r['Crew size']}",
            f"    Rostered shift ...... {r['Shift']}",
            f"    Window measured ..... {r['Window measured']}",
            f"    >= {threshold_f:.0f} °F in shift ... {r[f'>={threshold_f:.0f} °F in shift']}",
            f"    >= {threshold_f:.0f} °F all day ... {r[f'>={threshold_f:.0f} °F all day']}",
        ]

    out += [
        "",
        "-" * width,
        "METHOD",
        "-" * width,
        "",
        "  Source .......... FortyGuard Temperature API, /v1/heatmap",
        "  Analysis layer .. analytic_type=exceedance (hours above a threshold),",
        "                    NOT analytic_type=tcm (a single temperature).",
        "  Resolution ...... 20 m native, measured 2 m above ground.",
        "  Captured ........ live and committed; no figure here is modelled.",
        "",
        "  The threshold is a heat index in Fahrenheit. The API takes air temperature",
        "  in Celsius. Conversion is done per site at that site's measured humidity.",
        "",
        "-" * width,
        "WHAT WAS NOT MEASURED — read this before relying on the plan",
        "-" * width,
        "",
        "  1. UNMEASURED WINDOWS. The API takes whole hours, so each shift edge was",
        "     floored to the hour. Crews marked with unmeasured time above have minutes",
        "     at the edge of the shift that were never looked at. For day shifts that",
        "     sliver falls at the END of the shift, which in a Phoenix July is the",
        "     hottest part of it. Those minutes are UNMEASURED, NOT CLEAR.",
        "",
        "  2. NO READING IS NOT AN ALL-CLEAR. Where the call reads NO READING the API",
        "     returned zero tiles for that area on that date. Status: Completed. Cost:",
        "     4,220 credits. A coverage gap is not a safe reading, and this plan will",
        "     not convert one into the other. Those crews stay on the standing plan.",
        "",
        "  3. COUNTS, NOT TIMES. This reports HOW MANY hours were above the threshold,",
        "     not WHICH hours. Locating them needs an analysis layer that was not",
        "     captured for this date, so each control applies shift-wide.",
        "",
        "  4. HEAT INDEX, NOT WBGT. OSHA regulates against wet bulb globe temperature.",
        "     This plan does not model crew acclimatisation or workload. It is decision",
        "     support and does not replace a heat-illness prevention program.",
        "",
        "-" * width,
        "ACKNOWLEDGEMENT",
        "-" * width,
        "",
        "  Issued by ......................................  Time ................",
        "",
        "  Received by ....................................  Time ................",
        "",
        "=" * width,
        f"Generated by HeatGuard from measurements taken on {date}.",
        "=" * width,
        "",
    ]
    return "\n".join(out)


# ========================================================== the roster-wide headline

with today_tab:
    data = shift_exposure(DEMO_DATE)
    if data is None:
        st.warning("Roster exposure for the demo day has not been captured yet.")
    else:
        rows = [r for r in data["rows"] if r["whole_day_hours"] > 0]
        naive = sum(r["whole_day_hours"] * r["crew"] for r in rows)
        actual = sum(r["worker_hours"] for r in rows)
        crews = sum(r["crew"] for r in rows)

        # ------------------------------------------------------------ the call sheet
        # This is the product. Everything below it is the argument for why the calls are
        # what they are; a supervisor at 04:40 needs the calls, and needs them without
        # clicking anything.
        analysis = day_analysis(DEMO_DATE) or {"rows": [], "empty": []}
        arows = {r["site_id"]: r for r in analysis["rows"]}
        roster_csv = sites()
        threshold_f = data["threshold_f_heat_index"]
        all_rows = data["rows"]
        headcount = sum(r["crew"] for r in all_rows)

        sheet = []
        for r in all_rows:
            call_id, call_text = _call_for(r, arows.get(r["site_id"]))
            window, measured_h, unmeasured_h = _measured_window(r["shift"], r["night"])
            site_cfg = roster_csv.get(r["site_id"], {})
            # The ROSTERED length, not the measured one. The crew is outside for the
            # whole shift whether or not the API looked at all of it, and the pigeonhole
            # bound is a statement about the crew's exposure, not about our coverage.
            rostered_h = float(site_cfg.get("shift_hours") or measured_h)
            ar = arows.get(r["site_id"])
            has_data = ar is not None and not ar.get("empty")
            bound = (_bound_91(rostered_h, ar["hours_91"], r["night"])
                     if has_data else None)

            sheet.append({
                "call_id": call_id,
                "_crew_n": r["crew"],
                "Crew": r["name"],
                "Crew size": r["crew"],
                "Shift": r["shift"] + (" 🌙" if r["night"] else ""),
                "Call today": call_text,
                f">={threshold_f:.0f} °F in shift":
                    f"{r['in_shift_hours']:.1f} h" if has_data else "—",
                f">={threshold_f:.0f} °F all day":
                    f"{r['whole_day_hours']:.1f} h" if has_data else "—",
                "Window measured": window if has_data else "none — zero tiles returned",
                ">=91 °F in shift": (
                    "not derivable — shift crosses midnight" if has_data and r["night"]
                    else f"at least {bound:.1f} of {rostered_h:.1f} h" if has_data
                    else "—"),
            })

        _ORDER = {"rest_breaks_50_10": 0, "rest_breaks_55_5": 1, "no_reading": 2}
        sheet.sort(key=lambda x: (_ORDER[x["call_id"]], -x["_crew_n"], x["Crew"]))

        fifty = [x for x in sheet if x["call_id"] == "rest_breaks_50_10"]
        fives = [x for x in sheet if x["call_id"] == "rest_breaks_55_5"]
        nodata = [x for x in sheet if x["call_id"] == "no_reading"]

        st.subheader(
            f"{DEMO_DATE} · {len(sheet)} crews · {headcount} workers · "
            f"decision threshold {threshold_f:.0f} °F heat index"
        )

        chip_cols = st.columns(3)
        for col, group, band_id, label in (
            (chip_cols[0], fifty, "high", "50:10 work/rest"),
            (chip_cols[1], fives, "moderate", "55:5 work/rest"),
            (chip_cols[2], nodata, "below_caution", "no reading"),
        ):
            col.markdown(
                theme.band_chip(
                    band_id,
                    f"{len(group)} crew{'' if len(group) == 1 else 's'} · "
                    f"{sum(x['_crew_n'] for x in group)} workers — {label}"),
                unsafe_allow_html=True)

        _named = ", ".join(f"{x['Crew'].split(',')[0]} ({x['_crew_n']})" for x in fifty)
        st.success(
            f"**{len(fifty)} crews move to 50:10 work/rest today; {len(fives)} run 55:5; "
            f"{len(nodata)} has no reading.**\n\n"
            f"{_named} each crossed {threshold_f:.0f} °F heat index *inside their own "
            f"shift hours*. The other {len(fives)} crews with coverage never did.\n\n"
            f"**Nobody reaches the stop line.** OSHA's `stop_nonessential` rung starts at "
            f"115 °F heat index and today's highest site peak is 104.5 °F, so no crew on "
            f"this roster stops. The ladder has that rung and today it is empty — a tool "
            f"that always finds a reason to stop work gets switched off by March.",
            icon="✅",
        )

        st.markdown(
            f"**The rule, applied identically to every crew:**\n\n"
            f"- {threshold_f:.0f} °F heat index crossed **inside the crew's own shift "
            f"window** → 50:10 work/rest for the shift.\n"
            f"- Not crossed inside the shift → 55:5 work/rest for the shift.\n"
            f"- No tiles returned → **no call, and no all-clear.**\n\n"
            f"The rung follows the hours the crew is actually outside, not the day's "
            f"peak. Ten of the eleven sites with coverage peak within **1.9 °F** of one "
            f"another, so a peak-driven call is the same call eleven times."
        )
        st.caption(load_thresholds().disclaimer)

        st.dataframe(
            [{k: v for k, v in row.items() if not k.startswith(("call_id", "_"))}
             for row in sheet],
            use_container_width=True, hide_index=True,
        )

        st.caption(
            "**\"Window measured\" is not the rostered shift.** The API takes whole "
            "hours, so each shift edge was floored when the call was made. Crews showing "
            "unmeasured time have minutes at the edge of the shift that were never looked "
            "at — and for the day crews that sliver falls at the *end* of the shift, "
            "which in a Phoenix July is the hottest part of it. **Unmeasured, not clear.**"
        )
        st.caption(
            "**55:5 is not a per-crew finding.** Every crew with coverage is above 91 °F "
            "for part of its shift on this day, so the lower rung is a Phoenix July "
            "constant — `config/thresholds.yaml` predicted exactly that. The column is "
            "shown because the *bound* is honest arithmetic on a measured total, and it "
            "says \"at least\" for the same reason."
        )
        st.caption(
            "**A count, not a schedule.** This reports how many hours were above the "
            "threshold, not which ones. Locating them needs `analytic_type="
            "time_of_measure`, which was not captured for this date, so each control "
            "applies shift-wide."
        )

        if nodata:
            st.warning(
                f"**{nodata[0]['Crew']} has no reading, and that is not an all-clear.** "
                f"The API returned zero tiles for this area on this date. Status: "
                f"`Completed`. Cost: **4,220 credits**. A coverage gap billed at full "
                f"price is one of six failure modes that return a plausible-looking "
                f"result — this crew stays on the standing plan, and HeatGuard will not "
                f"turn silence into safety.", icon="⚠️")

        st.download_button(
            "⬇  Download the shift plan for 05:00",
            data=plan_text(DEMO_DATE, sheet, threshold_f),
            file_name=f"heat-plan-{DEMO_DATE}.txt",
            mime="text/plain",
            type="primary",
            help="One page. The calls, the measurement behind each one, the method, what "
                 "was NOT measured, and a signature line. This is the artefact that "
                 "leaves the browser.",
        )

        st.divider()

        # ------------------------------------ why the calls differ from the forecast
        st.markdown("#### Why the calls differ from the forecast")
        st.markdown(
            f"Every site on the roster peaked between **102.6 and 104.5 °F** — a spread "
            f"of **1.9 °F**. By peak alone they are the same day at the same place, and "
            f"a city-wide figure would call all of them dangerous."
        )

        a, b, c = st.columns(3)
        # Units live in the label, not the value: Streamlit truncates long metric
        # values in narrow columns, and "701 worker-…" is useless in a video frame.
        a.metric("City-wide figure · worker-hours", f"{naive:,.0f}",
                 help=f"{data['threshold_f_heat_index']:.0f} °F heat index, whole day, "
                      f"every crew, applied uniformly.")
        b.metric("Scoped to real shifts · worker-hours", f"{actual:,.0f}",
                 delta=f"-{naive - actual:,.0f}", delta_color="inverse",
                 help="Only the hours crews were actually outside.")
        c.metric("Over-count", f"{(naive - actual) / naive * 100:.0f}%",
                 help="Exposure nobody was ever standing in.")

        st.success(
            f"**{naive - actual:,.0f} worker-hours of 'unsafe exposure' that nobody was "
            f"standing in.** The dangerous window on this day runs roughly 13:00–20:00 — "
            f"almost entirely outside every shift on the roster. A city-wide call to stop "
            f"work would have been {(naive - actual) / naive * 100:.0f}% wrong, and "
            f"expensive.",
            icon="✅",
        )

        st.caption(
            f"**Measured here, and deliberately uncited.** The 1.9 °F peak spread, the "
            f"{naive:,.0f} → {actual:,.0f} worker-hours and the "
            f"{(naive - actual) / naive * 100:.0f}% over-count come from this project's "
            f"own committed fixture set for {DEMO_DATE}, not from anybody's publication. "
            f"They carry no source link because there is nothing external to link to, and "
            f"attaching one would be borrowing authority the figures do not need. The "
            f"external claims on this page are the ones with links; they are listed under "
            f"**Sources** at the foot."
        )

        # ------------------------------------------------------ what that is worth
        # The safety argument competes with a free NWS forecast and loses. The two
        # arguments that survive contact with a buyer are cost avoidance and defensible
        # documentation, and both use numbers already measured above.
        #
        # The dollar figure is DERIVED, not measured, so the rate is exposed as a control
        # rather than baked in. It used to default to an invented 55 — the only uncited
        # number in the whole submission. It now defaults to the BLS figure for the
        # construction industry and says so next to the control, which is both smaller and
        # worth more: a judge can check it, and can still move it.
        #
        # And the output is a RANGE, not a point. A single figure assumes the employer
        # stops work outright, which is the aggressive reading and the one the mandate
        # objection defeats: at the proposed high heat trigger what is owed is paid rest,
        # not a stoppage. So the floor values the phantom hours at the mandated rest
        # fraction alone, the ceiling values them as fully idle loaded labour, and the page
        # says the truth is between them rather than picking the flattering end.
        st.markdown("#### What that is worth")
        rate = st.slider(
            "Loaded labour rate, $/hour",
            min_value=25.0, max_value=100.0,
            value=DEFAULT_LOADED_RATE_USD_PER_HOUR, step=0.01, format="$%.2f",
            help="Wage plus burden — payroll tax, insurance, equipment standing idle. "
                 "The default is a published BLS figure for the construction industry, "
                 "not our assumption. Move it: both bounds scale linearly, and the "
                 "assumption is then yours.",
        )
        st.caption(
            f"Default: {SOURCES.cite('COST-01')} — total compensation per hour worked, "
            f"construction industry, wages plus benefits. It stays a slider because a "
            f"buyer who disagrees with the rate should be able to move it and watch both "
            f"bounds move with it."
        )

        phantom = naive - actual
        cost_floor = phantom * MANDATED_REST_FRACTION * rate
        cost_ceiling = phantom * rate

        money_a, money_b, money_c = st.columns(3)
        money_a.metric(
            "Floor · mandated rest only",
            f"${cost_floor:,.0f}",
            help=f"{phantom:,.0f} phantom worker-hours × 12.5% × ${rate:,.2f}/h. What is "
                 f"owed as paid rest even while the crew keeps working.",
        )
        money_b.metric(
            "Ceiling · fully idle labour",
            f"${cost_ceiling:,.0f}",
            help=f"{phantom:,.0f} phantom worker-hours × ${rate:,.2f}/h. What a full "
                 f"precautionary stop-work would cost. One day, one roster.",
        )
        money_c.metric(
            "Cost of being wrong the other way",
            "one heat-illness claim",
            help="An OSHA citation, a workers' compensation claim, or a fatality "
                 "investigation. HeatGuard does not price this — it documents the "
                 "decision instead.",
        )

        st.markdown(
            f"**The truth is between \\${cost_floor:,.0f} and \\${cost_ceiling:,.0f}, and "
            f"which end depends on what the employer actually does.** The floor values the "
            f"{phantom:,.0f} phantom worker-hours only as paid rest that would have been "
            f"owed anyway — {SOURCES.cite('COST-02')} — and it is the bound that survives "
            f"the objection that a heat trigger does not license stopping work at all. The "
            f"ceiling values the same hours as fully idle loaded labour. **No published "
            f"figure exists for the cost of a precautionary work stoppage**, so neither "
            f"end is a measured cost of stoppage and this page does not present one as if "
            f"it were."
        )
        st.warning(
            f"**The break provision the floor rests on is PROPOSED, and not in force.** "
            f"The federal heat standard is {SOURCES.cite('REG-02')} The control it would "
            f"impose at the high heat trigger is {SOURCES.cite('REG-05')}. Read the floor "
            f"as what the obligation would cost under the rule as proposed — never as a "
            f"requirement currently binding on an employer.",
            icon="⚠️",
        )

        st.info(
            f"**Over-warning is the expensive error, and it is the one nobody counts.** "
            f"Stopping work costs money on a day nobody was at risk; the "
            # Dollar signs are escaped: Streamlit reads $…$ as LaTeX math, which silently
            # eats both the currency symbol and the bold markers around it.
            f"{naive - actual:,.0f} worker-hours above are **\\${cost_floor:,.0f} to "
            f"\\${cost_ceiling:,.0f}** at \\${rate:,.2f}/h. Under-warning costs a claim — "
            f"rarer, far worse, and the reason the tool refuses rather than guesses.\n\n"
            f"**Every decision here is written to `data/decisions.jsonl`** — question, "
            f"layer chosen, why, threshold, result, action, timestamp. That file is the "
            f"product as much as the number is: in a citation or a comp dispute, what "
            f"protects a supervisor is evidence they followed a consistent, documented "
            f"process. A screenshot of a weather app is not that.",
            icon="💷",
        )

        st.markdown("#### The day, hour by hour")
        st.markdown(
            "Each bar is one crew's shift. The red band is the only window that was "
            "actually above threshold. **Almost every shift misses it** — that is the "
            "92% in one picture."
        )
        st.markdown(charts.the_day(rows,
                                   threshold_f=data["threshold_f_heat_index"]),
                    unsafe_allow_html=True)
        st.caption(
            "Night shifts cross midnight and are drawn as two segments on a single "
            "00:00–24:00 axis — the crew really is outside during both."
        )

        st.caption(
            f"Threshold {data['threshold_f_heat_index']:.0f} °F heat index, converted "
            f"per site to the equivalent air temperature at that site's measured "
            f"humidity. Night shifts are measured across two calls because a shift "
            f"crossing midnight cannot be one hour range."
        )

        st.markdown("---")
        st.markdown("#### The twelve sites and their predictions")
        st.markdown(
            "Each site carried a **falsifiable prediction** written before any data was "
            "fetched. **Two of eleven came true — worse than chance.** They are reported "
            "rather than dropped, because `docs/site_selection.md` committed to reporting "
            "them and a roster where every prediction held would be evidence of tuning."
        )
        roster_all = sites()
        st.dataframe(
            [
                {
                    "Site": s["name"], "Archetype": s["archetype"],
                    "Predicted": s["expected_profile"], "Crew": int(s["crew_size"]),
                    "Shift": f"{s['shift_start']}–{s['shift_end']}",
                    "Night": "🌙" if s["night_shift"] == "True" else "",
                }
                for s in roster_all.values()
            ],
            use_container_width=True, hide_index=True,
        )
        st.markdown(
            "**What the data actually separates is urban core from periphery, not "
            "surface type.** The three sites that differ — South Mountain, Estrella, "
            "Union Hills — are the three outermost. Downtown canyon, airfield asphalt "
            "and irrigated park within the core return the same numbers as each other. "
            "At 20 m native resolution over a 400 m area, the regional heat-island "
            "gradient dominates street-level surface differences. The thesis survives "
            "that; the site-selection hypothesis does not."
        )
def _render_mechanism(choice, result: dict | None, *, ranked_over: int = 0) -> None:
    """The audit trail for the answer directly above it. Collapsed, structured, adjacent.

    ADJACENT, not filed elsewhere. This used to be a run of headings, an info box, a
    four-column parameter row and two separate expanders spread down the page, which meant
    a reader checking one number had to scroll past three paragraphs to find out how it
    was produced. It is now one expander whose label already names the layer, holding a
    definition list — every row a fact about THIS answer.

    A table rather than prose on purpose: the brief is that the mechanism be auditable,
    and an auditor reads rows, not paragraphs.
    """
    rows = ask.mechanism_rows(choice, result, ranked_over=ranked_over)
    if choice.refused:
        read_as = (choice.question_type.value if choice.question_type
                   else "not recognised")
        label = f"⚙  Mechanism · {read_as} → refused, no call made"
    else:
        label = (f"⚙  Mechanism · {choice.question_type.value} → "
                 f"analytic_type={choice.analytic_type.value}, "
                 f"filter_type={choice.filter_type}")
    with st.expander(label):
        st.table({"Step": [name for name, _ in rows],
                  "This answer": [value for _, value in rows]})


def _render_answer(facts: list, date: str, question: str,
                   threshold_f: float, preview) -> None:
    """Run the plan the router already chose, and render the outcome.

    ⚠️ EVERY EARLY EXIT HERE IS `return`, NEVER `st.stop()`.

    `st.stop()` halts the ENTIRE script run, not the current tab or column. Because
    Streamlit executes this file top to bottom on every interaction, a stop inside the
    "Ask a question" tab silently prevented every tab defined LATER in the file — "The
    trap" and "How it decides" — from being populated at all. They only appeared once the
    button was pressed and the stop was skipped.

    That shipped, and it meant a judge opening the app cold saw two empty tabs, including
    the one carrying the strongest evidence for the 35% criterion. Use `return`.

    ONE CALL, WHATEVER THE CREW COUNT. The crew the answer is ABOUT — the one the ranking
    puts first — goes through `agent.answer()`, so the figures in the headline are what
    the chosen layer actually returned and the decision lands in `data/decisions.jsonl`.
    Every other selected crew is read from the committed roll-ups, because ranking twelve
    crews must not cost twenty-four calls. `tests/test_app_surface.py` pins the roll-ups
    against the live path so the two cannot drift.
    """
    if not facts:
        st.info("**Select at least one crew above.** A crew is a site: the roster carries "
                "its headcount and shift window.", icon="👷")
        return

    ordered = ask.rank(facts, preview.question_type)
    lead = ordered[0]

    # Refusals go through `answer()` too. It makes no call when the router refuses, and
    # the refusal has to reach `data/decisions.jsonl` — a log that records only answers
    # cannot show what was declined, which is the half that matters in an audit.
    with st.spinner("Routing, then fetching…"):
        try:
            out = answer(question, site_id=lead.site_id, date=date,
                         threshold_f=threshold_f, narrate=False)
        except tools.CacheMiss as exc:
            st.error(f"**Not in the cached set.** {exc}", icon="📦")
            return
        except tools.ToolsError as exc:
            st.error(f"**API error.** {exc}")
            return

    choice, result = out["choice"], out["result"]

    # `answer()` catches tools.ToolsError internally and returns it as out["error"]
    # rather than re-raising, so the `except tools.CacheMiss` above never fires for a
    # missing fixture. Without this branch the empty result fell straight through to
    # `result["peak"]` and the script died with a bare KeyError, taking every tab with
    # it. A missing fixture is a boring, expected condition; it must render as one.
    if out.get("error"):
        st.error(f"**No data behind this question.** {out['error']}", icon="📦")
        _render_mechanism(choice, result)
        return

    # ------------------------------------------------------------- refusal path
    # Rendered generically, from the LayerChoice alone. `forecast` and `intraday` refuse
    # for reasons router.py measured, and nothing here special-cases either of them: a
    # refusal panel with a branch per reason is a panel that will be wrong about the next
    # reason somebody adds.
    if choice.refused:
        read_as = (f"Read as *{choice.question_type.value}*" if choice.question_type
                   else "Not recognised as any of the six question types")
        # Same shape as an answer — headline, one line, mechanism — because a refusal IS
        # the answer here, not an error state. It gets the same prominence a number would.
        st.markdown(f"### Refused — {choice.refusal.value.replace('_', ' ')}")
        st.error(f"{read_as}. No call was made, so no credit was spent.", icon="🚫")
        st.caption(
            "Answerable here: what a site reached (snapshot), how long it stayed above "
            "the threshold (duration), and which crew is worst (comparison). The "
            "measurement behind this refusal is in the mechanism below."
        )
        _render_mechanism(choice, result)
        return

    # ---------------------------------------------------------------- the answer
    # The SHAPE comes from the routed layer, not from a fixed template. A snapshot is one
    # number, a duration is two, and a comparison is a ranking — see src/heatguard/ask.py,
    # which is pure so the three shapes can be tested without a browser.
    lead = ask.with_measured(lead, result)
    shaped = ask.build(choice.question_type, [lead] + list(ordered[1:]),
                       threshold_f=threshold_f)

    st.markdown(f"### {shaped.headline}")

    chips = []
    if shaped.band_id:
        chips.append(theme.band_chip(
            shaped.band_id, f"NWS {shaped.band_id.replace('_', ' ')}"))
    if shaped.action_id:
        chips.append(theme.band_chip(
            shaped.action_id, f"OSHA {shaped.action_id.replace('_', ' ')} risk"))
    # Colour is the fastest channel for severity and it is spent here, next to the call
    # it qualifies. Chips rather than a metric tile because `st.metric` cannot render
    # HTML, and because a severity stacked with two numbers reads as a third number.
    if shaped.call_text:
        st.markdown(
            f"**Call — {shaped.call_text}**&nbsp;&nbsp;&nbsp;"
            + "&nbsp;&nbsp;".join(chips),
            unsafe_allow_html=True)

    if shaped.metrics:
        cols = st.columns(len(shaped.metrics))
        for col, metric in zip(cols, shaped.metrics):
            col.metric(metric.label, metric.value, help=metric.help)

    if shaped.rows:
        st.dataframe(list(shaped.rows), use_container_width=True, hide_index=True)

    st.caption(" ".join(part for part in (shaped.lead, shaped.note) if part))

    # ------------------------------------------------------------ the mechanism
    _render_mechanism(choice, result, ranked_over=len(ordered))


#: The question text an example chip has asked for. NOT a widget key — that distinction
#: is the entire fix for a measured bug, see the slot comment in the Ask tab below.
ASK_TEXT_STATE = "ask_q_text"


# ========================================================================== decision
#
# THE WORKING SURFACE. Input band across the top, answer beneath it, mechanism collapsed
# under the answer — and nothing else at first glance.
#
# What this tab used to be: a six-row preset selectbox that made free text look like a
# menu, a single-site picker that could not answer the comparison question it offered, and
# a three-paragraph "What this shows" panel occupying the entire answer column until
# somebody pressed a button. The panel explained the product to a reader who had not used
# it yet, which is a landing page, not a tool.
#
# Three decisions drive the rebuild:
#
#   1. FREE TEXT IN, ROUTING AS AUDIT OUT. The preset menu is gone. The user types the
#      question; the router classifies it and the classification is rendered as auditable
#      output beside the answer, not as a control the user operates.
#   2. THE ANSWER FOLLOWS THE QUESTION. Shape and headline come from the routed layer, and
#      where that disagrees with the morning call sheet for the same crew, one line says
#      why. That disagreement is the entire thesis; hiding it would be hiding the product.
#   3. A CREW IS A SITE. `crew_size`, `shift_start`, `shift_end` and `night_shift` are
#      columns on config/sites.csv, so the control picks CREWS, and picks more than one —
#      being allowed only one site while being offered a comparison question was not sound.

with decision_tab:
    roster = sites()
    available = cached_dates() or [DEMO_DATE]

    # ------------------------------------------------------------------- input
    # One band, three controls, no prose between them. Who, when, and against what — the
    # three things that scope every answer below, and nothing that is not one of them.
    crew_col, date_col, threshold_col = st.columns([5, 2, 3])

    _default_crews = [c for c in ask.DEFAULT_CREW_IDS if c in roster] or list(roster)[:3]
    crew_ids = crew_col.multiselect(
        "Crews",
        options=list(roster),
        default=_default_crews,
        format_func=lambda s: ask.crew_option(roster[s]),
        help="A crew is a site. Headcount and shift window are how a supervisor names "
             "one. Pick two or more and the answer becomes a ranking.",
    )
    date = date_col.selectbox(
        "Date", options=available,
        index=available.index(DEMO_DATE) if DEMO_DATE in available else 0)
    threshold_label = threshold_col.radio(
        "Threshold", list(THRESHOLD_CHOICES), index=DEFAULT_THRESHOLD_INDEX,
        horizontal=True)
    threshold_f = THRESHOLD_CHOICES[threshold_label]

    # The box is seeded once so a cold visit answers something real on the first press,
    # and the chips below are examples rather than a mode selector — the router reads the
    # words, so editing one of them can change the layer, which is the point.
    # ---------------------------------------------------------------------------
    # THE BOX RENDERS ABOVE THE CHIPS BUT IS CREATED AFTER THEM.
    # ---------------------------------------------------------------------------
    # MEASURED, 29 Aug 2026, on the deployed app: clicking an example chip reset the
    # whole page back to the FIRST tab. The chips used `on_click=` to write
    # `st.session_state["ask_question"]` — which was the text box's own widget `key`.
    # Mutating a widget's key from a callback remounts that widget, and the remount takes
    # `st.tabs` with it, whose selected tab is client-side state. Pressing `Ask HeatGuard`
    # — a plain button with no callback — did NOT reset it, which is what isolated the
    # cause.
    #
    # The callback existed for a real reason: Streamlit refuses to write a widget's key
    # after that widget has been instantiated in the same run, and the chips belong BELOW
    # the box where a reader expects suggestions. `st.empty()` dissolves that constraint —
    # it reserves the box's POSITION now and lets it be BUILT later, so the chips run
    # first in code while still rendering second on screen. No callback, and the state
    # they write is not a widget key.
    st.session_state.setdefault(ASK_TEXT_STATE, ask.DEFAULT_QUESTION)
    _q_slot = st.empty()

    _chip_cols = st.columns(len(ask.EXAMPLES))
    for _col, (_label, _text) in zip(_chip_cols, ask.EXAMPLES):
        if _col.button(_label, key=f"eg_{_label}", use_container_width=True):
            st.session_state[ASK_TEXT_STATE] = _text

    # Deliberately keyless. The widget's identity includes `value`, so a chip press
    # rebuilds it with the new text, while typing survives any rerun that leaves `value`
    # alone — which is exactly the behaviour both paths need.
    question = _q_slot.text_input(
        "Question", value=st.session_state[ASK_TEXT_STATE],
        placeholder=ask.QUESTION_PLACEHOLDER)

    # Live routing preview — the whole IP, visible before anything is fetched and costing
    # nothing. Kept from the old tab because it is the best thing in it; compressed to one
    # line because it is a status readout, not an essay.
    _anchor = roster[crew_ids[0]] if crew_ids else next(iter(roster.values()))
    _preview = route(question, lat=float(_anchor["lat"]), lon=float(_anchor["lon"]),
                     date=date)
    if _preview.refused and _preview.question_type is None:
        # The unrecognised refusal has no question_type BY CONSTRUCTION — that is the
        # whole point of it, and dereferencing .value here would crash the script and
        # blank every tab. Same class of bug as the two already fixed today.
        st.warning("**Not recognised as any of the six question types** → no layer, no "
                   "call. Snapshot is not the fall-through: guessing narrow is how a "
                   "one-hour reading gets passed off as a duration answer.", icon="🚫")
    elif _preview.refused:
        st.warning(f"Reads as **{_preview.question_type.value}** → **refused** "
                   f"(`{_preview.refusal.value}`). No call would be made.", icon="🚫")
    else:
        _esc = (f" · escalated from *{_preview.escalated_from.value}*"
                if _preview.escalated_from else "")
        st.info(f"Reads as **{_preview.question_type.value}** → "
                f"`filter_type={_preview.filter_type}`, "
                f"`analytic_type={_preview.analytic_type.value}`{_esc}", icon="🧭")

    go = st.button("Ask HeatGuard", type="primary")

    st.divider()

    # ------------------------------------------------------------------ output
    #
    # The scope line. Not prose — it is the four facts that decide what the answer below
    # is ABOUT, restated where the answer is, so a screenshot of the result carries its
    # own scope and nobody has to scroll back to the controls to know what they are
    # looking at. Every figure in it is measured from config/sites.csv and the committed
    # fixtures, so none of them carries a citation.
    _headcount = sum(int(roster[c]["crew_size"]) for c in crew_ids)
    st.markdown(
        f"**{len(crew_ids)} crew{'' if len(crew_ids) == 1 else 's'} · {_headcount} "
        f"workers · {date} · threshold {threshold_f:.0f} °F heat index**")

    if go:
        _render_answer(
            ask.crew_facts(crew_ids, roster=roster, analysis=day_analysis(date),
                           shift_data=shift_exposure(date), threshold_f=threshold_f),
            date, question, threshold_f, _preview)
    else:
        # The empty state tells the reader what to do, not what to admire. The three
        # paragraphs that used to live here explained the routing argument to somebody
        # who had not yet asked anything; that argument belongs on "How it decides", and
        # the routing readout above already demonstrates it for free.
        st.info("**Press Ask HeatGuard to run the layer named above.** One crew answers "
                "as a card, two or more as a ranking, worst first. Routing has already "
                "happened — the button only fetches what that layer needs.", icon="⬆️")


# ============================================================================== trap

with trap_tab:
    st.subheader("Two calls. One unit. Seventeen hours of difference.")
    st.markdown(
        "Both calls below are **the same endpoint, the same area, the same date, the "
        "same `filter_type`, the same `analytic_type`, the same `direction`.** The only "
        "difference is whether the threshold was converted from Fahrenheit to Celsius "
        "before it was sent."
    )

    st.markdown(charts.unit_trap(), unsafe_allow_html=True)
    st.caption(
        "Encanto Park, 2025-07-15. Persistence says 16 of those 17 hours were "
        "*continuous* — which is the number that matters, because heat stroke follows "
        "uninterrupted exposure rather than a day's scattered total."
    )

    st.error(
        "**17 hours of dangerous exposure, reported as zero — as a confidently "
        "formatted all-clear.** For a heat-safety tool that is the worst available "
        "wrong answer, and it sits one unit conversion away at all times.",
        icon="🚨",
    )
    st.markdown(
        "HeatGuard refuses it before it reaches the wire. Every threshold crossing the "
        "API boundary is unit-suffixed (`threshold_c`), converted in exactly one "
        "function, and guarded — a threshold above 60 °C raises, because nowhere on "
        "Earth is that hot and it is therefore almost certainly Fahrenheit that skipped "
        "the conversion."
    )
    st.caption(
        "**Measured here, not cited.** The 17 hours and the 0 hours are two live calls "
        "this project made against the FortyGuard API, reproducible from "
        "`data/fixtures/t4/t4_probes.json` and pinned by `tests/test_api_contract.py`. "
        "They carry no source link because there is no external document to point at — "
        "nobody else has published this."
    )

    st.divider()
    st.markdown("#### Four more failures that look like answers")
    st.table({
        "What you ask for": [
            "An area outside the US",
            "A date before ~Q4 2021",
            "Tomorrow's date",
            "`exceedance` with no threshold",
        ],
        "What comes back": [
            "`Completed`, zero tiles",
            "`Completed`, zero tiles",
            "`Completed`, one flat value for the whole day",
            "`Completed`, 24.0 hours",
        ],
        "Charged?": ["4,220 credits", "4,220 credits", "4,220 credits", "4,220 credits"],
        "Why it is dangerous": [
            "Reads as 'no unsafe exposure'",
            "Documented start date is out by a year",
            "Exceedance against a constant is exactly 0 h or 24 h",
            "Silently defaults to 30 °C — a threshold nobody chose",
        ],
    })


# ============================================================================ method

with method_tab:
    st.subheader("The decision table")
    st.markdown(
        "`filter_type` selects the **time window**. `analytic_type` selects the "
        "**analysis layer** — and that is the one that silently changes the answer."
    )
    st.table({
        "Question": ["Is it safe right now?", "When do we start and stop?",
                     "Will we cross soon?", "How long above the band?",
                     "Chronically dangerous?", "Which site is worst?"],
        "filter_type": ["1 · hour", "3 · day", "2 · hour range", "3 · day",
                        "4 · day range", "3 · day"],
        "analytic_type": ["tcm", "time_of_measure", "tcm", "**exceedance**",
                          "**exceedance**", "**exceedance**"],
        "Wrong answer if answered as a snapshot": [
            "None — a snapshot is correct here",
            "One number, no schedule",
            "A historical average hides today",
            "A maximum says how hot, never how long",
            "One bad day looks structural",
            "Ranks by the clock, not by heat",
        ],
    })

    st.divider()
    st.markdown("#### The LLM does not choose the layer")
    st.markdown(
        "`router.py` is deterministic — no model call anywhere in it. That makes layer "
        "selection **auditable** (this is a safety tool), **reproducible** (every demo "
        "take matches), and **testable at zero cost** (over 400 offline tests, no network, "
        "no credits).\n\n"
        "The language model narrates and nothing else. With no API key the templated "
        "narration is used and the answer is byte-identical apart from wording — there "
        "is a test that runs the same question both ways and asserts every decisive "
        "field matches. *A safety tool whose recommendation depends on whether a "
        "language model was reachable is not a safety tool.*"
    )

    st.divider()
    st.markdown("#### Refusals are a feature")
    for reason in RefusalReason:
        st.markdown(f"- `{reason.value}`")
    st.caption(
        "The last one is the differentiator: refusing a well-formed question the API "
        "would happily answer, because the only layer that fits the requested scope "
        "would produce a confident wrong answer."
    )

    st.divider()
    st.markdown("#### Built to be relied on")
    st.markdown(
        "**It works on a cold visit.** This deployment is **offline by default** and "
        "serves a committed fixture cache. It needs no API key, so there is nothing to "
        "leak and nothing that breaks when the FortyGuard key expires — and **clicking "
        "around cannot spend a credit**. Every path you can click here was verified "
        "offline: 12 sites × 6 question shapes × 2 thresholds = **144 paths — 72 "
        "answered, 72 refused by design, zero errors, zero cache misses**. Half of them "
        "refuse because three of the six question shapes cannot be answered honestly "
        "from this API, and saying so is the product.\n\n"
        "**The build is sound.** Over 400 tests, all offline — no network, no credits, no "
        "key. Layer selection is deterministic, and its post-conditions *crash* rather "
        "than emit a layer already known to be wrong."
    )

    st.markdown("**The data is handled well.** Documented ways to misuse this API and "
                "get a confident wrong answer — each handled in code, not just noted:")
    st.table({
        "Trap": [
            "Analysis layers use a different schema",
            "`exceedance` counts hours, not degree-hours",
            "`env_params` heat index is a humidity artifact",
            "`env_params` is coarser than a parcel",
            "`threshold` is °C while readings are °F",
        ],
        "What we do about it": [
            "Two separate readers; the hours reader raises unless units are 'hour'",
            "Labelled hours everywhere; never an intensity or a severity",
            "No duration metric derived from it — duration comes from exceedance; "
            "env_params supplies humidity only",
            "Never used to discriminate between sites",
            "One conversion point, unit-suffixed, guarded above 60 °C",
        ],
    })
    st.caption(
        "The third one is the subtle one: that series holds temperature fixed and varies "
        "only humidity, so it peaks overnight. It is a humidity-sensitivity curve, not a "
        "diurnal forecast — we verified that by reproducing it from the single input "
        "temperature. Deriving duration from it would be a correctness failure."
    )

    st.divider()
    st.markdown("#### What is not proven yet")
    st.markdown(
        "Naming these is not modesty — a judge finds them in the first minute, and "
        "being the one who says them first is worth more than hoping nobody looks.\n\n"
        "- **No customer discovery.** Zero interviews. The crew sizes, shifts and site "
        "roster are *plausible constructions*, not observed operations from a real "
        "contractor. The mechanism is measured; the demand is not. Next step is five "
        "conversations with Phoenix safety supervisors before another line of code.\n"
        "- **Heat index, not WBGT** — the metric OSHA actually regulates against. "
        "`/v1/env_params` returns `wet_bulb_temperature_celsius`, so a WBGT estimate is "
        "reachable and it is the top of the roadmap, not a footnote.\n"
        "- **The per-site premise partly failed.** Predictions scored 2 of 11, worse "
        "than chance. The value turned out to be scoping to shifts and weighting by "
        "headcount — not site microclimate. Reported rather than quietly dropped."
    )

    # ------------------------------------------------------- the audit trail, visible
    #
    # CLAUDE.md calls `data/decisions.jsonl` "the compliance audit trail and the evidence
    # the system works". It was neither, from a judge's seat: the file is gitignored, and
    # the copy the deployed container writes lives in ephemeral storage nobody can reach.
    # The app claimed "Logged to data/decisions.jsonl" and gave no way to check.
    #
    # So it is rendered here. Every question asked in THIS session appears below as it is
    # asked, including refusals, and the whole file downloads as JSONL. A safety tool that
    # asks to be audited has to hand over the log.
    st.divider()
    st.markdown("#### The audit trail")
    st.markdown(
        "Every routing decision is appended to `data/decisions.jsonl` — the question, the "
        "layer chosen, the rationale, the refusal if there was one, and whether the prose "
        "came from the model or the template. **Refusals are logged too**, which is the "
        "half that matters: a log that only records answers cannot show what was declined."
    )

    _rows = recent_decisions(25)
    if _rows:
        st.caption(
            f"{len(_rows)} most recent — this container's log, including anything you "
            f"just asked. Restarting the app clears it; the committed sample below does "
            f"not move."
        )
        st.dataframe(
            [
                {
                    "at": r.get("at", "")[:19].replace("T", " "),
                    "site": r.get("site_name"),
                    "question": (r.get("question") or "")[:52],
                    "read as": r.get("question_type"),
                    "filter": r.get("filter_type"),
                    "layer": r.get("analytic_type"),
                    "refused": r.get("refusal") or "",
                    "peak °F": r.get("peak_f"),
                    "hours": r.get("hours_above"),
                    "prose": r.get("narration_source"),
                }
                for r in _rows
            ],
            use_container_width=True, hide_index=True,
        )
    else:
        st.caption("No decisions recorded yet — ask something on the second tab.")

    _log = decisions_bytes()
    if _log:
        st.download_button(
            "Download the decision log (JSONL)", data=_log,
            file_name="heatguard-decisions.jsonl", mime="application/x-ndjson",
            help="One JSON object per decision. This is the artefact a safety audit "
                 "would ask for.",
        )

    t = load_thresholds()
    st.divider()
    st.caption(t.disclaimer)


# ============================================================================= sources
#
# ONLY what this pass of the page actually rendered — never the whole registry. Thirty
# claims listed under a page that cited seven is a bibliography, not a citation: a reader
# cannot tell which of them any figure on screen rests on, which is the failure the
# registry existed to fix. `SOURCES` fills as the page renders, so this block is exactly
# the external claims above it, in the order they appeared.
#
# The ABSENCE of a figure here is itself the signal. Anything on this page with no entry
# below was measured by this project from its committed fixtures — the peak spread, the
# worker-hours, the 92%, the 17-hour unit trap, the 4,220 credits, the site and crew
# counts. None of them borrows a citation, and none of the claims below is presented as
# something we measured.
st.divider()
with st.expander(
    f"📚 Sources — the {len(SOURCES)} external claims rendered on this page"
):
    st.markdown(SOURCES.markdown())
    st.caption(
        "Every figure above that is **not** listed here was measured by this project from "
        "its own committed fixtures. `data/evidence/claims.json` is the registry and "
        "`tests/test_evidence.py` fails the build if a claim loses its source URL or its "
        "data year, if data older than three years is not flagged stale, if a "
        "general-population figure travels without its caveat, or if this page cites an id "
        "the registry does not hold. A citation that cannot be checked is not a citation."
    )
