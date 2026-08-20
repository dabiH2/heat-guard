"""
metrics.py — the headline number.

"Unsafe exposure-hours avoided" is the Impact criterion (40% of the score), so the
BASELINE has to be explicit. A number without a stated counterfactual invites the
question "avoided versus what?" and the answer has to already be in the README.

Proposed counterfactual (T7 — pressure-test before implementing):
    Current practice = one city-wide Phoenix forecast high, applied uniformly to
    every site. HeatGuard = the per-site hourly profile.

    avoided_hours(site, date) =
          hours above the unsafe band implied by the city-wide number
        - hours above the unsafe band in the per-site hourly profile

    Report the total across all sites, per week.
"""

from __future__ import annotations


def hours_above(profile: list[tuple[str, float]], threshold_f: float) -> float:
    """Count hours in an hourly profile at or above a threshold."""
    raise NotImplementedError("T7")


def exposure_hours_avoided(site_profile, citywide_profile, threshold_f: float) -> float:
    """The headline metric. See the module docstring for the counterfactual."""
    raise NotImplementedError("T7")
