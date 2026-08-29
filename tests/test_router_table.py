"""
Router decision-table tests — pure logic. No network, no credits, no API key.

`tests/test_router.py` holds the original contract and must keep passing untouched. This
file is the full T6 surface: every row of the decision table, every refusal, and — most
importantly — the INVARIANTS, which are the only part of the router that is allowed to
crash the process.

The reason the invariants are tested this hard: layer selection here does not depend on
the classifier being right. If it did, one missing synonym would silently reintroduce the
exact failure the project exists to prevent, and it would reintroduce it as a
well-formatted answer with no error attached. So `route` re-checks its own output against
the question text and raises. These tests prove the raise actually happens.
"""

from datetime import datetime, timedelta, timezone

import pytest

from heatguard.bands import load_thresholds
from heatguard.router import (
    DECISION_TABLE,
    DURATION_MARKERS,
    AnalyticType,
    QuestionType,
    RefusalReason,
    RouterInvariantError,
    check_refusals,
    classify,
    has_duration_marker,
    route,
)
from heatguard.tools import GRANULARITIES, MAX_AOI_KM2, MAX_DAYS_PER_CALL

PHX = dict(lat=33.4509, lon=-112.0732)          # Chase Tower, the lead site
MILAN = dict(lat=45.46, lon=9.19)
NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
PAST = "2025-07-15"


def r(question, **kw):
    """route() with the Phoenix site, a past date and a frozen clock."""
    args = {**PHX, "date": PAST, "now": NOW, **kw}
    return route(question, **args)


# ------------------------------------------------------------- table completeness

def test_every_question_type_has_a_row():
    assert set(DECISION_TABLE) == set(QuestionType)


def test_every_row_explains_itself_and_the_counterfactual():
    """Both sentences get spoken in the demo video, so both must actually exist."""
    for question_type, plan in DECISION_TABLE.items():
        assert len(plan.rationale) > 60, f"{question_type}: rationale too thin"
        assert len(plan.wrong_answer_if_snapshot) > 40, f"{question_type}: no counterfactual"


def test_every_row_names_its_own_parameters_in_its_rationale():
    """A rationale that does not state the parameters cannot be audited against the call."""
    for question_type, plan in DECISION_TABLE.items():
        assert f"filter_type={plan.filter_type}" in plan.rationale, question_type
        if plan.analytic_type:
            assert f"analytic_type={plan.analytic_type.value}" in plan.rationale, question_type


def test_exceedance_and_persistence_rows_always_carry_threshold_and_direction():
    """The API rejects the call without both; the client raises ValueError."""
    for question_type, plan in DECISION_TABLE.items():
        if plan.analytic_type in (AnalyticType.EXCEEDANCE, AnalyticType.PERSISTENCE):
            assert plan.needs_threshold, question_type
            assert plan.direction in ("above", "below"), question_type


def test_only_the_snapshot_row_uses_a_single_hour():
    """filter_type=1 answers exactly one of the six questions. Any other row using it is
    the bug this project is about."""
    single_hour = [q for q, p in DECISION_TABLE.items() if p.filter_type == 1]
    assert single_hour == [QuestionType.SNAPSHOT]


def test_granularity_is_constant_across_the_table():
    """Comparison ranks sites against each other. Varying resolution between them would
    rank them by resolution."""
    granularities = {p.granularity for p in DECISION_TABLE.values()}
    assert len(granularities) == 1
    assert granularities.pop() in GRANULARITIES


# ------------------------------------------------------------------ classification

