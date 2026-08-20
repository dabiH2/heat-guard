"""
router.py — THE CORE IP.

Maps an operator's question to the correct temperature analysis layer, states why,
and refuses when the data cannot answer.

DESIGN RULE, NON-NEGOTIABLE: no LLM call belongs in this module. The agent parses
intent and narrates; the router decides. That makes layer selection auditable (this
is a safety tool), reproducible (every demo take must match), and testable with zero
credits and no network.

The failure this exists to prevent: FortyGuard's own engineering lead warned that
"picking the wrong analysis layer will give you a confident wrong answer" — no error
raised, just a plausible wrong number. Ask a DURATION question, answer it with
filter_type=1, and you get the opposite operational decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class QuestionType(str, Enum):
    """The six operator questions. See ../08-spec-p3.md §3."""
    SNAPSHOT = "snapshot"            # "Is it safe at site 3 right now?"
    INTRADAY = "intraday"            # "When should we start and stop today?"
    FORECAST = "forecast"            # "Will we cross the threshold in the next few hours?"
    DURATION = "duration"            # "How long were they above the danger band?"
    PERSISTENCE = "persistence"      # "Is site 3 chronically dangerous?"
    COMPARISON = "comparison"        # "Which of our 12 sites is worst?"


class RefusalReason(str, Enum):
    """Grounded in verified API constraints — none of these are theatre."""
    OUTSIDE_US = "outside_us"                    # coverage is US-only
    BEFORE_2021 = "before_2021"                  # data starts 2021-01-01
    BEYOND_FORECAST = "beyond_forecast_horizon"  # heatmap forecasts to now +12h only
    AOI_TOO_LARGE = "aoi_too_large"              # ~130 km2 cap
    GRANULARITY_TOO_FINE = "granularity_too_fine"  # finest is 60 m
    WRONG_LAYER_WOULD_MISLEAD = "wrong_layer_would_mislead"
    # ^ the differentiator: refusing a well-formed question because the only
    #   affordable layer would produce a confident wrong answer.


# Any of these in a question makes it a DURATION question. It must never be
# answered with filter_type=1. Extend during T6, keep it explicit and testable.
DURATION_MARKERS: tuple[str, ...] = (
    "how long", "chronically", "typically", "this summer", "worst",
    "sustained", "over the day", "all day", "hours above",
)


@dataclass
class LayerChoice:
    """What the router decided, and the sentence it says out loud."""
    question_type: QuestionType | None
    endpoint: str | None                  # "/v1/heatmap" | "/v1/env_params" | ...
    filter_type: int | None               # 1 hour | 2 hour-range | 3 day | 4 day-range | 5 month
    granularity: int | None               # 60 | 80 | 100 metres
    rationale: str                        # shown in the UI and spoken in the video
    refusal: RefusalReason | None = None
    refusal_message: str | None = None
    params: dict = field(default_factory=dict)

    @property
    def refused(self) -> bool:
        return self.refusal is not None


def classify(question: str) -> QuestionType:
    """Pure string classification. T6: implement, and unit-test every branch."""
    raise NotImplementedError("T6")


def check_refusals(*, lat: float, lon: float, date: str, **kw) -> tuple[RefusalReason, str] | None:
    """
    Validate against the verified constraints BEFORE spending a credit.

    T4 supplies the observed failure modes; this turns them into pre-flight checks
    so the agent refuses cleanly instead of surfacing a raw API error.
    """
    raise NotImplementedError("T6")


def route(question: str, *, lat: float, lon: float, date: str, **kw) -> LayerChoice:
    """
    The entry point. classify -> check refusals -> select layer + params -> explain.

    Must be deterministic: same input, same LayerChoice, every time.
    """
    raise NotImplementedError("T6")
