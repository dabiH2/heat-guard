"""
bands.py — heat index to NWS band and OSHA action. Pure data lookup, no network.

A leaf module: router.py and metrics.py both need it, neither should own it. It reads
config/thresholds.yaml and nothing else.

The contract that matters: `band_for` and `action_for` are TOTAL over finite floats. They
never return None. A band lookup that can silently return None in a heat-safety tool is
the same failure class as picking the wrong analysis layer — no error raised, a decision
quietly not made. If the tables ever stop covering the line, that is a configuration bug
and it raises here rather than propagating a None into a work/stop call.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

THRESHOLDS_PATH = Path(__file__).resolve().parents[2] / "config" / "thresholds.yaml"


class ThresholdConfigError(ValueError):
    """The band tables are not contiguous, not total, or not sorted."""


@dataclass(frozen=True)
class Band:
    """One half-open interval [min_f, max_f) and what it means."""
    id: str
    min_f: float
    max_f: float
    label: str
    action: str | None = None       # only osha_actions rows carry one

    def contains(self, heat_index_f: float) -> bool:
        return self.min_f <= heat_index_f < self.max_f


@dataclass(frozen=True)
class Thresholds:
    units: str
    metric: str
    nws_bands: tuple[Band, ...]
    osha_actions: tuple[Band, ...]
    unsafe_from_f: float
    sensitivity_thresholds_f: tuple[float, ...]
    disclaimer: str


def _parse_table(rows: list[dict], *, name: str, with_action: bool) -> tuple[Band, ...]:
    """Build a band table and prove it is sorted, contiguous and gap-free.

    Contiguity is checked structurally rather than by probing values, so the guarantee
    holds for every real number in range and not just the ones a test happened to try.
    """
    bands = tuple(
        Band(
            id=row["id"],
            min_f=float(row["min_f"]),
            max_f=float(row["max_f"]),
            label=" ".join(str(row["label"]).split()),
            action=row["action"] if with_action else None,
        )
        for row in rows
    )
    if not bands:
        raise ThresholdConfigError(f"{name}: table is empty")

    for band in bands:
        if band.min_f >= band.max_f:
            raise ThresholdConfigError(
                f"{name}: band {band.id!r} has min_f {band.min_f} >= max_f {band.max_f}"
            )
        if with_action and not band.action:
            raise ThresholdConfigError(f"{name}: band {band.id!r} has no action")

    for lower, upper in zip(bands, bands[1:]):
        if lower.max_f != upper.min_f:
            gap_or_overlap = "gap" if lower.max_f < upper.min_f else "overlap"
            raise ThresholdConfigError(
                f"{name}: {gap_or_overlap} between {lower.id!r} (ends {lower.max_f}) and "
                f"{upper.id!r} (starts {upper.min_f}). Bands must be contiguous — a "
                f"temperature that matches no band is a decision quietly not made."
            )
    return bands


@lru_cache(maxsize=1)
def load_thresholds(path: Path | None = None) -> Thresholds:
    """Load and validate config/thresholds.yaml. Cached; call `.cache_clear()` in tests."""
    raw = yaml.safe_load((path or THRESHOLDS_PATH).read_text(encoding="utf-8"))

    nws = _parse_table(raw["nws_bands"], name="nws_bands", with_action=False)
    osha = _parse_table(raw["osha_actions"], name="osha_actions", with_action=True)

    unsafe = float(raw["unsafe_from_f"])
    if not osha[0].min_f <= unsafe < osha[-1].max_f:
        raise ThresholdConfigError(
            f"unsafe_from_f {unsafe} falls outside the action table"
        )

    return Thresholds(
        units=raw["units"],
        metric=raw["metric"],
        nws_bands=nws,
        osha_actions=osha,
        unsafe_from_f=unsafe,
        sensitivity_thresholds_f=tuple(float(t) for t in raw["sensitivity_thresholds_f"]),
        disclaimer=" ".join(str(raw["disclaimer"]).split()),
    )


def _lookup(table: tuple[Band, ...], heat_index_f: float, *, name: str) -> Band:
    if not math.isfinite(heat_index_f):
        raise ValueError(f"{name}: heat index is {heat_index_f!r}, not a finite number")
    for band in table:
        if band.contains(heat_index_f):
            return band
    # Structurally unreachable while the table is contiguous and spans the input, but a
    # value beyond the outer edges lands here. Raise rather than return None.
    raise ThresholdConfigError(
        f"{name}: {heat_index_f} F falls outside "
        f"[{table[0].min_f}, {table[-1].max_f}). Widen the table."
    )


def band_for(heat_index_f: float) -> Band:
    """The NWS band. What a forecast on the radio would call this number."""
    return _lookup(load_thresholds().nws_bands, heat_index_f, name="nws_bands")


def action_for(heat_index_f: float) -> Band:
    """The OSHA action. What the supervisor should actually do."""
    return _lookup(load_thresholds().osha_actions, heat_index_f, name="osha_actions")


def is_unsafe(heat_index_f: float, threshold_f: float | None = None) -> bool:
    """At or above the exposure threshold.

    `threshold_f` is explicit on purpose. The headline metric changes materially between
    91 F and 103 F, so callers that care are made to say which one they mean; see the
    note on `unsafe_from_f` in config/thresholds.yaml.
    """
    if threshold_f is None:
        threshold_f = load_thresholds().unsafe_from_f
    return heat_index_f >= threshold_f