@pytest.mark.parametrize("question, expected", [
    # snapshot
    ("Is it safe at site 3 right now?",                      QuestionType.SNAPSHOT),
    ("What's the temperature at the Chase Tower block?",     QuestionType.SNAPSHOT),
    # intraday
    ("When should we start and stop today?",                 QuestionType.INTRADAY),
    ("What time is the safe window at Encanto Park?",        QuestionType.INTRADAY),
    # forecast
    ("Will we cross the threshold in the next few hours?",   QuestionType.FORECAST),
    ("Is it going to get worse later today?",                QuestionType.FORECAST),
    # duration
    ("How long were they above the danger band?",            QuestionType.DURATION),
    ("How many hours over threshold on the ramp?",           QuestionType.DURATION),
    ("Were they above it for six hours straight?",           QuestionType.DURATION),
    # persistence (chronic — across days)
    ("Is site 3 chronically dangerous?",                     QuestionType.PERSISTENCE),
    ("What's it typically like here in July?",               QuestionType.PERSISTENCE),
    ("Is this a structural problem or one bad week?",        QuestionType.PERSISTENCE),
    # comparison
    ("Which of our 12 sites is worst?",                      QuestionType.COMPARISON),
    ("Rank the sites by exposure.",                          QuestionType.COMPARISON),
    ("Compare Sky Harbor and Encanto Park.",                 QuestionType.COMPARISON),
])
def test_classify(question, expected):
    assert classify(question) == expected


def test_classification_is_case_insensitive():
    assert classify("HOW LONG WERE THEY ABOVE THE BAND?") == QuestionType.DURATION


def test_unrecognised_questions_are_refused_not_guessed():
    """THE DUSTBIN REGRESSION.

    This test used to assert the opposite, and justified it on cost: "falling back to a
    broad layer would spend credits on a guess." That let a cost argument beat a safety
    argument inside a safety tool, and it contradicted the rule asserted eight tests
    below -- being wrong toward more data costs a credit, being wrong toward less costs
    a wrong call.

    It was not theoretical. SNAPSHOT had no markers of its own, so it was where every
    unrecognised phrasing landed, and SNAPSHOT is the single-hour `tcm` layer this whole
    project exists to warn people off. Eleven of fifteen realistic supervisor paraphrases
    came back as a one-hour reading, including "should I send the crew out for the full
    day?" -- a duration question in plain English, answered with one hour.

    Guessing broad and guessing narrow are both wrong. Not guessing is free.
    """
    assert classify("hello") is None
    assert classify("give me the numbers for this site") is None

    choice = r("hello")
    assert choice.refused
    assert choice.refusal is RefusalReason.UNRECOGNISED_QUESTION
    assert choice.filter_type is None and choice.analytic_type is None


def test_the_unrecognised_refusal_names_what_would_work():
    """A refusal that does not say what WOULD work is a dead end, not a safeguard."""
    message = r("hello").refusal_message.lower()
    for family in ("current reading", "how long", "which site", "later today"):
        assert family in message, f"{family!r} missing from the refusal message"


def test_snapshot_must_now_be_asked_for_explicitly():
    """Snapshot stays reachable -- it is a legitimate question, just no longer the place
    unrecognised text falls into."""
    for question in ("How hot is it right now?", "What is the temperature?",
                     "Current heat index at this site"):
        assert classify(question) is QuestionType.SNAPSHOT
        assert DECISION_TABLE[QuestionType.SNAPSHOT].filter_type == 1


def test_a_duration_marker_rescues_an_otherwise_unreadable_question():
    """The marker list is authoritative over the classifier and always has been. It must
    keep working when the classifier returns nothing at all, or the new refusal would
    swallow the exact questions that matter most."""
    choice = r("tell me about the worst of it out there")
    assert not choice.refused
    assert choice.question_type is QuestionType.DURATION
    assert choice.escalated_from is QuestionType.SNAPSHOT


def test_a_hard_api_violation_outranks_not_understanding_the_question():
    """"That granularity does not exist" is true regardless of what they meant, and is a
    more useful thing to be told than "I could not read you". The unrecognised refusal is
    the last resort, not the first excuse."""
    choice = r("mumble mumble at 30 m", granularity=30)
    assert choice.refusal is RefusalReason.GRANULARITY_TOO_FINE


def test_comparison_outranks_duration_when_both_markers_are_present():
    """'Which site is worst this summer?' carries comparison, persistence AND duration
    markers. Comparison wins — but the duration invariant still binds."""
    q = "Which site is worst this summer?"
    assert classify(q) == QuestionType.COMPARISON
    assert has_duration_marker(q)
    assert r(q).filter_type != 1


# ---------------------------------------- the failure this project exists to prevent

