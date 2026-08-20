"""
metrics.py — the headline number, and the counterfactual it is measured against.

Impact is 40% of the score and it is the one weight verified verbatim on camera. A
number without a stated baseline invites "avoided versus what?", so the counterfactual
has to be in the README before the number is.

===============================================================================
WHY "UNSAFE EXPOSURE-HOURS AVOIDED" IS NOT THE METRIC (T7)
===============================================================================
The proposal in TASKS.md was:

    avoided_hours = hours above the band implied by the city-wide number
                  - hours above the band in the per-site profile

Four problems, one of them fatal.

1. A forecast HIGH is a scalar. It does not imply a number of hours. To turn it into
   hours you must assume a diurnal shape — which is precisely the thing you are claiming
   the supervisor does not have. The baseline would have to invent what the product
   exists to supply.

2. FATAL: the subtraction is signed, and the sign flips on the best case. For the night
   crew at Chase Tower, the city-wide DAYTIME high implies roughly zero relevant hours
   across a 21:00-05:30 shift, while the real profile shows several. The formula returns
   a NEGATIVE number for the single strongest case in the project. The tool did not avoid
   those hours, it REVEALED them — and revealing them is the entire point.

3. "Avoided" claims credit for a behavioural change that has not happened. Hours are only
   avoided if a supervisor acts on the information.

4. It sums two opposite-signed wins that then cancel:

       over-warning corrected   city-wide says danger, site is actually cooler
                                -> work proceeds that would have been stopped
                                -> PRODUCTIVE HOURS RECOVERED

       under-warning corrected  city-wide says fine, site is hotter or hotter for longer
                                -> work stops that would have continued
                                -> UNSAFE HOURS CAUGHT

   Both are wins. Under the proposed formula they have opposite signs, so across twelve
   sites the tool can be right twelve times and net to approximately zero.

===============================================================================
WHAT IS MEASURED INSTEAD
===============================================================================
Three numbers, none of which cancel against another:

    unsafe_worker_hours_caught      crew-hours scheduled into hours the site was above
                                    threshold and the city-wide number said it was not.
                                    The safety number. Owned by the safety officer.

    productive_worker_hours_recovered
                                    crew-hours the city-wide number would have shut down
                                    at sites that were actually below threshold.
                                    The cost number. Owned by operations.

    decisions_changed               how many (site, shift) pairs got a different
                                    operational call. The honest denominator: "HeatGuard
                                    changed the call at 5 of 12 sites today."

All three are counted in WORKER-hours, not clock-hours, because a 22-person crew at the
27th Avenue campus and a 4-person crew on Roosevelt Row are not the same exposure. And
all three are counted ONLY INSIDE THE CREW'S SHIFT WINDOW — hours nobody was standing in
are not exposure, which is the same correction that put night crews in the roster.

===============================================================================
THE BASELINE IS NOT A PROXY. IT IS THE ACTUAL NUMBER.
===============================================================================
The official temperature for Phoenix is observed at station KPHX — Phoenix Sky Harbor
International Airport. When a supervisor hears "Phoenix hit 112 today", that number came
from Sky Harbor.

Sky Harbor is PHX-SKY in our roster: square kilometres of unshaded concrete, predicted
`high_peak_long_tail`. So the counterfactual is not modelled or assumed. It is one of the
twelve sites we already measure, and it is structurally one of the hottest. Applying it
uniformly over-warns the irrigated sites and, for a night crew, describes a shift that
had already ended.

The baseline applies that ONE scalar flat across every hour, which is a deliberately
crude model — and a faithful one. A supervisor with a single daily high has no shape to
apply; the call is binary and covers the whole shift. Assuming anything richer would
flatter the baseline with information it does not have.

VERIFY IN T4: that PHX-SKY is the station the public Phoenix figure comes from is
well-established but is not something this repo has confirmed against a source. It is
load-bearing for the whole metric, so confirm it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .bands import action_for, load_thresholds

#: The roster site whose reading stands in for "the city-wide number". See module docs.
BASELINE_SITE_ID = "PHX-SKY"

#: An (ISO-8601 local timestamp, value) pair. `env_params` returns local-time timestamps
#: with the offset attached, so shift windows need no timezone conversion.
Reading = tuple[str, float]


class MetricsError(ValueError):
    """The inputs cannot support the number being asked for."""


# --------------------------------------------------------------------- shift windows

@dataclass(frozen=True)
class Shift:
    """A crew's working window on a given date, and how many people are in it."""
    site_id: str
    start: str          # "21:00"
    end: str            # "05:30"
    crew_size: int

    @property
    def crosses_midnight(self) -> bool:
        return self.end <= self.start

    def window(self, date: str) -> tuple[datetime, datetime]:
        """Absolute [start, end) for this shift on `date`, naive local time.

        Returned as explicit datetimes rather than hour-of-day so a night shift is
        unambiguous. Selecting "hours 21-23 and 00-05" out of a two-day profile would
        silently double-count; an explicit window cannot.
        """
        start = datetime.fromisoformat(f"{date}T{self.start}:00")
        end = datetime.fromisoformat(f"{date}T{self.end}:00")
        if self.crosses_midnight:
            end += timedelta(days=1)
        return start, end

    @property
    def length_hours(self) -> float:
        start, end = self.window("2000-01-01")
        return (end - start).total_seconds() / 3600.0


