"""
Threshold and band tests — pure logic. No network, no credits, no API key.

T2's ask was "verify the numbers, confirm the action mapping is sane". These tests are
that verification in executable form. Two things they pin:

1. TOTALITY. Every finite heat index maps to exactly one NWS band and exactly one OSHA
   action. The draft table had two holes — 90.5 F and 125 F matched nothing — because the
   bounds were copied from a secondary source that transcribes the NWS chart as
   "Extreme Caution 91-103" and "Extreme Danger 126+". The primary source says 90-103 and
   125+. A lookup returning None in a heat-safety tool is a decision quietly not made.

2. THE BOUNDARY VALUES THEMSELVES, against the primary sources, so that a future edit
   that reintroduces the secondary-source numbers fails here rather than in the demo.
"""

import math

import pytest

from heatguard.bands import (
    ThresholdConfigError,
    _parse_table,
    action_for,
    band_for,
    is_unsafe,
    load_thresholds,
)


# --------------------------------------------------------------------- totality

@pytest.mark.parametrize("table_name", ["nws_bands", "osha_actions"])
def test_tables_are_contiguous(table_name):
    """Structural proof: each band ends exactly where the next begins."""
    table = getattr(load_thresholds(), table_name)
    for lower, upper in zip(table, table[1:]):
        assert lower.max_f == upper.min_f, (
            f"{table_name}: {lower.id} ends {lower.max_f}, {upper.id} starts {upper.min_f}"
        )


@pytest.mark.parametrize("lookup", [band_for, action_for])
def test_lookup_is_total_over_the_working_range(lookup):
    """Sweep the whole plausible range in half-degree steps. Nothing may fall through."""
    t = -99.0
    while t < 999.0:
        assert lookup(t) is not None
        t += 0.5


@pytest.mark.parametrize("lookup", [band_for, action_for])
@pytest.mark.parametrize("value", [80.0, 90.0, 90.5, 91.0, 103.0, 115.0, 124.9, 125.0, 126.0])
def test_the_specific_values_that_used_to_fall_through(lookup, value):
    """90.5 and 125.0 matched no band in the draft. This is the regression."""
    assert lookup(value) is not None


@pytest.mark.parametrize("lookup", [band_for, action_for])
def test_no_value_matches_two_bands(lookup):
    """Half-open intervals mean the boundary belongs to the upper band, not both."""
    thresholds = load_thresholds()
    for table in (thresholds.nws_bands, thresholds.osha_actions):
        for value in (80.0, 90.0, 91.0, 103.0, 115.0, 125.0):
            assert sum(b.contains(value) for b in table) == 1


# ------------------------------------------------------- NWS boundaries, verified

@pytest.mark.parametrize("heat_index_f, expected", [
    (79.9, "below_caution"),
    (80.0, "caution"),          # NWS: Caution 80-90
    (89.9, "caution"),
    (90.0, "extreme_caution"),  # NWS: Extreme Caution 90-103, NOT 91
    (102.9, "extreme_caution"),
    (103.0, "danger"),          # NWS: Danger 103-124
    (124.9, "danger"),
    (125.0, "extreme_danger"),  # NWS: Extreme Danger 125+, NOT 126
    (140.0, "extreme_danger"),
])
def test_nws_band_boundaries(heat_index_f, expected):
    assert band_for(heat_index_f).id == expected


def test_the_osha_86f_datum_lands_in_caution():
    """The whole thesis in one assertion.

    OSHA: "Outdoor workers have died of heat stroke when the day's maximum Heat Index was
    only 86 F." If 86 F reads as merely 'Caution', then the daily maximum cannot be the
    thing that decides safety — which is the argument for measuring duration.
    """
    assert band_for(86.0).id == "caution"


# --------------------------------------------------------- OSHA action ladder

@pytest.mark.parametrize("heat_index_f, expected_action", [
    (75.0, "work"),
    (80.0, "work_with_provision"),      # OSHA: protective measures from 80 F up
    (90.9, "work_with_provision"),
    (91.0, "rest_breaks_55_5"),         # OSHA moderate risk: 91-103
    (102.9, "rest_breaks_55_5"),
    (103.0, "rest_breaks_50_10"),       # OSHA high risk: 103-115
    (114.9, "rest_breaks_50_10"),
    (115.0, "stop_nonessential"),       # OSHA very high / extreme: 115+
    (130.0, "stop_nonessential"),
])
def test_osha_action_ladder(heat_index_f, expected_action):
    assert action_for(heat_index_f).action == expected_action