@pytest.mark.parametrize("question", [
    "How long were they above the danger band?",
    "Is this site chronically dangerous?",
    "What's it typically like here in July?",
    "Which site is worst this summer?",
    "How many hours above threshold?",
    "Were they above it for five hours straight?",
    "Was it sustained all day?",
    "What's it historically like on this block?",
])
def test_duration_questions_never_use_a_single_hour(question):
    assert r(question, end_date="2025-07-29").filter_type != 1


@pytest.mark.parametrize("question", [
    "How long were they above the danger band?",
    "How many hours above threshold?",
    "Which site is worst this summer?",
])
def test_duration_questions_never_use_tcm(question):
    """The subtler half. filter_type=3 + tcm returns a whole day of data and still
    answers the wrong question — aggregate temperature, never a count of hours."""
    choice = r(question, end_date="2025-07-29")
    assert choice.analytic_type is not AnalyticType.TCM


@pytest.mark.parametrize("marker", DURATION_MARKERS)
def test_every_declared_duration_marker_is_honoured(marker):
    """Each marker in the published list must actually change the layer, not just sit
    in a tuple looking reassuring."""
    choice = r(f"Tell me about {marker} at this site", end_date="2025-07-29")
    assert choice.filter_type != 1
    assert choice.analytic_type is not AnalyticType.TCM


# -------------------------------------------------------- duration escalation

def test_a_classifier_miss_escalates_instead_of_answering_with_one_hour():
    """'Tell me about the worst at this site' carries the authoritative marker 'worst'
    but matches none of the comparison phrasings. The marker wins over the classifier."""
    c = r("Tell me about the worst at this site")
    assert c.escalated_from is QuestionType.SNAPSHOT
    assert c.question_type is QuestionType.DURATION
    assert c.filter_type == 3
    assert c.analytic_type is AnalyticType.EXCEEDANCE


def test_escalation_is_recorded_in_the_rationale_not_hidden():
    """An audit trail that silently rewrote its own question is not an audit trail."""
    c = r("Tell me about the worst at this site")
    assert "duration marker" in c.rationale
    assert "snapshot" in c.rationale


def test_escalation_leaves_alone_the_types_that_already_measure_duration():
    """COMPARISON and PERSISTENCE already route to exceedance, so a duration marker
    changes nothing and must not silently rewrite the question type."""
    c = r("Which site is worst this summer?", end_date="2025-07-29")
    assert c.question_type is QuestionType.COMPARISON
    assert c.escalated_from is None


def test_no_escalation_when_there_is_no_duration_marker():
    c = r("Is it safe right now?")
    assert c.escalated_from is None
    assert c.question_type is QuestionType.SNAPSHOT
    assert c.filter_type == 1


def test_a_forecast_phrasing_carrying_a_duration_marker_also_escalates():
    """'worst' is an authoritative duration marker but matches no classifier DURATION
    phrasing, so this lands on FORECAST — whose row is tcm, aggregate temperature."""
    c = r("Will it be worst later today?")
    assert c.escalated_from is QuestionType.FORECAST
    assert c.analytic_type is AnalyticType.EXCEEDANCE


def test_a_duration_phrasing_needs_no_escalation():
    """'sustained' is in the classifier's own DURATION list, so it routes there directly.
    Escalation is the safety net, not the mechanism."""
    c = r("Will it be sustained for the rest of the shift?")
    assert c.question_type is QuestionType.DURATION
    assert c.escalated_from is None


def test_escalation_direction_is_always_toward_more_data_never_less():
    """Being wrong toward the broader layer costs a credit. Being wrong toward the
    narrower one costs a wrong operational decision. So no escalation may ever land on
    a row that uses a single hour or aggregate temperature."""
    for question in ("Tell me about the worst at this site",
                     "Will it be worst later today?"):
        c = r(question)
        assert c.escalated_from is not None
        assert c.filter_type != 1
        assert c.analytic_type is not AnalyticType.TCM


# ------------------------------------------------------------------- invariants