def shift_from_row(row: dict) -> Shift:
    """Build a Shift from a config/sites.csv row."""
    return Shift(
        site_id=row["site_id"],
        start=row["shift_start"],
        end=row["shift_end"],
        crew_size=int(row["crew_size"]),
    )


# ------------------------------------------------------------------------ counting

def _parse(reading: Reading) -> tuple[datetime, float]:
    stamp, value = reading
    # Tolerate a trailing offset ("2025-07-15T14:00:00-07:00") by dropping it: the
    # profile and the shift are both already in the site's local time.
    parsed = datetime.fromisoformat(stamp)
    return parsed.replace(tzinfo=None), float(value)


def hours_above(profile: list[Reading], threshold_f: float) -> float:
    """Count whole hourly readings at or above a threshold.

    At the threshold counts as above — consistent with `bands.is_unsafe`, and the
    conservative direction for a safety tool.

    Each reading is taken to represent the hour block that STARTS at its timestamp.
    Use `unsafe_hours_in_shift` when a shift boundary can fall mid-hour; this function
    counts whole readings and would over-count in that case.
    """
    return float(sum(1 for _, value in map(_parse, profile) if value >= threshold_f))


def _overlap_hours(block_start: datetime, window_start: datetime,
                   window_end: datetime) -> float:
    """How much of the hour block starting at `block_start` lies inside the window.

    This is the fix for a real off-by-one. A 05:00-13:30 shift is 8.5 hours long but
    contains NINE hourly readings — 05:00 through 13:00 — because the 13:00 reading
    covers 13:00-14:00 and only half of it is in the shift. Counting readings as hours
    inflates every day shift on the roster by about 6%, silently and in the direction
    that makes the product look better.
    """
    block_end = block_start + timedelta(hours=1)
    overlap = min(block_end, window_end) - max(block_start, window_start)
    return max(0.0, overlap.total_seconds() / 3600.0)


def shift_readings(profile: list[Reading], shift: Shift,
                   date: str) -> list[tuple[Reading, float]]:
    """Readings whose hour block overlaps the shift, each with its overlap in hours.

    A night shift spanning midnight needs a profile covering both calendar days. If it
    does not, that is raised rather than quietly returning a short count — an
    undercounted night shift is the exact error this project exists to prevent, and it
    would land on the lead demo site.
    """
    start, end = shift.window(date)
    weighted = [
        (reading, weight)
        for reading in profile
        if (weight := _overlap_hours(_parse(reading)[0], start, end)) > 0
    ]

    covered = sum(weight for _, weight in weighted)
    if covered + 1e-9 < shift.length_hours:
        raise MetricsError(
            f"{shift.site_id}: shift {shift.start}-{shift.end} on {date} is "
            f"{shift.length_hours:g} h but the profile only covers {covered:g} h of it. "
            f"{'A shift crossing midnight needs both calendar days. ' if shift.crosses_midnight else ''}"
            f"Refusing to report a short count."
        )
    return weighted


