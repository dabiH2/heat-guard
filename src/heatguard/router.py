"""
router.py — THE CORE IP.

Maps an operator's question to the correct temperature analysis layer, states why, and
refuses when the data cannot answer it.

DESIGN RULE, NON-NEGOTIABLE: no LLM call belongs in this module. The agent parses intent
and narrates; the router decides. That makes layer selection auditable (this is a safety
tool), reproducible (every demo take must match), and testable with zero credits and no
network.

-------------------------------------------------------------------------------
WHAT THIS EXISTS TO PREVENT
-------------------------------------------------------------------------------
`filter_type` selects the TIME WINDOW — how much data. `analytic_type` selects the
ANALYSIS LAYER — what question you ask of that data. They are separate parameters, and
the second is the one that silently changes the answer.

`tcm` and `exceedance` are the same endpoint, the same filter_type, the same AOI — one
optional string apart. Ask "how long were they above the threshold", let `analytic_type`
default to `tcm`, and you get a well-formed map of peak temperature: same shape of
output, opposite operational decision, no error raised anywhere.

Fawad Shah demonstrates the inversion on FortyGuard's own client case study
(`02-temperature-api` [00:36:14]-[00:37:23]), six parcels over 28 Jul-3 Aug:
ranked by PEAK the hottest-to-coolest spread is 0.7 °C — operationally "all six sites are
the same". Ranked by DURATION: "for more than 19 hours it stayed above, and then for five
hours straight it was above the threshold."

OSHA records outdoor-worker heat-stroke deaths at a daily maximum heat index of only
86 °F, inside the NWS "Caution" band. Peak is a poor predictor of harm. Duration is the
signal.

-------------------------------------------------------------------------------
THE UNIT DISCIPLINE THIS MODULE ENFORCES
-------------------------------------------------------------------------------
The router NEVER emits a bare `threshold`. It emits `threshold_f` — a heat-index
threshold in Fahrenheit, because OSHA and NWS are Fahrenheit and the users are US
supervisors — plus `threshold_basis` recording what that number is measured against.

Resolving it to the Celsius AIR-TEMPERATURE threshold the API wants is `tools.py`'s job
and nowhere else's, because it needs live humidity. Two conversions are involved and both
are silent killers if skipped:

  1. °F -> °C. Passing 91 meaning °F makes the API read 91 °C = 195.8 °F. Exceedance
     returns 0 hours at every cell, status `succeeded`, credit spent, and the tool
     reports a confident all-clear across all twelve sites.
  2. heat index -> air temperature. `exceedance` thresholds the TEMPERATURE field. OSHA
     bands are HEAT INDEX. In dry Phoenix heat index runs BELOW air temperature, so the
     equivalent air temperature is higher than 91 °F; during monsoon humidity it runs
     above, so the equivalent is lower. Same OSHA threshold, different air temperature,
     depending on the day. See `LayerChoice.threshold_basis`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date as _date
from datetime import datetime, timedelta, timezone
from enum import Enum

from .bands import load_thresholds
from .tools import EARLIEST_DATE as _EARLIEST
from .tools import (
    DEFAULT_GRANULARITY,
    GRANULARITIES,
    MAX_AOI_KM2,
    MAX_DAYS_PER_CALL,
    MAX_FUTURE_DAYS_ACCEPTED,
    MAX_FUTURE_DAYS_USABLE,
)


class QuestionType(str, Enum):
    """The six operator questions."""
    SNAPSHOT = "snapshot"            # "Is it safe at site 3 right now?"
    INTRADAY = "intraday"            # "When should we start and stop today?"
    FORECAST = "forecast"            # "Will we cross the threshold in the next few hours?"
    DURATION = "duration"            # "How long were they above the danger band?"
    PERSISTENCE = "persistence"      # "Is site 3 chronically dangerous?"
    COMPARISON = "comparison"        # "Which of our 12 sites is worst?"


class AnalyticType(str, Enum):
    """`analytic_type` on POST /v1/heatmap.

    NAME COLLISION, READ THIS. `QuestionType.PERSISTENCE` and `AnalyticType.PERSISTENCE`
    are different things and are deliberately namespaced apart:

      QuestionType.PERSISTENCE   "is this site CHRONICALLY dangerous?" — across many DAYS
      AnalyticType.PERSISTENCE   longest continuous run of HOURS above threshold

    A chronic question is answered with a day RANGE, not with this analytic type. They
    compose, they are not synonyms.
    """
    TCM = "tcm"                          # snapshot temperature per tile
    TIME_OF_MEASURE = "time_of_measure"  # hour-of-day of each cell's peak
    EXCEEDANCE = "exceedance"            # hours each cell spends past threshold
    PERSISTENCE = "persistence"          # longest continuous run of those hours


class RefusalReason(str, Enum):
    """Grounded in verified API constraints — none of these are theatre."""
    OUTSIDE_US = "outside_us"                      # coverage is US-only
    # Name predates the measurement: coverage actually starts ~Q4 2021, and
    # EARLIEST_DATE is 2022-01-01. Kept as-is to avoid churning tests for no gain.
    BEFORE_2021 = "before_2021"
    # NOT "now + 12 h" — that was measured wrong in T4. The API accepts up to today + 1,
    # but tomorrow returns one flat value with no diurnal structure, so the usable
    # boundary is today. See tools.MAX_FUTURE_DAYS_ACCEPTED / _USABLE.
    BEYOND_FORECAST = "beyond_forecast_horizon"
    EXCEEDS_30_DAY_WINDOW = "exceeds_30_day_window"  # max 30 days returned per call
    AOI_TOO_LARGE = "aoi_too_large"                # 15 mi^2 on the hackathon plan
    GRANULARITY_TOO_FINE = "granularity_too_fine"  # only 60 / 80 / 100 m exist
    WRONG_LAYER_WOULD_MISLEAD = "wrong_layer_would_mislead"
    # ^ the differentiator: refusing a well-formed question because the only layer that
    #   fits the requested scope would produce a confident wrong answer.
    UNRECOGNISED_QUESTION = "unrecognised_question"
    # ^ MEASURED DEFECT, fixed 2026-08-29. SNAPSHOT used to be the dustbin: it had no
    #   markers of its own, so anything the marker table did not recognise fell through
    #   to filter_type=1 + tcm - the single-hour layer this entire project exists to warn
    #   against. Probed with fifteen paraphrases a supervisor would plausibly type;
    #   ELEVEN came back as a one-hour snapshot, including "should I send the crew out
    #   for the full day?" and "which of my sites should I worry about".
    #
    #   The old justification was cost: "falling back to a BROAD layer would spend
    #   credits on a guess." That let a cost argument beat a safety argument inside a
    #   safety tool, and it contradicted this codebase's own rule, asserted in
    #   test_escalation_direction_is_always_toward_more_data_never_less: being wrong
    #   toward more data costs a credit, being wrong toward less costs a wrong call.
    #
    #   Guessing broad and guessing narrow are both wrong. Not guessing is free.


class RouterInvariantError(AssertionError):
    """A structurally impossible layer choice was produced. This is a code bug.

    Raised rather than returned. A safety tool must fail loudly rather than emit a layer
    it has already determined cannot answer the question.
    """


# ---------------------------------------------------------------- verified constants

#: The API constants live in tools.py — the API boundary module — and are imported here.
#: A safety limit that exists in three files is a limit that will disagree with itself.
#: MEASURED, not documented: coverage starts in Q4 2021, not 2021-01-01. A date before it
#: returns Completed with zero cells and is billed full price. See tools.EARLIEST_DATE.
EARLIEST_DATE = _date(*(int(p) for p in _EARLIEST.split("-")))

# Coarse coverage boxes. A pre-flight check, not a border. The API is the authority — but
# a non-US AOI fails SILENTLY AND BILLS YOU (Fawad [00:13:39]: "it's just going to spend
# your credit"), so catching the obvious cases here is a cost control, not just hygiene.
_US_BOXES = (
    (24.4, 49.4, -125.0, -66.9),    # CONUS
    (51.2, 71.5, -168.0, -129.9),   # Alaska
    (18.9, 22.3, -160.3, -154.8),   # Hawaii
    (17.9, 18.6, -67.3, -65.2),     # Puerto Rico
)


# ---------------------------------------------------------------- classification

# Order matters and is the classifier. First family to match wins. Kept as literal data
# rather than a chain of ifs so the table can be read, diffed and tested directly.
_MARKERS: tuple[tuple[QuestionType, tuple[str, ...]], ...] = (
    (QuestionType.COMPARISON, (
        "which site", "which of our", "which of the", "which sites", "which is worst",
        "compare", "comparison", "rank", "ranking", "worst site", "hottest site",
        "across sites", "across our sites", "site is worst", "sites is worst",
        # Added after the paraphrase probe: these read as comparison to any human and
        # were falling through to a single-hour snapshot.
        "which of my", "my sites", "our sites", "other sites", "worry about",
        "worse than", "better than", "hotter than", "cooler than", "compared to",
        "versus",
    )),
    (QuestionType.PERSISTENCE, (
        "chronically", "chronic", "typically", "usually", "normally", "historically",
        "every summer", "this summer", "each summer", "over the past", "in general",
        "on average", "most days", "structural",
    )),
    (QuestionType.DURATION, (
        "how long", "how many hours", "hours above", "hours over", "time above",
        "sustained", "all day", "over the day", "throughout the day", "duration",
        "how much of the", "straight", "in a row", "continuous", "consecutive",
        # Added after the paraphrase probe. "Should I send the crew out for the full
        # day?" is a duration question in plain English and was answered with one hour.
        "full day", "whole day", "whole shift", "full shift", "entire shift",
        "through the afternoon", "all afternoon", "for the day",
    )),
    (QuestionType.FORECAST, (
        "will we", "will it", "will they", "going to", "next few hours", "later today",
        "rest of the shift", "rest of today", "expect", "forecast", "next hour",
        "coming hours", "next week", "tomorrow",
    )),
    (QuestionType.INTRADAY, (
        "when should", "what time", "start and stop", "start or stop", "schedule",
        "when can we", "when do we", "best time", "safe window", "shift window",
    )),
    # LAST deliberately. Snapshot is now a family you have to ASK for, not the place
    # unrecognised text lands. Ordering it last keeps "how long has it been this hot"
    # a duration question even though it also contains a snapshot marker.
    (QuestionType.SNAPSHOT, (
        "how hot", "how warm", "temperature", "right now", "at the moment",
        "currently", "current heat", "what is it now", "reading",
        "heat index", "degrees",
    )),
)

# TASKS.md T6: any of these makes a question a duration question, and it must NEVER be
# answered with a single-hour window. Enforced as a POST-CONDITION in `route`, not by the
# classifier — see `_assert_invariants`. Relying on the classifier alone would mean one
# missed synonym silently reintroduces the exact bug this project is about.
DURATION_MARKERS: tuple[str, ...] = (
    "how long", "chronically", "typically", "this summer", "worst",
    "sustained", "over the day", "all day", "hours above", "how many hours",
    "in a row", "straight", "consecutive", "continuous", "duration",
    "historically", "most days", "on average", "every summer",
)

#: Shown when nothing matches. It names the six families rather than saying "rephrase",
#: because a refusal that does not tell you what WOULD work is just a dead end.
UNRECOGNISED_MESSAGE = (
    "I could not tell which kind of question that is, so I did not pick a layer and did "
    "not call the API. Choosing wrongly here is not a small error: `tcm` and "
    "`exceedance` are the same endpoint one optional string apart, and the wrong one "
    "answers a duration question with a single hour - same shape of output, opposite "
    "operational decision, no error raised.\n\n"
    "Try one of the six: a **current reading**, **when** during the day, **how long** "
    "above a threshold, whether it is **chronic**, **which site** is worst, or what "
    "happens **later today**."
)


_GRANULARITY_RE = re.compile(r"(\d+)\s*(?:m\b|metre|meter)", re.IGNORECASE)


def classify(question: str) -> QuestionType | None:
    """Pure string classification. Deterministic, no network, no model.

    Returns **None** when no family matches, and None means *refuse* - not "snapshot".

    This used to fall through to SNAPSHOT, described as "the narrowest, cheapest layer".
    That was wrong, and measurably so: SNAPSHOT had no markers of its own, so it was the
    dustbin for every phrasing the table did not recognise, and SNAPSHOT is exactly the
    single-hour layer this project was built to warn people off. Eleven of fifteen
    realistic supervisor paraphrases came back as a one-hour `tcm` reading.

    A safety tool that cannot tell what it was asked must say so. Refusing is free, and
    it is the same behaviour the tool already has for a non-US area or an uncovered date.
    """
    text = question.lower()
    for question_type, markers in _MARKERS:
        if any(marker in text for marker in markers):
            return question_type
    return None


def has_duration_marker(question: str) -> bool:
    text = question.lower()
    return any(marker in text for marker in DURATION_MARKERS)


def _escalate_for_duration(question: str, question_type: QuestionType) -> QuestionType:
    """Apply the duration-marker rule as a classification OVERRIDE, not just a check.

    TASKS.md T6 states it absolutely: any question containing 'how long', 'chronically',
    'typically', 'this summer' or 'worst' is a duration question and must never be
    answered with a single hour. So the marker list is authoritative over the classifier,
    and where they disagree the marker wins.

    This exists because the classifier WILL have gaps — 'Tell me about the worst at this
    site' carries the marker 'worst' but matches none of the comparison phrasings, and
    fell through to SNAPSHOT. Crashing on that would be wrong: it is a legitimate
    question and a classifier miss, not a code bug. Escalating to the broader, more
    expensive, correct layer is the safe direction to be wrong in.

    Only fires when the selected row would actually answer with a single hour or with
    aggregate temperature. COMPARISON and PERSISTENCE already use exceedance, so a
    duration marker changes nothing there and they are left alone.
    """
    if not has_duration_marker(question):
        return question_type
    plan = DECISION_TABLE[question_type]
    if plan.filter_type == 1 or plan.analytic_type is AnalyticType.TCM:
        return QuestionType.DURATION
    return question_type


# ---------------------------------------------------------------- the decision table

@dataclass(frozen=True)
class Plan:
    """One row of the decision table."""
    endpoint: str
    filter_type: int
    analytic_type: AnalyticType | None
    granularity: int | None
    direction: str | None
    needs_threshold: bool
    rationale: str
    wrong_answer_if_snapshot: str


#: THE DECISION TABLE. This is the artefact the whole project is built to defend.
DECISION_TABLE: dict[QuestionType, Plan] = {

    QuestionType.SNAPSHOT: Plan(
        endpoint="/v1/heatmap",
        filter_type=1,
        analytic_type=AnalyticType.TCM,
        granularity=DEFAULT_GRANULARITY,
        direction=None,
        needs_threshold=False,
        rationale=(
            "Single-hour snapshot (filter_type=1, analytic_type=tcm). This is one of the "
            "few questions a single hour genuinely answers: you asked what it is like "
            "now, not how long it has been like this."
        ),
        wrong_answer_if_snapshot=(
            "None — a snapshot is the correct layer here. It is the only row in this "
            "table where that is true."
        ),
    ),

    QuestionType.INTRADAY: Plan(
        endpoint="/v1/heatmap",
        filter_type=3,
        analytic_type=AnalyticType.TIME_OF_MEASURE,
        granularity=DEFAULT_GRANULARITY,
        direction=None,
        needs_threshold=False,
        rationale=(
            "Whole day, keyed on when each tile peaks (filter_type=3, "
            "analytic_type=time_of_measure). Deciding when to start and stop needs the "
            "SHAPE of the day, not its height — the hour the site peaks is what moves "
            "the shift, not the number it peaks at."
        ),
        wrong_answer_if_snapshot=(
            "A single hour gives one number and no schedule. It cannot tell you which "
            "hour to avoid, which is the entire question."
        ),
    ),

    QuestionType.FORECAST: Plan(
        endpoint="/v1/heatmap",
        filter_type=2,
        analytic_type=AnalyticType.TCM,
        granularity=DEFAULT_GRANULARITY,
        direction=None,
        needs_threshold=False,
        rationale=(
            "Forward hour range inside the +12 h horizon (filter_type=2, "
            "analytic_type=tcm). The heatmap is the only layer that forecasts at all, "
            "and only 12 hours out."
        ),
        wrong_answer_if_snapshot=(
            "A historical average hides what today is doing. A single past hour cannot "
            "answer a question about the hours ahead."
        ),
    ),

    QuestionType.DURATION: Plan(
        endpoint="/v1/heatmap",
        filter_type=3,
        analytic_type=AnalyticType.EXCEEDANCE,
        granularity=DEFAULT_GRANULARITY,
        direction="above",
        needs_threshold=True,
        rationale=(
            "Hours above threshold across the whole day (filter_type=3, "
            "analytic_type=exceedance). The API counts the hours per tile server-side; "
            "this is a measurement, not an estimate derived from a peak."
        ),
        wrong_answer_if_snapshot=(
            "A maximum tells you how hot it got. It can never tell you how long it "
            "stayed there — and OSHA records deaths at a daily maximum of only 86 °F."
        ),
    ),

    QuestionType.PERSISTENCE: Plan(
        endpoint="/v1/heatmap",
        filter_type=4,
        analytic_type=AnalyticType.EXCEEDANCE,
        granularity=DEFAULT_GRANULARITY,
        direction="above",
        needs_threshold=True,
        rationale=(
            "Hours above threshold across a range of days (filter_type=4, "
            "analytic_type=exceedance). 'Chronically' is a claim about many days, so it "
            "needs many days; a single day cannot distinguish a structural problem from "
            "one bad afternoon."
        ),
        wrong_answer_if_snapshot=(
            "One bad day looks structural, and one good day looks safe. Either way you "
            "are describing the weather and calling it the site."
        ),
    ),

    QuestionType.COMPARISON: Plan(
        endpoint="/v1/heatmap",
        filter_type=3,
        analytic_type=AnalyticType.EXCEEDANCE,
        granularity=DEFAULT_GRANULARITY,
        direction="above",
        needs_threshold=True,
        rationale=(
            "Hours above threshold, same day and same granularity at every site "
            "(filter_type=3, analytic_type=exceedance). Ranking by duration rather than "
            "by peak is the whole point: FortyGuard's own case study found a 0.7 °C "
            "spread by peak across six parcels — indistinguishable — against 19 hours of "
            "exceedance and a 5-hour continuous run by duration."
        ),
        wrong_answer_if_snapshot=(
            "Ranking twelve sites by whichever hour you happened to sample ranks them by "
            "the clock, not by heat. Vary granularity between sites and you are not even "
            "comparing the same thing."
        ),
    ),
}


@dataclass
class LayerChoice:
    """What the router decided, and the sentence it says out loud."""
    question_type: QuestionType | None
    endpoint: str | None
    filter_type: int | None
    analytic_type: AnalyticType | None
    granularity: int | None
    rationale: str
    wrong_answer_if_snapshot: str = ""
    refusal: RefusalReason | None = None
    refusal_message: str | None = None

    #: Set when the duration-marker rule overrode the classifier. Recorded rather than
    #: hidden — an audit trail that silently rewrote its own question is not an audit
    #: trail. Appears in the rationale and in data/decisions.jsonl.
    escalated_from: QuestionType | None = None

    # Unit-suffixed on purpose. The router emits a HEAT-INDEX threshold in FAHRENHEIT;
    # tools.py resolves it to a Celsius AIR-TEMPERATURE threshold using live humidity.
    # A bare `threshold` must not exist anywhere in this codebase.
    threshold_f: float | None = None
    threshold_basis: str | None = None
    direction: str | None = None

    params: dict = field(default_factory=dict)

    @property
    def refused(self) -> bool:
        return self.refusal is not None


# ---------------------------------------------------------------------- refusals

def _in_us(lat: float, lon: float) -> bool:
    return any(
        lo_lat <= lat <= hi_lat and lo_lon <= lon <= hi_lon
        for lo_lat, hi_lat, lo_lon, hi_lon in _US_BOXES
    )


def _parse_date(value: str) -> _date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def check_refusals(
    *,
    lat: float,
    lon: float,
    date: str,
    end_date: str | None = None,
    granularity: int | None = None,
    aoi_km2: float | None = None,
    question: str = "",
    question_type: QuestionType | None = None,
    now: datetime | None = None,
) -> tuple[RefusalReason, str] | None:
    """Validate against the verified constraints BEFORE spending a credit.

    Priority is fixed and documented so the same input always produces the same refusal.
    Coverage first (no data at all), then time, then request shape, then — last — the
    question/layer mismatch, which is only meaningful once the request is otherwise valid.
    """
    now = now or datetime.now(timezone.utc)
    today = now.date()

    # 1. Coverage. First because a non-US AOI fails silently AND bills you.
    if not _in_us(lat, lon):
        return (
            RefusalReason.OUTSIDE_US,
            f"({lat:.4f}, {lon:.4f}) is outside FortyGuard's coverage, which is US-only. "
            f"I am not sending this: a non-US area of interest does not raise an error, "
            f"it returns an empty-looking result and still spends the credit.",
        )

    try:
        start = _parse_date(date)
    except ValueError:
        return (
            RefusalReason.BEFORE_2021,
            f"{date!r} is not a date I can read. Use YYYY-MM-DD.",
        )

    # 2. Time.
    if start < EARLIEST_DATE:
        return (
            RefusalReason.BEFORE_2021,
            f"{date} is before {EARLIEST_DATE.isoformat()}, where FortyGuard's coverage "
            f"actually begins. The documentation says 2021-01-01, but 2021-07-15 and "
            f"2021-10-15 both came back Completed with zero tiles — and were billed "
            f"4,220 credits each. An empty result is not a safe reading, so this is "
            f"refused rather than sent.",
        )

    # The forecast boundary is NOT where the API stops accepting requests. It is where
    # the API stops returning a diurnal profile — one day earlier. See tools.py.
    usable_through = today + timedelta(days=MAX_FUTURE_DAYS_USABLE)
    if start > usable_through:
        accepted_through = today + timedelta(days=MAX_FUTURE_DAYS_ACCEPTED)
        if start <= accepted_through:
            return (
                RefusalReason.BEYOND_FORECAST,
                f"{date} is tomorrow, and the API will happily accept it and charge you "
                f"for it — but it returns a single flat value for the whole day. "
                f"Measured: today came back 33.7-41.9 °C across the day, tomorrow came "
                f"back 34.34 °C for every hour, minimum equal to maximum. There is no "
                f"diurnal shape in it, so hours-above-threshold against it is exactly 0 "
                f"or exactly 24 and never anything in between. Today "
                f"({today.isoformat()}) or earlier is answerable.",
            )
        return (
            RefusalReason.BEYOND_FORECAST,
            f"{date} is in the future. FortyGuard rejects any start_date beyond "
            f"{accepted_through.isoformat()} outright, and only through "
            f"{usable_through.isoformat()} does it return a real diurnal profile. "
            f"Anything further would be a historical average dressed up as a forecast.",
        )

    if end_date is not None:
        try:
            finish = _parse_date(end_date)
        except ValueError:
            return (
                RefusalReason.BEFORE_2021,
                f"{end_date!r} is not a date I can read. Use YYYY-MM-DD.",
            )
        span_days = (finish - start).days + 1
        if span_days > MAX_DAYS_PER_CALL:
            return (
                RefusalReason.EXCEEDS_30_DAY_WINDOW,
                f"{date} to {end_date} is {span_days} days. The API returns at most "
                f"{MAX_DAYS_PER_CALL} days per call, so this would come back quietly "
                f"truncated. Split it into {-(-span_days // MAX_DAYS_PER_CALL)} calls.",
            )

    # 3. Request shape.
    if aoi_km2 is not None and aoi_km2 > MAX_AOI_KM2:
        return (
            RefusalReason.AOI_TOO_LARGE,
            f"That area of interest is {aoi_km2:.1f} km², over the {MAX_AOI_KM2} km² "
            f"(15 mi²) cap on this plan. Split it or coarsen the granularity.",
        )

    requested = granularity
    if requested is None and question:
        match = _GRANULARITY_RE.search(question)
        if match:
            requested = int(match.group(1))
    if requested is not None and requested not in GRANULARITIES:
        finest = min(GRANULARITIES)
        detail = (
            f"finer than the {finest} m floor" if requested < finest
            else "not one of the resolutions the API offers"
        )
        return (
            RefusalReason.GRANULARITY_TOO_FINE,
            f"{requested} m is {detail}. FortyGuard resolves to "
            f"{'/'.join(str(g) for g in GRANULARITIES)} m — the data is measured 2 m "
            f"above ground at 20 m spatial resolution, so there is no street-level "
            f"detail to return.",
        )

    # 4. Question/layer mismatch. Last: only meaningful if the request is otherwise sound.
    if question_type is QuestionType.PERSISTENCE and end_date is None:
        return (
            RefusalReason.WRONG_LAYER_WOULD_MISLEAD,
            "You asked whether this site is chronically dangerous, but gave me a single "
            "day. I can answer it, and the answer would be worthless: one bad day looks "
            "structural and one good day looks safe. Give me an end date — two weeks of "
            "the same month is enough.",
        )

    if question_type is QuestionType.DURATION and granularity is None and _single_hour(question):
        return (
            RefusalReason.WRONG_LAYER_WOULD_MISLEAD,
            "You asked how long the site was above the threshold, but scoped it to a "
            "single hour. Duration cannot be measured in an instant. Ask about the day, "
            "or ask what the temperature was at that hour.",
        )

    return None


_SINGLE_HOUR_RE = re.compile(
    r"\bat\s+(?:\d{1,2}\s*(?:am|pm)|\d{1,2}:\d{2})\b|\bat\s+that\s+hour\b", re.IGNORECASE
)


def _single_hour(question: str) -> bool:
    return bool(_SINGLE_HOUR_RE.search(question))


# ------------------------------------------------------------------------- route

def _assert_invariants(question: str, choice: LayerChoice) -> None:
    """Post-conditions that must hold for every non-refused choice.

    These are checked independently of the classifier on purpose. If layer selection
    depended solely on `classify` matching a marker, one missing synonym would silently
    reintroduce the exact failure this project exists to prevent. Here it crashes instead.
    """
    if choice.refused:
        return

    if has_duration_marker(question) and choice.filter_type == 1:
        raise RouterInvariantError(
            f"{question!r} contains a duration marker but resolved to filter_type=1. "
            f"A single hour cannot answer how long — this would be a confident wrong "
            f"answer, which is the one thing this module exists to prevent."
        )

    if has_duration_marker(question) and choice.analytic_type is AnalyticType.TCM:
        raise RouterInvariantError(
            f"{question!r} contains a duration marker but resolved to "
            f"analytic_type=tcm. tcm returns aggregate temperature per tile, never a "
            f"count of hours. The question would go unanswered with no error raised."
        )

    if choice.analytic_type in (AnalyticType.EXCEEDANCE, AnalyticType.PERSISTENCE):
        if choice.threshold_f is None or choice.direction is None:
            raise RouterInvariantError(
                f"analytic_type={choice.analytic_type.value} requires both a threshold "
                f"and a direction; the API rejects the call without them."
            )
        if choice.threshold_basis is None:
            raise RouterInvariantError(
                "a threshold was emitted without a basis. tools.py cannot know whether "
                "to treat it as heat index or as air temperature, and guessing wrong "
                "returns zero exceedance hours everywhere."
            )


def route(
    question: str,
    *,
    lat: float,
    lon: float,
    date: str,
    end_date: str | None = None,
    granularity: int | None = None,
    aoi_km2: float | None = None,
    threshold_f: float | None = None,
    now: datetime | None = None,
) -> LayerChoice:
    """The entry point. classify -> check refusals -> select layer + params -> explain.

    Deterministic: same input, same LayerChoice, every time. `now` is injectable so the
    forecast-horizon check can be tested without the clock making tests flaky, and so a
    demo take can be reproduced exactly.
    """
    classified = classify(question)
    unrecognised = classified is None

    # A duration marker is authoritative on its own and never needed the classifier to
    # agree. So a marker rescues an otherwise unreadable question, and it is recorded as
    # an escalation from SNAPSHOT rather than silently becoming a duration question --
    # "the classifier had nothing, the marker carried it" is exactly what the audit trail
    # should say.
    if unrecognised and has_duration_marker(question):
        classified, unrecognised = QuestionType.SNAPSHOT, False

    question_type = None if unrecognised else _escalate_for_duration(question, classified)
    escalated_from = (
        classified if (not unrecognised and question_type is not classified) else None
    )

    refusal = check_refusals(
        lat=lat, lon=lon, date=date, end_date=end_date, granularity=granularity,
        aoi_km2=aoi_km2, question=question, question_type=question_type, now=now,
    )

    # AFTER the constraint checks, deliberately. A hard, verifiable API violation -- a
    # non-US point, a 30 m granularity that does not exist, a date outside coverage --
    # is a better thing to tell someone than "I did not understand you", and it is true
    # regardless of what they meant. "I could not read the question" is the last resort,
    # not the first excuse.
    if refusal is None and unrecognised:
        refusal = (RefusalReason.UNRECOGNISED_QUESTION, UNRECOGNISED_MESSAGE)

    if refusal is not None:
        reason, message = refusal
        return LayerChoice(
            question_type=question_type,
            endpoint=None, filter_type=None, analytic_type=None, granularity=None,
            rationale=(
                f"Refused before any call was made, so no credit was spent. {message}"
            ),
            refusal=reason,
            refusal_message=message,
            escalated_from=escalated_from,
        )

    plan = DECISION_TABLE[question_type]

    rationale = plan.rationale
    if escalated_from is not None:
        rationale = (
            f"{rationale} (Read as a duration question rather than "
            f"{escalated_from.value}: the wording carries a duration marker, and the "
            f"{escalated_from.value} layer would have answered with a single hour or an "
            f"aggregate temperature. Escalated to the broader layer deliberately.)"
        )

    resolved_threshold_f: float | None = None
    basis: str | None = None
    if plan.needs_threshold:
        resolved_threshold_f = (
            threshold_f if threshold_f is not None else load_thresholds().unsafe_from_f
        )
        basis = "heat_index_f"

    choice = LayerChoice(
        question_type=question_type,
        endpoint=plan.endpoint,
        filter_type=plan.filter_type,
        analytic_type=plan.analytic_type,
        granularity=granularity if granularity is not None else plan.granularity,
        rationale=rationale,
        wrong_answer_if_snapshot=plan.wrong_answer_if_snapshot,
        escalated_from=escalated_from,
        threshold_f=resolved_threshold_f,
        threshold_basis=basis,
        direction=plan.direction,
        params={
            "polygon_aoi_required": True,
            "start_date": date,
            "end_date": end_date,
            "filter_type": plan.filter_type,
            "analytic_type": plan.analytic_type.value if plan.analytic_type else None,
            "granularity": granularity if granularity is not None else plan.granularity,
            "direction": plan.direction,
            # Deliberately NOT `threshold`. tools.py must convert heat index -> air
            # temperature and °F -> °C before anything reaches the wire.
            "threshold_f_unresolved": resolved_threshold_f,
        },
    )

    _assert_invariants(question, choice)
    return choice