def test_the_action_ladder_splits_where_nws_does_not():
    """115 F is an OSHA breakpoint and not an NWS one. Keeping the tables separate is
    the reason the tool does not recommend the same control at 104 F and at 124 F."""
    assert band_for(104.0).id == band_for(124.0).id == "danger"
    assert action_for(104.0).action != action_for(124.0).action


def test_actions_escalate_monotonically():
    """Severity must never go down as it gets hotter."""
    order = ["work", "work_with_provision", "rest_breaks_55_5",
             "rest_breaks_50_10", "stop_nonessential"]
    seen = [action_for(t).action for t in range(-50, 200, 1)]
    ranks = [order.index(a) for a in seen]
    assert ranks == sorted(ranks)


def test_every_action_carries_a_readable_instruction():
    for band in load_thresholds().osha_actions:
        assert len(band.label) > 20, f"{band.id} has no usable instruction"


# ---------------------------------------------------------- the unsafe threshold

def test_unsafe_threshold_does_not_contradict_the_thesis():
    """A threshold of 103 F would make the headline metric blind to the 86-103 F range
    the project's own argument says people die in. 91 F is where OSHA first prescribes a
    work/rest cycle rather than general advice."""
    assert load_thresholds().unsafe_from_f == 91.0


def test_unsafe_threshold_sits_on_an_osha_breakpoint():
    """Not an arbitrary number — it must be the bottom edge of an action band."""
    unsafe = load_thresholds().unsafe_from_f
    assert any(b.min_f == unsafe for b in load_thresholds().osha_actions)


@pytest.mark.parametrize("heat_index_f, threshold_f, expected", [
    (90.9, 91.0, False),
    (91.0, 91.0, True),      # at the threshold counts as unsafe
    (102.9, 103.0, False),
    (103.0, 103.0, True),
])
def test_is_unsafe_boundaries(heat_index_f, threshold_f, expected):
    assert is_unsafe(heat_index_f, threshold_f) is expected


def test_sensitivity_thresholds_include_both_candidates():
    """T7 must report the headline number at 91 AND 103. A result that only holds at one
    threshold is a result about the threshold."""
    assert set(load_thresholds().sensitivity_thresholds_f) == {91.0, 103.0}


# ------------------------------------------------------------ config validation

def test_non_finite_input_raises_rather_than_guessing():
    for bad in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError):
            band_for(bad)


def test_a_gap_in_the_table_is_rejected_at_load():
    """This is the exact defect the draft shipped with."""
    rows = [
        {"id": "caution", "min_f": 80, "max_f": 90, "label": "x"},
        {"id": "extreme_caution", "min_f": 91, "max_f": 103, "label": "x"},  # gap at 90-91
    ]
    with pytest.raises(ThresholdConfigError, match="gap"):
        _parse_table(rows, name="nws_bands", with_action=False)


def test_an_overlap_in_the_table_is_rejected_at_load():
    rows = [
        {"id": "a", "min_f": 80, "max_f": 95, "label": "x"},
        {"id": "b", "min_f": 90, "max_f": 103, "label": "x"},
    ]
    with pytest.raises(ThresholdConfigError, match="overlap"):
        _parse_table(rows, name="nws_bands", with_action=False)


def test_an_inverted_band_is_rejected_at_load():
    rows = [{"id": "a", "min_f": 100, "max_f": 80, "label": "x"}]
    with pytest.raises(ThresholdConfigError, match="min_f"):
        _parse_table(rows, name="nws_bands", with_action=False)


def test_an_action_row_without_an_action_is_rejected():
    rows = [{"id": "a", "min_f": 80, "max_f": 90, "label": "x", "action": ""}]
    with pytest.raises(ThresholdConfigError, match="no action"):
        _parse_table(rows, name="osha_actions", with_action=True)


# ------------------------------------------------------------------- metadata

def test_units_are_fahrenheit_and_the_metric_is_heat_index():
    """T4 must confirm /v1/env_params returns heat index in Fahrenheit. If it returns
    Celsius, every number in thresholds.yaml is wrong by a plausible-looking factor."""
    t = load_thresholds()
    assert t.units == "fahrenheit"
    assert t.metric == "heat_index"


def test_the_disclaimer_names_the_wbgt_limitation(thresholds):
    """OSHA's own thresholds are WBGT-based. Hiding that would be the weaker choice."""
    assert "WBGT" in thresholds["disclaimer"]
