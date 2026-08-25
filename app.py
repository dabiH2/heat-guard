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

import os
import sys
from datetime import date as _date
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from heatguard import tools                                    # noqa: E402
from heatguard.agent import answer, load_sites                 # noqa: E402
from heatguard.bands import action_for, band_for, load_thresholds  # noqa: E402
from heatguard.router import AnalyticType, RefusalReason       # noqa: E402

st.set_page_config(page_title="HeatGuard", page_icon="🌡️", layout="wide")

# The demo day and the sites whose data is committed to the cache. Anything outside this
# set cannot be answered offline, so the UI does not offer it.
DEMO_DATE = "2025-07-15"
THRESHOLD_CHOICES = {
    "91 °F — OSHA moderate risk (work/rest cycles begin)": 91.0,
    "103 °F — OSHA high risk (50:10 cycles, buddy system)": 103.0,
}


@st.cache_data
def sites():
    return load_sites()


@st.cache_data
def cached_dates() -> list[str]:
    """Dates the fixture cache can actually answer, newest first."""
    seen = {p["date"] for p in tools.cached_combinations() if p.get("date")}
    return sorted(seen, reverse=True)


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

st.markdown(
    "> **A safety manager with twelve Phoenix sites decides each morning where crews can "
    "work.** Today that decision comes from a single city-wide forecast high. "
    "OSHA records outdoor-worker heat-stroke deaths at a daily maximum heat index of "
    "only **86 °F** — inside the *Caution* band. **Peak temperature is a poor predictor "
    "of harm. Duration above a threshold is the signal.**"
)

decision_tab, trap_tab, roster_tab, method_tab = st.tabs(
    ["Decision", "⚠️ The trap", "The twelve sites", "How it decides"]
)


# ========================================================================== decision

with decision_tab:
    left, right = st.columns([1, 2])

    with left:
        st.subheader("Ask")
        roster = sites()
        site_id = st.selectbox(
            "Site",
            options=list(roster),
            format_func=lambda s: f"{roster[s]['name']}  ·  {roster[s]['archetype']}",
        )
        site = roster[site_id]

        shift = f"{site['shift_start']}–{site['shift_end']}"
        night = site["night_shift"] == "True"
        st.caption(
            f"**{site['crew_size']} crew** · shift {shift}"
            f"{' 🌙 **night**' if night else ''} · predicted `{site['expected_profile']}`"
        )

        available = cached_dates() or [DEMO_DATE]
        date = st.selectbox("Date", options=available,
                            index=available.index(DEMO_DATE)
                            if DEMO_DATE in available else 0)

        question = st.text_input(
            "Question",
            value="How many hours were they above the danger threshold?",
            help="The wording decides the analysis layer. Try 'is it safe right now?' "
                 "against 'how long were they above the band?' — same site, same day, "
                 "different layer, different answer.",
        )

        threshold_label = st.radio("Threshold", list(THRESHOLD_CHOICES),
                                   help="Reported at both, because the number changes "
                                        "materially between them.")
        threshold_f = THRESHOLD_CHOICES[threshold_label]

        go = st.button("Ask HeatGuard", type="primary", use_container_width=True)

    with right:
        if not go:
            st.subheader("What this shows")
            st.markdown(
                "The router classifies the question against a decision table **before "
                "any API call is made**, picks the analysis layer, states why, and "
                "refuses when the data cannot answer it.\n\n"
                "`tcm` and `exceedance` are the *same endpoint*, the *same* "
                "`filter_type`, the *same* area — **one optional string apart**. Ask a "
                "duration question, let the default stand, and you get a "
                "well-formatted map of peak temperature with no error and no hint the "
                "question went unanswered."
            )
            st.stop()

        with st.spinner("Routing, then fetching…"):
            try:
                out = answer(question, site_id=site_id, date=date,
                             threshold_f=threshold_f, narrate=False)
            except tools.CacheMiss as exc:
                st.error(f"**Not in the cached set.** {exc}", icon="📦")
                st.stop()
            except tools.ToolsError as exc:
                st.error(f"**API error.** {exc}")
                st.stop()

        choice, result = out["choice"], out["result"]

        # ---------------------------------------------------------- refusal path
        if choice.refused:
            st.error(f"**Refused — {choice.refusal.value.replace('_', ' ')}**", icon="🚫")
            st.markdown(choice.refusal_message)
            st.success(
                "**No API call was made, so no credit was spent.** Three FortyGuard "
                "failure modes return `Completed` with a plausible-looking empty result "
                "*and charge for it* — a non-US area, a date outside real coverage, and "
                "tomorrow's date. Refusing here is a cost control as much as a "
                "correctness one.",
                icon="✅",
            )
            st.stop()

        if result.get("empty"):
            st.warning(
                "**The API returned no tiles for this area and date.** That is a "
                "coverage gap, not a safe reading — it is deliberately *not* reported "
                "as an all-clear.", icon="⚠️")
            st.stop()

        # ------------------------------------------------------------ the answer
        peak = result["peak"]
        band = band_for(peak["max_f"])
        action = action_for(peak["max_f"])

        st.subheader(f"{site['name']} · {date}")

        cols = st.columns(3)
        cols[0].metric("Peak heat index", f"{peak['max_f']:.0f} °F",
                       help="The number a forecast would report.")
        if result.get("hours") is not None:
            cols[1].metric(f"Hours above {threshold_f:.0f} °F",
                           f"{result['hours']:.1f} h",
                           help="What the duration layer measures. This is the one that "
                                "changes the decision.")
        cols[2].metric("NWS band", band.id.replace("_", " ").title())

        st.markdown(f"### Action — {action.action.replace('_', ' ')}")
        st.markdown(action.label)

        # ----------------------------------------------- the routing decision itself
        st.divider()
        st.markdown("#### The layer, and why")
        st.info(choice.rationale, icon="🧭")

        detail = st.columns(4)
        detail[0].markdown(f"**Endpoint**\n\n`{choice.endpoint}`")
        detail[1].markdown(f"**filter_type**\n\n`{choice.filter_type}`")
        detail[2].markdown(
            f"**analytic_type**\n\n`{choice.analytic_type.value if choice.analytic_type else '—'}`")
        detail[3].markdown(f"**granularity**\n\n`{choice.granularity} m`")

        if choice.escalated_from is not None:
            st.warning(
                f"The wording carried a duration marker, so this was read as a duration "
                f"question rather than a *{choice.escalated_from.value}* one. The marker "
                f"list overrides the classifier deliberately — being wrong toward more "
                f"data costs a credit, being wrong toward less costs a wrong call.",
                icon="↗️")

        with st.expander("What a snapshot would have said instead"):
            st.markdown(choice.wrong_answer_if_snapshot)

        if result.get("threshold_c_air") is not None:
            with st.expander("The unit conversion behind that threshold"):
                st.markdown(
                    f"OSHA bands are **heat index**. `exceedance` thresholds **air "
                    f"temperature**. At this site's measured "
                    f"**{result['humidity_pct']:.0f}%** humidity:\n\n"
                    f"- OSHA threshold: **{result['threshold_f_heat_index']:.0f} °F heat index**\n"
                    f"- Equivalent air temperature: **{result['threshold_f_air']:.0f} °F**"
                    f" = **{result['threshold_c_air']:.2f} °C** ← what is sent\n\n"
                    f"In dry Phoenix air the equivalent runs *above* the OSHA number; "
                    f"under monsoon humidity it runs *below*. Same threshold, different "
                    f"air temperature, depending on the day."
                )

        st.caption(f"Logged to `data/decisions.jsonl` · "
                   f"calls made: {', '.join(result.get('calls', [])) or 'none'}")


