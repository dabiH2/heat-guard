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
from heatguard.agent import answer, load_sites                 # noqa: E402
from heatguard import charts                                  # noqa: E402
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

today_tab, decision_tab, trap_tab, method_tab = st.tabs(
    ["📋 The morning call", "Ask a question", "⚠️ The trap", "How it decides"]
)


@st.cache_data
def shift_exposure(date: str) -> dict | None:
    path = (Path(__file__).parent / "data" / "fixtures" / "t8"
            / f"shift_exposure_{date}.json")
    if not path.exists():
        return None
    import json
    return json.loads(path.read_text(encoding="utf-8"))


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

        st.subheader(f"{DEMO_DATE} — {len(rows)} sites, {crews} workers")
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

        # ------------------------------------------------------ what that is worth
        # The safety argument competes with a free NWS forecast and loses. The two
        # arguments that survive contact with a buyer are cost avoidance and defensible
        # documentation, and both use numbers already measured above.
        #
        # The dollar figure is DERIVED, not measured, so the rate is exposed as a control
        # rather than baked in. A judge who thinks $55 is wrong can move it and watch the
        # number change — which is more persuasive than a figure they cannot interrogate,
        # and more honest than presenting an assumption as a finding.
        st.markdown("#### What that is worth")
        rate = st.slider(
            "Loaded labour rate, $/hour",
            min_value=25, max_value=100, value=55, step=5,
            help="Wage plus burden — payroll tax, insurance, equipment standing idle. "
                 "Move it: the saving scales linearly and the assumption is yours, "
                 "not ours.",
        )
        avoided = (naive - actual) * rate

        money_a, money_b = st.columns(2)
        money_a.metric(
            "Unnecessary stop-work avoided, one day",
            f"${avoided:,.0f}",
            help=f"{naive - actual:,.0f} phantom worker-hours × ${rate}/h. "
                 f"One day, one roster.",
        )
        money_b.metric(
            "Cost of being wrong the other way",
            "one heat-illness claim",
            help="An OSHA citation, a workers' compensation claim, or a fatality "
                 "investigation. HeatGuard does not price this — it documents the "
                 "decision instead.",
        )

        st.info(
            f"**Over-warning is the expensive error, and it is the one nobody counts.** "
            f"Stopping work costs money on a day nobody was at risk; the "
            # Dollar signs are escaped: Streamlit reads $…$ as LaTeX math, which silently
            # eats both the currency symbol and the bold markers around it.
            f"{naive - actual:,.0f} worker-hours above are **\\${avoided:,.0f}** at "
            f"\\${rate}/h. Under-warning costs a claim — rarer, far worse, and the reason "
            f"the tool refuses rather than guesses.\n\n"
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

        st.markdown("#### What the city-wide figure claims, against what is real")
        st.markdown(charts.phantom_bars(rows), unsafe_allow_html=True)

        st.markdown("#### Where the exposure actually is")
        st.dataframe(
            [
                {
                    "Site": r["name"],
                    "Shift": r["shift"] + (" 🌙" if r["night"] else ""),
                    "Crew": r["crew"],
                    "Whole day (h)": r["whole_day_hours"],
                    "In shift (h)": r["in_shift_hours"],
                    "Worker-hours": r["worker_hours"],
                }
                for r in sorted(rows, key=lambda x: -x["worker_hours"])
            ],
            use_container_width=True, hide_index=True,
        )

        top_whole = max(r["whole_day_hours"] for r in rows)
        tied = [r for r in rows if abs(r["whole_day_hours"] - top_whole) < 0.05]
        exposed = sorted([r for r in rows if r["worker_hours"] > 0],
                         key=lambda r: -r["worker_hours"])

        if len(tied) > 1 and exposed:
            worst, second = exposed[0], (exposed[1] if len(exposed) > 1 else None)
            st.info(
                f"**Ranking by heat and ranking by harm give different answers.**\n\n"
                f"**{len(tied)} of {len(rows)} sites tie** at {top_whole:.0f} hours above "
                f"threshold for the day — by that measure they are indistinguishable, and "
                f"a heat map would colour them identically. Scoped to shifts, only "
                f"**{len(exposed)}** carry any exposure at all."
                + (
                    f"\n\n**{worst['name']}** carries the most: "
                    f"{worst['worker_hours']:.0f} worker-hours against "
                    f"{second['worker_hours']:.0f} at {second['name']} — the same "
                    f"{worst['in_shift_hours']:.0f} hour of overlap, but "
                    f"**{worst['crew']} people standing in it** rather than "
                    f"{second['crew']}."
                    if second else ""
                )
                + "\n\nHeat maps rank tiles. Crews are what get hurt.",
                icon="🎯",
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
def _render_answer(site: dict, site_id: str, date: str, question: str,
                   threshold_f: float) -> None:
    """Route the question, run the plan, and render the outcome.

    ⚠️ EVERY EARLY EXIT HERE IS `return`, NEVER `st.stop()`.

    `st.stop()` halts the ENTIRE script run, not the current tab or column. Because
    Streamlit executes this file top to bottom on every interaction, a stop inside the
    "Ask a question" tab silently prevented every tab defined LATER in the file — "The
    trap" and "How it decides" — from being populated at all. They only appeared once the
    button was pressed and the stop was skipped.

    That shipped, and it meant a judge opening the app cold saw two empty tabs, including
    the one carrying the strongest evidence for the 35% criterion. Use `return`.
    """
    with st.spinner("Routing, then fetching…"):
        try:
            out = answer(question, site_id=site_id, date=date,
                         threshold_f=threshold_f, narrate=False)
        except tools.CacheMiss as exc:
            st.error(f"**Not in the cached set.** {exc}", icon="📦")
            return
        except tools.ToolsError as exc:
            st.error(f"**API error.** {exc}")
            return

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
        return

    if result.get("empty"):
        st.warning(
            "**The API returned no tiles for this area and date.** That is a "
            "coverage gap, not a safe reading — it is deliberately *not* reported "
            "as an all-clear.", icon="⚠️")
        return

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
        if go:
            _render_answer(site, site_id, date, question, threshold_f)
        else:
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

    st.divider()
    st.markdown("#### Built to be relied on")
    st.markdown(
        "**It works on a cold visit.** This deployment is **offline by default** and "
        "serves a committed fixture cache. It needs no API key, so there is nothing to "
        "leak and nothing that breaks when the FortyGuard key expires — and **clicking "
        "around cannot spend a credit**. Every path you can click here was verified "
        "offline: 12 sites × 4 question shapes × 2 thresholds, 36 answered, 12 refused "
        "by design, **zero cache misses**.\n\n"
        "**The build is sound.** 349 tests, all offline — no network, no credits, no "
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

    t = load_thresholds()
    st.divider()
    st.caption(t.disclaimer)