def test_invariant_raises_rather_than_returning_a_known_wrong_layer(monkeypatch):
    """Force the table into the bad state and prove the router refuses to emit it.

    A safety tool must crash rather than hand back a layer it has already determined
    cannot answer the question.
    """
    from heatguard import router as router_mod

    broken = dict(DECISION_TABLE)
    broken[QuestionType.DURATION] = router_mod.Plan(
        endpoint="/v1/heatmap", filter_type=1, analytic_type=AnalyticType.TCM,
        granularity=100, direction=None, needs_threshold=False,
        rationale="x" * 80, wrong_answer_if_snapshot="y" * 50,
    )
    monkeypatch.setattr(router_mod, "DECISION_TABLE", broken)

    with pytest.raises(RouterInvariantError, match="single hour cannot answer how long"):
        r("How long were they above the danger band?")


def test_invariant_catches_a_missing_threshold(monkeypatch):
    from heatguard import router as router_mod

    broken = dict(DECISION_TABLE)
    broken[QuestionType.DURATION] = router_mod.Plan(
        endpoint="/v1/heatmap", filter_type=3, analytic_type=AnalyticType.EXCEEDANCE,
        granularity=100, direction="above", needs_threshold=False,   # <- the bug
        rationale="x" * 80, wrong_answer_if_snapshot="y" * 50,
    )
    monkeypatch.setattr(router_mod, "DECISION_TABLE", broken)

    with pytest.raises(RouterInvariantError, match="requires both a threshold"):
        r("How long were they above the danger band?")


def test_invariants_do_not_fire_on_the_real_table():
    """The shipped table must satisfy its own post-conditions on every question type."""
    for question in ("Is it safe right now?", "When should we start and stop today?",
                     "Will we cross the threshold soon?", "How long were they above it?",
                     "Is it chronically dangerous?", "Which site is worst?"):
        r(question, end_date="2025-07-29")


# ---------------------------------------------------------------------- refusals

def test_refuses_outside_us_and_says_it_would_have_been_billed():
    """Non-US does not error, it returns an empty-looking result AND spends the credit,
    so this refusal is a cost control, not a formality."""
    c = r("Is it safe right now?", **MILAN)
    assert c.refused and c.refusal is RefusalReason.OUTSIDE_US
    assert "credit" in c.refusal_message


def test_refuses_before_2021():
    c = r("Is it safe right now?", date="2019-07-15")
    assert c.refused and c.refusal is RefusalReason.BEFORE_2021


def test_accepts_the_first_day_of_MEASURED_coverage():
    """2022-01-01, not the documented 2021-01-01. Measured on PHX-CHASE: 2021-07-15 and
    2021-10-15 both returned Completed with zero tiles and were billed 4,220 credits
    each; 2022-01-15 returned 10 tiles."""
    from heatguard.tools import EARLIEST_DATE
    assert EARLIEST_DATE == "2022-01-01"
    assert not r("Is it safe right now?", date="2022-01-01").refused


def test_refuses_the_documented_but_empty_2021_dates():
    """The documented start date is a year early. A date inside that gap does not
    error — it returns an empty result at full price, which is the same silent-and-billed
    shape as a non-US AOI."""
    for date in ("2021-01-01", "2021-07-15", "2021-10-15", "2021-12-31"):
        choice = r("Is it safe right now?", date=date)
        assert choice.refused and choice.refusal is RefusalReason.BEFORE_2021, date
        assert "billed" in choice.refusal_message


def test_refuses_dates_the_api_rejects_outright():
    """MEASURED: start_date >= today+2 returns HTTP 400 'is in the future'."""
    beyond = (NOW + timedelta(days=3)).date().isoformat()
    c = r("Will we cross the threshold?", date=beyond)
    assert c.refused and c.refusal is RefusalReason.BEYOND_FORECAST


def test_refuses_tomorrow_even_though_the_api_accepts_and_bills_for_it():
    """The finding that matters most from T4.

    Tomorrow is accepted (HTTP 200), costs 4,220 credits, and returns ONE FLAT VALUE for
    the whole day — measured 34.34 °C with minimum equal to maximum, against 33.7-41.9 °C
    for today. Exceedance against a constant is exactly 0 or exactly 24 hours. The
    boundary that matters is where the diurnal profile stops, not where the API stops
    accepting requests.
    """
    tomorrow = (NOW + timedelta(days=1)).date().isoformat()
    c = r("Will we cross the threshold?", date=tomorrow)
    assert c.refused and c.refusal is RefusalReason.BEYOND_FORECAST
    assert "flat" in c.refusal_message
    assert "charge you" in c.refusal_message


