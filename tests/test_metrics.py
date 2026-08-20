"""
Metric tests — pure logic. No network, no credits, no API key.

The headline number carries the 40% Impact criterion, which is the one weight verified
verbatim on camera. So the tests here are less about arithmetic than about the two ways
the number can be dishonest:

  1. counting hours nobody was standing in (outside the shift window), and
  2. letting two opposite-signed wins cancel each other to nearly zero.

The Chase Tower night crew is the case that breaks the naive metric, so it gets its own
section.
"""

import pytest

from heatguard.metrics import (
    BASELINE_SITE_ID,
    MetricsError,
    Shift,
    compare_to_baseline,
    exposure_hours_avoided,
    hours_above,
    readings_in_shift,
    rollup,
    shift_from_row,
    unsafe_hours_in_shift,
    worker_hours,
)

THRESHOLD = 91.0


def profile(date: str, values: dict[int, float]) -> list[tuple[str, float]]:
    """An hourly profile for `date`: {hour: heat_index_f}."""
    return [(f"{date}T{h:02d}:00:00", v) for h, v in sorted(values.items())]


def flat(date: str, value: float, hours=range(24)) -> list[tuple[str, float]]:
    return profile(date, {h: value for h in hours})


DAY = Shift(site_id="PHX-27TH", start="05:30", end="14:00", crew_size=22)
NIGHT = Shift(site_id="PHX-CHASE", start="21:00", end="05:30", crew_size=6)


# --------------------------------------------------------------------- shift windows

def test_day_shift_window():
    start, end = DAY.window("2025-07-15")
    assert start.isoformat() == "2025-07-15T05:30:00"
    assert end.isoformat() == "2025-07-15T14:00:00"
    assert DAY.length_hours == 8.5
    assert not DAY.crosses_midnight


def test_night_shift_window_rolls_into_the_next_day():
    start, end = NIGHT.window("2025-07-15")
    assert start.isoformat() == "2025-07-15T21:00:00"
    assert end.isoformat() == "2025-07-16T05:30:00"
    assert NIGHT.length_hours == 8.5
    assert NIGHT.crosses_midnight


def test_night_shift_length_is_not_negative():
    """A naive end-minus-start gives -15.5 h and silently zeroes the metric."""
    assert NIGHT.length_hours > 0


def test_shift_can_be_built_from_a_sites_csv_row(site_rows):
    row = next(r for r in site_rows if r["site_id"] == "PHX-CHASE")
    shift = shift_from_row(row)
    assert shift.crosses_midnight and shift.crew_size == 6


# ------------------------------------------------------------------------ counting

def test_hours_above_counts_the_threshold_itself():
    p = profile("2025-07-15", {0: 90.9, 1: 91.0, 2: 91.1})
    assert hours_above(p, THRESHOLD) == 2.0


def test_hours_above_is_zero_when_nothing_crosses():
    assert hours_above(flat("2025-07-15", 80.0), THRESHOLD) == 0.0


def test_only_hours_inside_the_shift_are_counted():
    """The T1 correction, enforced in code: hours nobody was standing in are not
    exposure. Hot all day, but this crew works 05:30-14:00."""
    p = profile("2025-07-15", {h: (120.0 if h >= 15 else 80.0) for h in range(24)})
    assert hours_above(p, THRESHOLD) == 9.0          # 15:00-23:00, all dangerous
    assert unsafe_hours_in_shift(p, DAY, "2025-07-15", THRESHOLD) == 0.0


def test_a_night_shift_reads_hours_from_both_calendar_days():
    p = (profile("2025-07-15", {h: (100.0 if h >= 21 else 70.0) for h in range(24)})
         + profile("2025-07-16", {h: (100.0 if h < 6 else 70.0) for h in range(24)}))
    inside = readings_in_shift(p, NIGHT, "2025-07-15")
    assert len(inside) == 9                           # 21,22,23 + 00..05
    # 8.5 h of shift, all of it above threshold — NOT 9.0. The 05:00 reading covers
    # 05:00-06:00 but the crew leaves at 05:30, so it contributes half an hour.
    assert unsafe_hours_in_shift(p, NIGHT, "2025-07-15", THRESHOLD) == 8.5