# ============================================================================== trap

with trap_tab:
    st.subheader("Two calls. One unit. Seventeen hours of difference.")
    st.markdown(
        "Both calls below are **the same endpoint, the same area, the same date, the "
        "same `filter_type`, the same `analytic_type`, the same `direction`.** The only "
        "difference is whether the threshold was converted from Fahrenheit to Celsius "
        "before it was sent."
    )

    a, b = st.columns(2)
    with a:
        st.success("**Converted correctly**", icon="✅")
        st.code('threshold = 35.00   # 95 °F → °C', language="python")
        st.metric("Hours above threshold", "17.0 h")
        st.caption("Encanto Park, 2025-07-15. Persistence says 16 of those 17 hours "
                   "were *continuous*.")
    with b:
        st.error("**Sent as Fahrenheit**", icon="🔥")
        st.code('threshold = 95      # read as 95 °C = 203 °F', language="python")
        st.metric("Hours above threshold", "0.0 h", delta="-17.0 h")
        st.caption("Status `Completed`. Credit spent. Nothing raised anywhere.")

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
    st.caption("Reproducible from `data/fixtures/t4/t4_probes.json`; pinned by "
               "`tests/test_api_contract.py`.")

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


# ============================================================================ roster

with roster_tab:
    st.subheader("Twelve sites, chosen for thermal diversity during shift hours")
    st.markdown(
        "Each site carries a **falsifiable prediction** written before any data was "
        "fetched. Sites whose prediction fails are kept and reported — a roster where "
        "all twelve came true would be evidence of tuning, not of a working instrument."
    )
    roster = sites()
    st.dataframe(
        [
            {
                "Site": s["name"],
                "Archetype": s["archetype"],
                "Predicted": s["expected_profile"],
                "Crew": int(s["crew_size"]),
                "Shift": f"{s['shift_start']}–{s['shift_end']}",
                "Night": "🌙" if s["night_shift"] == "True" else "",
            }
            for s in roster.values()
        ],
        use_container_width=True, hide_index=True,
    )
    st.markdown(
        "**Why night crews.** Phoenix's urban heat island is *nocturnal*. A downtown "
        "site's extra hours above the band land in the evening — so if every crew "
        "clocked out at 15:30, those hours would be real physics and a fake decision. "
        "Phoenix genuinely paves roads and does downtown utility work at night in "
        "summer. **A night crew downtown is the strongest case here: the city-wide "
        "forecast *high* is a daytime number and says nothing about a 21:00–05:30 "
        "shift.**"
    )


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
        "take matches), and **testable at zero cost** (336 offline tests, no network, "
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

    t = load_thresholds()
    st.divider()
    st.caption(t.disclaimer)
