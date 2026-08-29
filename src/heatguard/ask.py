"""
ask.py — the SHAPE of one answer in the "Ask a question" tab.

WHY THIS IS NOT INSIDE app.py
-----------------------------
The Ask tab has to do something no other tab does: change shape with the question. A
snapshot answer is one number, a duration answer is two, and a comparison is a ranking —
and the entire thesis of this project is that those are three different answers to three
different questions and must not look alike.

That was the bug. Every question rendered the same panel: peak on the left, an optional
hours tile beside it, the same heading, the same chips. A judge could ask a snapshot
question and a duration question and see the same screen twice, which is precisely the
failure the router exists to prevent, reproduced one layer up in the interface.

Deciding an answer's shape inside a Streamlit callback means it can only be checked by
driving a browser. Everything here is pure — dicts in, dataclasses out, no Streamlit
import, no network, no clock — so `tests/test_app_surface.py` can assert that the three
shapes actually differ without rendering a pixel.

NOTHING HERE PICKS A LAYER. `router.py` does that, deterministically, before any call is
made. This module is handed the layer the router already chose and decides only how the
answer reads.

THE NUMBERS COME FROM THE COMMITTED ROLL-UPS.
`data/fixtures/t8/analysis_<date>.json` (whole-day peak and hours per site) and
`data/fixtures/t8/shift_exposure_<date>.json` (hours inside each crew's own shift) were
built from the same live calls the agent makes, so a ranking across twelve crews costs
zero calls instead of twenty-four. `tests/test_app_surface.py` pins the two against
`agent.answer()` for every site and both thresholds, so the roll-up and the live path
cannot silently drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .bands import action_for, band_for, load_thresholds
from .router import QuestionType

#: The three shapes the committed fixtures can honestly answer. `persistence`,
#: `forecast` and `intraday` are refused by router.py, and nothing in this module
#: invents a shape for a question the data cannot answer.
ANSWERABLE = (QuestionType.SNAPSHOT, QuestionType.DURATION, QuestionType.COMPARISON)

#: Starting points, NOT a mode selector. The router reads the words, so editing one of
#: these can change the layer — which is the point, and the live preview shows it before
#: anything is fetched.
#:
#: The fourth is deliberately a question that REFUSES. Refusal is the behaviour this
#: project is proudest of and the one a cold visitor is least likely to discover by
#: accident; making them guess a phrasing that triggers it hides the best thing here.
EXAMPLES: tuple[tuple[str, str], ...] = (
    ("Right now", "How hot is it at this crew's site right now?"),
    ("Hours above", "How many hours were they above the threshold today?"),
    ("Worst crew", "Which of these crews is worst today?"),
    ("Start and stop · refuses", "When should we start and stop today?"),
)

#: Seeded into the box so a cold visit answers something real on the first press. It is
#: a comparison because the crew control defaults to more than one crew, and an interface
#: whose default question does not fit its default selection teaches the wrong thing.
DEFAULT_QUESTION = EXAMPLES[2][1]

QUESTION_PLACEHOLDER = "Ask in your own words — e.g. which crew is worst today?"

#: A small default, not the whole roster. Twelve pre-selected crews is a wall, and one is
#: not a comparison. These three separate under every offered threshold — two tie on
#: whole-day hours and are split by hours inside the shift, the third separates outright —
#: so the ranking demonstrates something on the first press rather than printing a
#: three-way tie. Filtered against the live roster by the caller.
DEFAULT_CREW_IDS = ("PHX-27TH", "PHX-CHASE", "PHX-UNHL")

#: OSHA's rungs in the words a foreman uses, plus the two non-calls. Deliberately a
#: separate copy from app.py's morning-call table: the two tabs answer different
#: questions and must be free to diverge. `tests/test_app_surface.py` asserts they agree
#: crew-for-crew on the demo day, which proves the claim instead of assuming it.
CALL_TEXT = {
    "rest_breaks_50_10": "50:10 work/rest",
    "rest_breaks_55_5": "55:5 work/rest",
    "no_reading": "NO READING",
    "no_call": "no call from this layer",
}


# --------------------------------------------------------------------- crew identity

def crew_option(site: dict) -> str:
    """One line of crew identity: who they are, how many, and when they are outside.

    A CREW IS A SITE in this data model — `crew_size`, `shift_start`, `shift_end` and
    `night_shift` are columns on `config/sites.csv`. A supervisor picks a crew, not a
    geography, so the option has to read as one. "PHX-CHASE · downtown_canyon" is a row
    in a database; "Chase Tower block · 6 crew · 21:00–05:30 🌙" is a crew.
    """
    return (
        f"{site['name']} · {site['crew_size']} crew · "
        f"{site['shift_start']}–{site['shift_end']}"
        + (" 🌙" if _is_night(site) else "")
    )


def _is_night(site: dict) -> bool:
    return str(site.get("night_shift", "")).strip().lower() == "true"


def rung_band_id(call_id: str) -> str | None:
    """The colour band that belongs to an OSHA rung, read out of the same table the
    rung came from.

    Colour is the fastest channel for severity and this app spends it in exactly one
    vocabulary, defined once by the legend above the tabs. A duration answer has no heat
    index to band — it is measured in hours — so its chip colours the CALL rather than a
    temperature, which is the point: the rung is what the supervisor acts on.

    Derived rather than mapped in a literal, so a rung added to `config/thresholds.yaml`
    cannot end up grey here while the rest of the app knows its colour.

    NONE FOR THE NON-CALLS, and that matters more than it looks. `no_reading` and
    `no_call` are not rungs; falling back to the lowest band would have printed "OSHA
    below caution risk" beside a crew the API returned zero tiles for. That is silence
    rendered as safety — the precise failure the morning sheet refuses to make — so it
    returns nothing and the caller shows no chip at all.
    """
    for band in load_thresholds().osha_actions:
        if band.action == call_id:
            return band.id
    return None


# ------------------------------------------------------------------- the measured facts

def shift_floor_hours(shift_hours: float, hours_above: float,
                      night: bool) -> float | None:
    """A FLOOR on hours above the threshold inside the shift, by pigeonhole.

    If a site was above the threshold for H of 24 hours, a shift of length L must overlap
    at least L - (24 - H) of them whatever order the hours came in. Arithmetic on a
    measured total, so it is honest — but it is a lower bound, and every rendering of it
    says "at least".

    None for night shifts. The bound needs the whole-day total for the SAME 24 hours the
    shift spans, and a shift crossing midnight spans two dates; the cache holds 16 July
    only as the post-midnight tail of these very shifts. A number here would mean
    stretching a 15 July measurement across a day nobody measured.
    """
    if night:
        return None
    return max(0.0, shift_hours - (24.0 - hours_above))


def shift_rule_call(*, has_data: bool, in_shift_hours: float | None,
                    in_shift_floor: float | None) -> tuple[str, str]:
    """The call the SHIFT rule supports — the same rule the morning call sheet applies.

    Keyed on hours above the threshold inside the crew's own window, never on the day's
    peak: ten of the twelve sites peak within 1.9 °F of one another, so a peak-driven
    ladder returns the same rung for almost every crew.

    Where the chosen threshold is not the one the shift roll-up measured, only the
    pigeonhole floor is available. A floor ABOVE zero still supports the tighter rung —
    the crew provably had exposure inside the shift. A floor OF zero supports nothing: it
    neither finds exposure nor rules it out, and this returns `no_call` rather than
    reporting the absence of a bound as an all-clear.
    """
    if not has_data:
        return "no_reading", CALL_TEXT["no_reading"]
    if in_shift_hours is not None:
        rung = "rest_breaks_50_10" if in_shift_hours > 0 else "rest_breaks_55_5"
        return rung, CALL_TEXT[rung]
    if in_shift_floor is not None and in_shift_floor > 0:
        return "rest_breaks_50_10", CALL_TEXT["rest_breaks_50_10"]
    return "no_call", CALL_TEXT["no_call"]


@dataclass(frozen=True)
class CrewFact:
    """Everything known about one crew on one date at one threshold.

    Assembled from the two committed roll-ups and `config/sites.csv`. No call is made to
    build one, which is what lets a twelve-crew ranking cost nothing.
    """
    site_id: str
    name: str
    crew_size: int
    shift: str
    night: bool
    has_data: bool
    peak_f: float | None
    day_hours: float | None
    #: Measured inside the shift. Only available at the threshold the shift roll-up was
    #: built at; None otherwise, and then `in_shift_floor` is what there is.
    in_shift_hours: float | None
    in_shift_floor: float | None
    rostered_hours: float
    #: What to print for the in-shift figure, already qualified: a measurement, an
    #: "at least" bound, or the reason there is neither.
    in_shift_text: str
    call_id: str
    call_text: str

    @property
    def crew_label(self) -> str:
        return f"{self.name}{' 🌙' if self.night else ''}"


def crew_facts(crew_ids, *, roster: dict, analysis: dict | None,
               shift_data: dict | None, threshold_f: float) -> list[CrewFact]:
    """Build one CrewFact per selected crew, in the order given.

    `analysis` carries whole-day peak and hours-above per site; `shift_data` carries the
    hours inside each crew's own window. Either can be missing — only 2025-07-15 has
    roll-ups — and a missing roll-up degrades to "no reading" rather than raising, because
    a coverage gap is a boring expected condition and must render as one.
    """
    arows = {r["site_id"]: r for r in (analysis or {}).get("rows", [])}
    srows = {r["site_id"]: r for r in (shift_data or {}).get("rows", [])}
    sheet_threshold = (shift_data or {}).get("threshold_f_heat_index")
    hours_key = f"hours_{threshold_f:.0f}"

    facts: list[CrewFact] = []
    for site_id in crew_ids:
        site = roster.get(site_id, {})
        arow = arows.get(site_id)
        srow = srows.get(site_id, {})
        night = _is_night(site) if site else bool(srow.get("night"))
        has_data = arow is not None and not arow.get("empty")

        # The ROSTERED length, not the measured one. The crew is outside for the whole
        # shift whether or not the API looked at all of it, so the floor is a statement
        # about the crew's exposure and not about our coverage.
        rostered = float(site.get("shift_hours") or 0.0)

        peak_f = arow.get("peak_f") if has_data else None
        day_hours = arow.get(hours_key) if has_data else None

        in_shift: float | None = None
        if (has_data and sheet_threshold is not None
                and abs(float(sheet_threshold) - threshold_f) < 0.01):
            in_shift = srow.get("in_shift_hours")

        floor = None
        if has_data and in_shift is None and day_hours is not None and rostered:
            floor = shift_floor_hours(rostered, float(day_hours), night)

        if not has_data:
            text = "—"
        elif in_shift is not None:
            text = f"{in_shift:.1f} h"
        elif floor is not None:
            text = f"at least {floor:.1f} of {rostered:.1f} h"
        else:
            text = "not derivable — shift crosses midnight"

        call_id, call_text = shift_rule_call(
            has_data=has_data, in_shift_hours=in_shift, in_shift_floor=floor)

        facts.append(CrewFact(
            site_id=site_id,
            name=site.get("name") or srow.get("name") or site_id,
            crew_size=int(site.get("crew_size") or srow.get("crew") or 0),
            shift=(f"{site['shift_start']}–{site['shift_end']}" if site
                   else srow.get("shift", "")),
            night=night,
            has_data=has_data,
            peak_f=float(peak_f) if peak_f is not None else None,
            day_hours=float(day_hours) if day_hours is not None else None,
            in_shift_hours=float(in_shift) if in_shift is not None else None,
            in_shift_floor=floor,
            rostered_hours=rostered,
            in_shift_text=text,
            call_id=call_id,
            call_text=call_text,
        ))
    return facts


def with_measured(fact: CrewFact, result: dict) -> CrewFact:
    """Overlay what the live call actually returned onto the roll-up figures.

    Exactly one call is made per question — for the crew the answer is about — and this
    is where its numbers reach the screen, so the headline figure is the one the chosen
    layer returned rather than a pre-computed lookalike. `hours` is only overlaid when
    the layer produced one: a snapshot returns none, and writing None over a roll-up
    figure would blank a number that is perfectly good.
    """
    peak = (result or {}).get("peak") or {}
    hours = (result or {}).get("hours")
    return replace(
        fact,
        peak_f=float(peak["max_f"]) if peak.get("max_f") is not None else fact.peak_f,
        day_hours=float(hours) if hours is not None else fact.day_hours,
    )


# ----------------------------------------------------------------------- the ranking

def _rank_value(fact: CrewFact, question_type: QuestionType | None) -> float | None:
    """The number the ROUTED LAYER measures, and therefore the number that ranks.

    Ranking a snapshot question by duration would answer a question nobody asked, and
    ranking a duration question by peak is the exact inversion this project exists to
    show: FortyGuard's own case study found six parcels 0.7 °C apart by peak and 19 hours
    apart by exceedance.
    """
    if question_type is QuestionType.SNAPSHOT:
        return fact.peak_f
    return fact.day_hours


def rank(facts, question_type: QuestionType | None) -> list[CrewFact]:
    """Worst first. Crews with no reading sort last — never as a zero.

    A coverage gap rendered as 0.0 hours ranks a crew nobody measured as the safest on
    the roster, which is the worst available wrong answer for a heat-safety tool and the
    exact failure the morning sheet refuses to make.

    Ties are broken by hours inside the shift, then headcount, then name, so the order is
    deterministic and a demo take is reproducible.
    """
    def key(fact: CrewFact):
        value = _rank_value(fact, question_type)
        return (
            0 if value is not None else 1,
            -(value or 0.0),
            -(fact.in_shift_hours if fact.in_shift_hours is not None
              else fact.in_shift_floor or 0.0),
            -fact.crew_size,
            fact.name,
        )

    return sorted(facts, key=key)


# ------------------------------------------------------------------------ the answer

@dataclass(frozen=True)
class Metric:
    """One tile. Two per answer at most — a third dilutes whichever one decides."""
    label: str
    value: str
    help: str


@dataclass(frozen=True)
class Answer:
    """What to render, already shaped by the layer the router chose."""
    kind: str                       # "card" | "ranking" | "no_reading"
    headline: str                   # the big line, and it changes with the layer
    lead: str                       # one short line: what this layer measures
    call_text: str                  # the call, in the words a foreman uses
    call_id: str
    note: str                       # ONE line: where this differs from the morning sheet
    metrics: tuple[Metric, ...] = ()
    rows: tuple[dict, ...] = ()
    rank_column: str = ""
    #: The NWS band is only carried where the answer rests on a TEMPERATURE. A duration
    #: answer is measured in hours and has no band — inventing one would smuggle the peak
    #: back into an answer that deliberately does not use it. `action_id` always carries
    #: the colour of the call itself.
    band_id: str | None = None
    action_id: str | None = None


def _sheet_leader(facts) -> CrewFact | None:
    """The crew the MORNING SHEET would put first: tighter rung, then bigger crew."""
    order = {"rest_breaks_50_10": 0, "rest_breaks_55_5": 1, "no_call": 2, "no_reading": 3}
    ranked = sorted(facts, key=lambda f: (order.get(f.call_id, 9), -f.crew_size, f.name))
    return ranked[0] if ranked else None


def _snapshot_note(fact: CrewFact) -> str:
    """Decision 2, on screen: where the answer differs from the sheet, and why.

    This is the whole thesis in one line. The sheet counts hours inside the crew's own
    window; a snapshot reads the day's maximum. For Sky Harbor on the demo day those give
    DIFFERENT RUNGS for the same crew on the same date — 50:10 from the peak, 55:5 from
    the shift — and an interface that shows one without naming the other is hiding the
    only interesting thing it knows.
    """
    if not fact.has_data:
        return ""
    peak_call = action_for(fact.peak_f).action
    if peak_call == fact.call_id:
        return (f"Morning sheet agrees ({fact.call_text}) — reached the other way, from "
                f"hours inside the shift rather than from the peak.")
    return (f"Morning sheet says **{fact.call_text}** for this crew. Different question, "
            f"different layer: it counts hours inside the shift, a snapshot reads the "
            f"day's peak.")


def _duration_note(fact: CrewFact) -> str:
    if not fact.has_data:
        return ""
    if fact.in_shift_hours is not None:
        return ("Same layer the morning sheet is built on, so the call matches it — "
                "this is that sheet asked one crew at a time.")
    if fact.in_shift_floor is not None:
        return ("The shift roll-up was measured at a different threshold, so the in-shift "
                "figure here is a pigeonhole floor — a bound, not a measurement.")
    return ("This shift crosses midnight, so no in-shift figure is derivable at this "
            "threshold; the morning sheet answers it at the threshold it measured.")


def _ranking_note(ordered, question_type: QuestionType | None) -> str:
    leader = _sheet_leader(ordered)
    if question_type is QuestionType.SNAPSHOT:
        peaks = [f.peak_f for f in ordered if f.peak_f is not None]
        spread = (max(peaks) - min(peaks)) if len(peaks) > 1 else 0.0
        return (f"Ranked by peak, the layer this question asked for — and these crews are "
                f"**{spread:.1f} °F** apart by it. Ask how long instead and the order "
                f"changes.")
    if leader is not None and ordered and leader.site_id != ordered[0].site_id:
        return (f"Morning sheet leads with **{leader.name}** instead. Different question, "
                f"different layer: it ranks by hours inside each crew's own shift, this "
                f"ranks the whole day.")
    return ("Morning sheet leads with the same crew, reached the other way — by hours "
            "inside each crew's own shift rather than across the whole day.")


def build(question_type: QuestionType | None, facts, *,
          threshold_f: float) -> Answer:
    """The answer, shaped by the layer. One crew is a card; two or more is a ranking.

    A comparison is ALWAYS a ranking even with one crew selected, because the question
    asked for an ordering and printing a single card in reply to "which crew is worst"
    quietly answers a different question. The headline says there is nothing to compare
    it against instead.
    """
    ordered = rank(facts, question_type)
    if not ordered:
        return Answer(kind="no_reading", headline="No crews selected.",
                      lead="Pick at least one crew above.", call_text="", call_id="",
                      note="")

    wants_ranking = len(ordered) > 1 or question_type is QuestionType.COMPARISON
    if wants_ranking:
        return _ranking(ordered, question_type, threshold_f)
    return _card(ordered[0], question_type, threshold_f)


def _no_reading(fact: CrewFact) -> Answer:
    return Answer(
        kind="no_reading",
        headline=f"No reading for {fact.name}.",
        lead="The API returned zero tiles for this area on this date. Status: Completed. "
             "Cost: 4,220 credits.",
        call_text=CALL_TEXT["no_reading"],
        call_id="no_reading",
        note="A coverage gap is not a safe reading, and this crew stays on the standing "
             "plan.",
        action_id=rung_band_id("no_reading"),
    )


def _card(fact: CrewFact, question_type: QuestionType | None,
          threshold_f: float) -> Answer:
    if not fact.has_data:
        return _no_reading(fact)

    if question_type is QuestionType.SNAPSHOT:
        action = action_for(fact.peak_f)
        return Answer(
            kind="card",
            headline=f"{fact.peak_f:.0f} °F peak heat index · {fact.name}",
            lead="Snapshot layer: what it reached. It cannot say how long it stayed "
                 "there.",
            call_text=CALL_TEXT.get(action.action, action.action.replace("_", " ")),
            call_id=action.action,
            note=_snapshot_note(fact),
            metrics=(
                Metric("Peak heat index", f"{fact.peak_f:.0f} °F",
                       "The single number a forecast would report."),
            ),
            band_id=band_for(fact.peak_f).id,
            action_id=action.id,
        )

    hours = fact.day_hours if fact.day_hours is not None else 0.0
    return Answer(
        kind="card",
        headline=f"{hours:.1f} hours above {threshold_f:.0f} °F · {fact.name}",
        lead=f"Duration layer: how long, across the whole day and inside the "
             f"{fact.shift} shift.",
        call_text=fact.call_text,
        call_id=fact.call_id,
        note=_duration_note(fact),
        metrics=(
            Metric(f"Hours ≥ {threshold_f:.0f} °F · whole day", f"{hours:.1f} h",
                   "Counted server-side by the exceedance layer, per tile, per hour."),
            Metric(f"Inside the {fact.shift} shift", fact.in_shift_text,
                   "The hours this crew was actually outside. This is the one that "
                   "changes the call."),
        ),
        action_id=rung_band_id(fact.call_id),
    )


def _ranking(ordered, question_type: QuestionType | None,
             threshold_f: float) -> Answer:
    top = ordered[0]
    if question_type is QuestionType.SNAPSHOT:
        rank_column = "▸ Peak °F"
        second_column = "NWS band"
        lead = "Snapshot layer: ranked by what each site reached, not by how long."
        superlative = "hottest"
        value = f"{top.peak_f:.0f} °F peak" if top.peak_f is not None else "no reading"
    else:
        rank_column = f"▸ Hours ≥ {threshold_f:.0f} °F"
        second_column = "In shift"
        lead = (f"Duration layer: ranked by hours above {threshold_f:.0f} °F across the "
                f"whole day.")
        superlative = "worst"
        value = (f"{top.day_hours:.1f} h above {threshold_f:.0f} °F"
                 if top.day_hours is not None else "no reading")

    if len(ordered) == 1:
        headline = f"{top.name} · {value} · nothing to compare it against"
        note = "A ranking of one crew is not a comparison. Add crews above."
    else:
        headline = f"{top.name} is {superlative} of {len(ordered)} crews · {value}"
        note = _ranking_note(ordered, question_type)

    rows = []
    for position, fact in enumerate(ordered, start=1):
        if question_type is QuestionType.SNAPSHOT:
            primary = f"{fact.peak_f:.1f}" if fact.peak_f is not None else "no reading"
            secondary = (band_for(fact.peak_f).id.replace("_", " ")
                         if fact.peak_f is not None else "—")
        else:
            primary = (f"{fact.day_hours:.1f} h" if fact.day_hours is not None
                       else "no reading")
            secondary = fact.in_shift_text
        rows.append({
            "#": position,
            "Crew": fact.crew_label,
            rank_column: primary,
            second_column: secondary,
            "Size": fact.crew_size,
            "Shift": fact.shift,
            "Morning call": fact.call_text,
        })

    # NO SINGLE CALL LINE ON A RANKING, deliberately. A ranking answers about several
    # crews and each has its own rung; one call printed above the table would either be
    # the leader's — read as if it applied to everyone — or an average of rungs, which is
    # not a thing. The per-crew call is a COLUMN, next to the crew it belongs to.
    return Answer(
        kind="ranking",
        headline=headline,
        lead=lead,
        call_text="",
        call_id=top.call_id,
        note=note,
        rows=tuple(rows),
        rank_column=rank_column,
    )


# ------------------------------------------------------------------- the mechanism

def mechanism_rows(choice, result: dict | None, *, ranked_over: int = 0) -> list[tuple[str, str]]:
    """The audit trail for ONE answer, as a definition list.

    Adjacent to the answer and collapsed, not filed in a separate tab: a reader checking
    a number should not have to go looking for how it was produced. Every row is a fact
    about THIS answer — the layer, why that one, the exact parameters, what the wrong
    layer would have said, and the unit conversion that is the single most dangerous step
    in the pipeline.

    Rows appear only when they apply. A snapshot sends no threshold, so it gets no
    conversion row; a question that was not escalated gets no escalation row. A fixed
    grid with empty cells reads as a failed render and teaches a reader to skim.
    """
    result = result or {}
    rows: list[tuple[str, str]] = []

    read_as = choice.question_type.value if choice.question_type else "not recognised"
    rows.append(("Question read as", read_as))

    if choice.refused:
        rows.append(("Outcome", f"refused · {choice.refusal.value}"))
        rows.append(("Calls made", "none — refused before the wire, no credit spent"))
        rows.append(("Why", choice.refusal_message or ""))
        return rows

    rows.append(("Endpoint", choice.endpoint or "—"))
    rows.append(("filter_type", str(choice.filter_type)))
    rows.append((
        "analytic_type",
        choice.analytic_type.value if choice.analytic_type else "—"))
    rows.append(("granularity", f"{choice.granularity} m"))
    if choice.direction:
        rows.append(("direction", choice.direction))
    rows.append(("Why this layer", choice.rationale))
    if choice.escalated_from is not None:
        rows.append((
            "Escalated",
            f"read as duration rather than {choice.escalated_from.value} — the wording "
            f"carries a duration marker, and being wrong toward more data costs a "
            f"credit while being wrong toward less costs a wrong call"))
    rows.append(("What a snapshot would have said", choice.wrong_answer_if_snapshot))

    if result.get("threshold_c_air") is not None:
        rows.append((
            "Unit conversion",
            f"{result['threshold_f_heat_index']:.0f} °F heat index → "
            f"{result['threshold_f_air']:.0f} °F air → "
            f"{result['threshold_c_air']:.2f} °C sent, at this site's measured "
            f"{result['humidity_pct']:.0f}% humidity. OSHA bands are heat index; "
            f"exceedance thresholds air temperature. In dry Phoenix air the equivalent "
            f"runs above the OSHA number, under monsoon humidity below."))

    calls = ", ".join(result.get("calls", [])) or "none"
    rows.append(("Calls made", f"{calls} — one crew, from the committed cache"))
    if ranked_over > 1:
        rows.append((
            "Ranking source",
            f"{ranked_over} crews ranked from the committed roll-up for this date "
            f"(data/fixtures/t8), not from {ranked_over} calls"))
    rows.append(("Logged to", "data/decisions.jsonl — see the audit trail on the last tab"))
    return rows