def test_a_boundary_reading_contributes_only_its_overlap():
    """The off-by-one that inflated every day shift by ~6%. A 05:00-13:30 shift holds
    nine hourly readings but only 8.5 hours of crew time."""
    p = flat("2025-07-15", 100.0)
    assert len(readings_in_shift(p, DAY, "2025-07-15")) == 9
    assert unsafe_hours_in_shift(p, DAY, "2025-07-15", THRESHOLD) == 8.5


def test_unsafe_hours_can_never_exceed_the_shift_length():
    for shift, days in ((DAY, ["2025-07-15"]), (NIGHT, ["2025-07-15", "2025-07-16"])):
        p = [r for d in days for r in flat(d, 130.0)]
        assert unsafe_hours_in_shift(p, shift, "2025-07-15", THRESHOLD) \
               == pytest.approx(shift.length_hours)


def test_a_night_shift_with_only_one_day_of_data_raises():
    """Silently returning 3 instead of 9 would undercount the lead demo site by two
    thirds. Refuse rather than report a short count."""
    p = flat("2025-07-15", 100.0)
    with pytest.raises(MetricsError, match="both calendar days"):
        unsafe_hours_in_shift(p, NIGHT, "2025-07-15", THRESHOLD)


def test_worker_hours_scale_with_crew_size():
    assert worker_hours(8.0, 22) == 176.0
    assert worker_hours(8.0, 4) == 32.0


# ------------------------------------------ the flaw that killed the original metric

def _night_crew_case():
    """Chase Tower night crew. The city-wide DAYTIME high is below the threshold at
    night, so the baseline says the shift is fine. The canyon says otherwise."""
    site = (profile("2025-07-15", {h: (96.0 if h >= 21 else 88.0) for h in range(24)})
            + profile("2025-07-16", {h: (96.0 if h < 6 else 88.0) for h in range(24)}))
    return compare_to_baseline(
        site_profile=site,
        baseline_scalar_f=88.0,        # city-wide figure, below the 91 °F threshold
        shift=NIGHT, date="2025-07-15", threshold_f=THRESHOLD,
    )


def test_the_naive_metric_goes_negative_on_the_projects_best_case():
    """THE reason 'exposure-hours avoided' was replaced. The tool did not avoid these
    hours, it revealed them — and revealing them is the entire point."""
    site = (profile("2025-07-15", {h: (96.0 if h >= 21 else 88.0) for h in range(24)})
            + profile("2025-07-16", {h: (96.0 if h < 6 else 88.0) for h in range(24)}))
    naive = exposure_hours_avoided(site, 88.0, NIGHT, "2025-07-15", THRESHOLD)
    assert naive < 0, "if this is ever >= 0 the demo's headline case has changed"


def test_the_decomposition_stays_positive_on_the_same_case():
    c = _night_crew_case()
    assert c.unsafe_hours_caught == 8.5
    assert c.unsafe_worker_hours_caught == 51.0        # 8.5 h x 6 crew
    assert c.productive_hours_recovered == 0.0


def test_the_two_counters_never_cancel():
    """One of them is always zero for a given site. That is what stops twelve correct
    calls from netting to approximately nothing."""
    for c in (_night_crew_case(), _over_warned_case()):
        assert c.unsafe_hours_caught == 0.0 or c.productive_hours_recovered == 0.0


def _over_warned_case():
    """Encanto Park. The city-wide figure says danger; the irrigated site is cooler."""
    site = flat("2025-07-15", 86.0)
    return compare_to_baseline(
        site_profile=site, baseline_scalar_f=104.0,
        shift=Shift("PHX-ENCA", "05:30", "14:00", 7), date="2025-07-15",
        threshold_f=THRESHOLD,
    )