def readings_in_shift(profile: list[Reading], shift: Shift, date: str) -> list[Reading]:
    """The readings overlapping the shift, unweighted. For peaks and inspection."""
    return [reading for reading, _ in shift_readings(profile, shift, date)]


def unsafe_hours_in_shift(profile: list[Reading], shift: Shift, date: str,
                          threshold_f: float) -> float:
    """Hours at or above threshold inside the crew's shift window.

    Boundary readings contribute only the fraction of their hour that the crew was
    actually on site, so this can never exceed `shift.length_hours`.
    """
    return sum(
        weight
        for reading, weight in shift_readings(profile, shift, date)
        if _parse(reading)[1] >= threshold_f
    )


def worker_hours(hours: float, crew_size: int) -> float:
    """Clock-hours to worker-hours. A 22-person crew is not a 4-person crew."""
    return hours * crew_size


# -------------------------------------------------------------------- the comparison

@dataclass(frozen=True)
class SiteComparison:
    """What the city-wide number said, what the site actually did, and the difference."""
    site_id: str
    date: str
    threshold_f: float
    crew_size: int
    shift_hours: float

    baseline_scalar_f: float
    baseline_unsafe_hours: float
    site_unsafe_hours: float

    baseline_action: str
    site_action: str

    @property
    def decision_changed(self) -> bool:
        return self.baseline_action != self.site_action

    @property
    def unsafe_hours_caught(self) -> float:
        """Hours the city-wide number missed. Never negative — see the module docstring."""
        return max(0.0, self.site_unsafe_hours - self.baseline_unsafe_hours)

    @property
    def productive_hours_recovered(self) -> float:
        """Hours the city-wide number would have shut down unnecessarily."""
        return max(0.0, self.baseline_unsafe_hours - self.site_unsafe_hours)

    @property
    def unsafe_worker_hours_caught(self) -> float:
        return worker_hours(self.unsafe_hours_caught, self.crew_size)

    @property
    def productive_worker_hours_recovered(self) -> float:
        return worker_hours(self.productive_hours_recovered, self.crew_size)

    def summary(self) -> str:
        """One line, for the UI and for data/decisions.jsonl."""
        if not self.decision_changed:
            return (f"{self.site_id}: agrees with the city-wide call "
                    f"({self.site_action}).")
        if self.unsafe_hours_caught > 0:
            return (f"{self.site_id}: city-wide said {self.baseline_action}, site is "
                    f"{self.site_action} — {self.unsafe_hours_caught:.0f} h above "
                    f"{self.threshold_f:.0f} °F inside the shift that the city-wide "
                    f"number did not show "
                    f"({self.unsafe_worker_hours_caught:.0f} worker-hours).")
        return (f"{self.site_id}: city-wide said {self.baseline_action}, site is "
                f"{self.site_action} — {self.productive_hours_recovered:.0f} h of "
                f"working time the city-wide number would have shut down "
                f"({self.productive_worker_hours_recovered:.0f} worker-hours).")


def compare_to_baseline(
    *,
    site_profile: list[Reading],
    baseline_scalar_f: float,
    shift: Shift,
    date: str,
    threshold_f: float | None = None,
) -> SiteComparison:
    """Compare one site's shift against the city-wide scalar applied flat.

    `baseline_scalar_f` is the single daily figure a supervisor would actually hear —
    the KPHX / Sky Harbor observation. Applied flat across every hour of the shift,
    because a supervisor holding one number has no shape to apply.
    """
    threshold_f = threshold_f if threshold_f is not None else load_thresholds().unsafe_from_f

    site_unsafe = unsafe_hours_in_shift(site_profile, shift, date, threshold_f)
    baseline_unsafe = shift.length_hours if baseline_scalar_f >= threshold_f else 0.0

    site_peak = max(v for _, v in map(_parse, readings_in_shift(site_profile, shift, date)))

    return SiteComparison(
        site_id=shift.site_id,
        date=date,
        threshold_f=threshold_f,
        crew_size=shift.crew_size,
        shift_hours=shift.length_hours,
        baseline_scalar_f=baseline_scalar_f,
        baseline_unsafe_hours=baseline_unsafe,
        site_unsafe_hours=site_unsafe,
        baseline_action=action_for(baseline_scalar_f).action,
        site_action=action_for(site_peak).action,
    )