def test_accepts_today():
    assert not r("Will we cross the threshold?", date=NOW.date().isoformat()).refused


def test_the_two_future_refusals_explain_themselves_differently():
    """Tomorrow and next week fail for different reasons and must say so."""
    tomorrow = r("Will it?", date=(NOW + timedelta(days=1)).date().isoformat())
    next_week = r("Will it?", date=(NOW + timedelta(days=7)).date().isoformat())
    assert tomorrow.refusal_message != next_week.refusal_message
    assert "flat" in tomorrow.refusal_message
    assert "rejects" in next_week.refusal_message


def test_refuses_a_span_longer_than_thirty_days():
    """The API truncates quietly past 30 days, so a long span comes back looking fine."""
    c = r("Is it chronically dangerous?", date="2025-06-01", end_date="2025-07-31")
    assert c.refused and c.refusal is RefusalReason.EXCEEDS_30_DAY_WINDOW
    assert "truncated" in c.refusal_message


def test_accepts_a_span_of_exactly_thirty_days():
    c = r("Is it chronically dangerous?", date="2025-07-01", end_date="2025-07-30")
    assert not c.refused


def test_refuses_oversized_aoi():
    """Built once AOI geometry was wired — see scripts/build_sites.py."""
    c = r("Is it safe right now?", aoi_km2=MAX_AOI_KM2 + 1)
    assert c.refused and c.refusal is RefusalReason.AOI_TOO_LARGE


def test_accepts_a_real_site_aoi():
    """Our sites are 0.124 km², ~313x under the cap."""
    assert not r("Is it safe right now?", aoi_km2=0.124).refused


@pytest.mark.parametrize("granularity", [10, 20, 45, 75, 250])
def test_refuses_granularities_the_api_does_not_offer(granularity):
    c = r("Is it safe right now?", granularity=granularity)
    assert c.refused and c.refusal is RefusalReason.GRANULARITY_TOO_FINE


@pytest.mark.parametrize("granularity", GRANULARITIES)
def test_accepts_every_real_granularity(granularity):
    assert not r("Is it safe right now?", granularity=granularity).refused


def test_reads_granularity_out_of_the_question_text():
    c = r("Show me street-level detail at 10m")
    assert c.refused and c.refusal is RefusalReason.GRANULARITY_TOO_FINE
    assert "20 m spatial resolution" in c.refusal_message


def test_refuses_a_chronic_question_scoped_to_one_day():
    """THE differentiator refusal: the call would succeed and the answer would be
    worthless. One bad day looks structural."""
    c = r("Is this site chronically dangerous?")     # no end_date
    assert c.refused and c.refusal is RefusalReason.WRONG_LAYER_WOULD_MISLEAD
    assert "one bad day" in c.refusal_message.lower()


def test_accepts_a_chronic_question_given_a_date_range():
    c = r("Is this site chronically dangerous?", end_date="2025-07-29")
    assert not c.refused
    assert c.filter_type == 4


def test_refuses_a_duration_question_scoped_to_a_single_hour():
    c = r("How long were they above the band at 2pm?")
    assert c.refused and c.refusal is RefusalReason.WRONG_LAYER_WOULD_MISLEAD
    assert "instant" in c.refusal_message


def test_every_refusal_carries_a_human_message():
    for choice in (r("Is it safe?", **MILAN),
                   r("Is it safe?", date="2019-01-01"),
                   r("Is it safe?", granularity=10),
                   r("Is it chronically dangerous?")):
        assert choice.refusal_message, "a refusal the operator cannot read is a bug"
        assert len(choice.refusal_message) > 40


def test_a_refusal_spends_no_credit_and_says_so():
    c = r("Is it safe right now?", **MILAN)
    assert c.endpoint is None and c.filter_type is None
    assert "no credit was spent" in c.rationale


def test_unreadable_dates_are_refused_not_crashed():
    assert r("Is it safe right now?", date="15/07/2025").refused


# ----------------------------------------------------------------- refusal priority