def test_over_warning_is_counted_as_recovered_working_time():
    c = _over_warned_case()
    assert c.productive_hours_recovered == 8.5
    assert c.productive_worker_hours_recovered == pytest.approx(59.5)
    assert c.unsafe_hours_caught == 0.0


def test_agreement_changes_no_decision():
    site = flat("2025-07-15", 104.0)
    c = compare_to_baseline(
        site_profile=site, baseline_scalar_f=104.0,
        shift=Shift("PHX-SKY", "05:00", "13:30", 14), date="2025-07-15",
        threshold_f=THRESHOLD,
    )
    assert not c.decision_changed
    assert c.unsafe_hours_caught == 0.0 and c.productive_hours_recovered == 0.0
    assert "agrees with the city-wide call" in c.summary()


def test_every_comparison_produces_a_readable_line():
    for c in (_night_crew_case(), _over_warned_case()):
        assert len(c.summary()) > 60
        assert c.site_id in c.summary()


# -------------------------------------------------------------------------- rollup

def test_rollup_sums_both_counters_without_cancelling():
    day = rollup([_night_crew_case(), _over_warned_case()])
    assert day.unsafe_worker_hours_caught == 51.0
    assert day.productive_worker_hours_recovered == pytest.approx(59.5)
    assert day.decisions_changed == 2 and day.sites == 2


def test_rollup_headline_reads_as_a_sentence():
    headline = rollup([_night_crew_case(), _over_warned_case()]).headline()
    assert "changed the call at 2 of 2 sites" in headline
    assert "91 °F" in headline


def test_rollup_refuses_to_mix_thresholds():
    """Summing a site judged at 91 °F with one judged at 103 °F produces a number that
    means nothing."""
    a = _night_crew_case()
    b = compare_to_baseline(
        site_profile=flat("2025-07-15", 86.0), baseline_scalar_f=104.0,
        shift=Shift("PHX-ENCA", "05:30", "14:00", 7), date="2025-07-15",
        threshold_f=103.0,
    )
    with pytest.raises(MetricsError, match="mix thresholds"):
        rollup([a, b])


def test_rollup_refuses_to_mix_dates():
    a = _night_crew_case()
    b = compare_to_baseline(
        site_profile=flat("2025-07-16", 86.0), baseline_scalar_f=104.0,
        shift=Shift("PHX-ENCA", "05:30", "14:00", 7), date="2025-07-16",
        threshold_f=THRESHOLD,
    )
    with pytest.raises(MetricsError, match="multiple dates"):
        rollup([a, b])


def test_rollup_refuses_an_empty_roster():
    with pytest.raises(MetricsError):
        rollup([])


# --------------------------------------------------------------------- the baseline

def test_the_baseline_site_is_in_the_roster(site_rows):
    """The counterfactual is not modelled — it is one of the twelve sites we measure.
    KPHX, the official Phoenix observing station, is Sky Harbor."""
    assert BASELINE_SITE_ID in {r["site_id"] for r in site_rows}


def test_the_baseline_site_is_predicted_to_be_structurally_hot(site_rows):
    """Applying it uniformly should over-warn the cool sites. That is the point."""
    sky = next(r for r in site_rows if r["site_id"] == BASELINE_SITE_ID)
    assert sky["expected_profile"] == "high_peak_long_tail"


def test_the_baseline_is_applied_flat_across_the_shift():
    """A supervisor holding one daily number has no diurnal shape to apply. Assuming a
    shape would flatter the baseline with information it does not have."""
    c = compare_to_baseline(
        site_profile=flat("2025-07-15", 80.0), baseline_scalar_f=95.0,
        shift=DAY, date="2025-07-15", threshold_f=THRESHOLD,
    )
    assert c.baseline_unsafe_hours == DAY.length_hours     # the whole shift, or none

    c2 = compare_to_baseline(
        site_profile=flat("2025-07-15", 80.0), baseline_scalar_f=90.0,
        shift=DAY, date="2025-07-15", threshold_f=THRESHOLD,
    )
    assert c2.baseline_unsafe_hours == 0.0