# ------------------------------------------------------------------------- rollup

@dataclass(frozen=True)
class DayRollup:
    """The headline numbers for one day across the roster."""
    date: str
    threshold_f: float
    comparisons: tuple[SiteComparison, ...]

    @property
    def unsafe_worker_hours_caught(self) -> float:
        return sum(c.unsafe_worker_hours_caught for c in self.comparisons)

    @property
    def productive_worker_hours_recovered(self) -> float:
        return sum(c.productive_worker_hours_recovered for c in self.comparisons)

    @property
    def decisions_changed(self) -> int:
        return sum(1 for c in self.comparisons if c.decision_changed)

    @property
    def sites(self) -> int:
        return len(self.comparisons)

    def headline(self) -> str:
        return (
            f"{self.date}, threshold {self.threshold_f:.0f} °F heat index: HeatGuard "
            f"changed the call at {self.decisions_changed} of {self.sites} sites — "
            f"{self.unsafe_worker_hours_caught:.0f} unsafe worker-hours the city-wide "
            f"figure did not show, and "
            f"{self.productive_worker_hours_recovered:.0f} worker-hours of working time "
            f"it would have shut down unnecessarily."
        )


def rollup(comparisons: list[SiteComparison]) -> DayRollup:
    if not comparisons:
        raise MetricsError("no comparisons to roll up")
    dates = {c.date for c in comparisons}
    thresholds = {c.threshold_f for c in comparisons}
    if len(dates) != 1:
        raise MetricsError(f"comparisons span multiple dates: {sorted(dates)}")
    if len(thresholds) != 1:
        raise MetricsError(
            f"comparisons mix thresholds {sorted(thresholds)} — the headline number is "
            f"meaningless unless every site was judged against the same one."
        )
    return DayRollup(
        date=dates.pop(),
        threshold_f=thresholds.pop(),
        comparisons=tuple(comparisons),
    )


def sensitivity(
    build: "callable[[float], list[SiteComparison]]",
) -> dict[float, DayRollup]:
    """Run the rollup at every threshold in `sensitivity_thresholds_f` (91 and 103 °F).

    T2 requires this. Neither threshold is neutral — at 91 °F a Phoenix summer day shift
    saturates and night shifts differentiate sharply; at 103 °F the reverse. A result
    that only holds at one threshold is a result about the threshold, so both get
    reported and the reader decides.
    """
    return {
        t: rollup(build(t)) for t in load_thresholds().sensitivity_thresholds_f
    }


# --------------------------------------------------------------- the naive metric

def exposure_hours_avoided(site_profile: list[Reading], baseline_scalar_f: float,
                           shift: Shift, date: str,
                           threshold_f: float | None = None) -> float:
    """The signed net from the original T7 proposal. KEPT, BUT DO NOT HEADLINE IT.

    Returns baseline_unsafe - site_unsafe, so it is NEGATIVE whenever the site is worse
    than the city-wide figure suggested — which is the case the project exists to
    surface, and is the strongest case in the demo. It also cancels two opposite-signed
    wins against each other.

    Retained so the decomposition can be shown to reduce to it, and so the demo can show
    the naive number going negative on the Chase Tower night crew. That contrast is worth
    more than the number.
    """
    c = compare_to_baseline(
        site_profile=site_profile, baseline_scalar_f=baseline_scalar_f,
        shift=shift, date=date, threshold_f=threshold_f,
    )
    return c.baseline_unsafe_hours - c.site_unsafe_hours
