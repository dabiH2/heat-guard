"""
Router tests — pure logic. No network, no credits, no API key.

Get these green before anything else is built on top. They are also the cheapest
possible proof to a judge that layer selection is deliberate rather than incidental.
"""

import pytest

from heatguard.router import QuestionType, RefusalReason, classify, route


# ---------------------------------------------------------------- classification

@pytest.mark.parametrize("question, expected", [
    ("Is it safe at site 3 right now?",                    QuestionType.SNAPSHOT),
    ("When should we start and stop today?",               QuestionType.INTRADAY),
    ("Will we cross the threshold in the next few hours?", QuestionType.FORECAST),
    ("How long were they above the danger band?",          QuestionType.DURATION),
    ("Is site 3 chronically dangerous?",                   QuestionType.PERSISTENCE),
    ("Which of our 12 sites is worst?",                    QuestionType.COMPARISON),
])
def test_classify(question, expected):
    assert classify(question) == expected


# ------------------------------------------------- the failure this project exists for

@pytest.mark.parametrize("question", [
    "How long were they above the danger band?",
    "Is this site chronically dangerous?",
    "What's it typically like here in July?",
    "Which site is worst this summer?",
])
def test_duration_questions_never_use_single_hour(question):
    """A duration question answered with filter_type=1 returns a confident wrong number."""
    choice = route(question, lat=33.45, lon=-112.07, date="2025-07-15")
    assert choice.filter_type != 1


def test_router_always_explains_itself():
    choice = route("Is it safe right now?", lat=33.45, lon=-112.07, date="2025-07-15")
    assert choice.rationale, "every choice must carry a rationale — it is shown and spoken"


def test_router_is_deterministic():
    args = dict(lat=33.45, lon=-112.07, date="2025-07-15")
    a = route("Which site is worst this summer?", **args)
    b = route("Which site is worst this summer?", **args)
    assert a == b, "demo takes must reproduce exactly"


# ---------------------------------------------------------------- refusals

def test_refuses_outside_us():
    c = route("Is it safe right now?", lat=45.46, lon=9.19, date="2025-07-15")  # Milan
    assert c.refused and c.refusal is RefusalReason.OUTSIDE_US


def test_refuses_before_2021():
    c = route("Is it safe right now?", lat=33.45, lon=-112.07, date="2019-07-15")
    assert c.refused and c.refusal is RefusalReason.BEFORE_2021


def test_refuses_beyond_forecast_horizon():
    c = route("Will we cross the threshold next week?", lat=33.45, lon=-112.07, date="2099-01-01")
    assert c.refused and c.refusal is RefusalReason.BEYOND_FORECAST


def test_refuses_oversized_aoi():
    # AOI geometry is wired (scripts/build_sites.py), so this is now real. The cap is
    # 15 mi2 / ~38.85 km2 on the hackathon plan, not the handbook's 130 km2.
    from heatguard.tools import MAX_AOI_KM2
    c = route("Is it safe right now?", lat=33.45, lon=-112.07, date="2025-07-15",
              aoi_km2=MAX_AOI_KM2 + 1)
    assert c.refused and c.refusal is RefusalReason.AOI_TOO_LARGE


def test_refuses_too_fine_granularity():
    c = route("Show me street-level detail at 10m", lat=33.45, lon=-112.07, date="2025-07-15")
    assert c.refused and c.refusal is RefusalReason.GRANULARITY_TOO_FINE


def test_refusals_carry_a_human_message():
    c = route("Is it safe right now?", lat=45.46, lon=9.19, date="2025-07-15")
    assert c.refusal_message, "a refusal the operator cannot read is a bug"