def test_coverage_outranks_everything_else():
    """Milan, in 2019, at 10 m, over a huge AOI — all four are wrong. Coverage wins,
    deterministically, because it is the one that costs money to discover."""
    c = route("How long at 10m?", lat=45.46, lon=9.19, date="2019-01-01",
              aoi_km2=999.0, now=NOW)
    assert c.refusal is RefusalReason.OUTSIDE_US


def test_date_outranks_request_shape():
    c = r("Is it safe right now?", date="2019-01-01", granularity=10, aoi_km2=999.0)
    assert c.refusal is RefusalReason.BEFORE_2021


def test_layer_mismatch_is_checked_last():
    """It is only meaningful once the request is otherwise valid."""
    c = r("Is this site chronically dangerous?", granularity=10)
    assert c.refusal is RefusalReason.GRANULARITY_TOO_FINE


def test_check_refusals_is_usable_on_its_own():
    assert check_refusals(lat=33.45, lon=-112.07, date=PAST, now=NOW) is None
    assert check_refusals(lat=45.46, lon=9.19, date=PAST, now=NOW) is not None


# ------------------------------------------------------------------ unit discipline

def test_the_router_never_emits_a_bare_threshold():
    """A bare `threshold` is the °C/°F trap. Every emitted threshold must be
    unit-suffixed and must declare what it is measured against."""
    c = r("How long were they above the danger band?")
    assert "threshold" not in c.params
    assert c.threshold_f is not None
    assert c.threshold_basis == "heat_index_f"


def test_the_threshold_defaults_to_the_osha_policy_number():
    c = r("How long were they above the danger band?")
    assert c.threshold_f == load_thresholds().unsafe_from_f == 91.0


def test_the_threshold_can_be_overridden_for_sensitivity_reporting():
    """T7 reports the headline metric at 91 AND 103."""
    assert r("How long were they above it?", threshold_f=103.0).threshold_f == 103.0


def test_snapshot_carries_no_threshold_at_all():
    c = r("Is it safe right now?")
    assert c.threshold_f is None and c.direction is None


def test_the_unresolved_threshold_is_named_so_tools_must_convert_it():
    """params carries `threshold_f_unresolved`, not `threshold`, so a caller that passes
    params straight to the API gets a KeyError instead of a wrong answer."""
    c = r("How long were they above the danger band?")
    assert c.params["threshold_f_unresolved"] == 91.0
    assert "threshold" not in c.params


# ------------------------------------------------------------------- determinism

def test_router_is_deterministic():
    args = dict(**PHX, date=PAST, end_date="2025-07-29", now=NOW)
    assert route("Which site is worst this summer?", **args) == \
           route("Which site is worst this summer?", **args)


def test_router_is_deterministic_without_an_injected_clock():
    """Demo takes must reproduce even when `now` is the real wall clock, which means no
    timestamp may leak into the output."""
    args = dict(**PHX, date=PAST)
    assert route("How long were they above it?", **args) == \
           route("How long were they above it?", **args)


def test_every_choice_explains_itself():
    for question in ("Is it safe right now?", "How long were they above it?",
                     "Which site is worst?", "When should we start and stop?"):
        assert r(question).rationale


def test_the_routing_spec_doc_has_not_drifted_from_the_code():
    """docs/routing_spec.md is what a judge reads. If it disagrees with DECISION_TABLE
    it is worse than no document at all."""
    from pathlib import Path
    spec = (Path(__file__).resolve().parents[1] / "docs" / "routing_spec.md").read_text(
        encoding="utf-8")
    for question_type in QuestionType:
        assert question_type.name in spec, f"{question_type.name} missing from the spec"
    for reason in RefusalReason:
        assert reason.name in spec, f"{reason.name} missing from the spec"
    for plan in DECISION_TABLE.values():
        if plan.analytic_type:
            assert plan.analytic_type.value in spec


def test_the_lead_demo_question_routes_to_exceedance():
    """The money shot: a night crew's duration question must land on exceedance, not on
    the tcm default that shares the same endpoint and filter_type."""
    c = r("How many hours were the night crew above the threshold?")
    assert c.endpoint == "/v1/heatmap"
    assert c.analytic_type is AnalyticType.EXCEEDANCE
    assert c.filter_type == 3
    assert c.direction == "above"
