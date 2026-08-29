"""
make_decisions_sample.py — generate a REAL sample of the audit trail.

Run:  python scripts/make_decisions_sample.py

WHY THIS EXISTS
README and the written summary both call `data/decisions.jsonl` a product in its own
right — the evidence that a documented, consistent process was followed, which is what
protects a supervisor in an OSHA citation. But the runtime log is gitignored, as an
append-only operational log should be, so a fresh clone had nothing to look at. The
mechanism was real and the artefact was missing, which is precisely the drift this
project spends its whole pitch complaining about.

So this writes `data/decisions.sample.jsonl` by asking the real agent real questions
against the committed 2025-07-15 fixtures. Nothing here is hand-authored: every record
is whatever `agent.answer()` actually produced, including the rationale text and the
refusal messages.

OFFLINE, ALWAYS. HEATGUARD_OFFLINE is forced on before the agent is imported, so this
cannot spend a FortyGuard credit even if a key is present in the environment.

DETERMINISM. The file is overwritten, not appended, and the scenarios below are fixed,
so re-running produces identical records except for the `at` timestamp — which is a real
generation time and is deliberately not faked. The test that pins this file does not
assert on it.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Force offline BEFORE importing the agent — tools.py reads this at call time, but
# setting it here makes the guarantee obvious and unconditional.
os.environ["HEATGUARD_OFFLINE"] = "1"
os.environ.pop("HEATGUARD_ONLINE", None)

from heatguard import agent  # noqa: E402

OUT = ROOT / "data" / "decisions.sample.jsonl"
DATE = "2025-07-15"

# Each scenario is chosen to exercise a path that makes the log worth keeping. A sample
# showing only happy-path answers would prove nothing a screenshot could not.
SCENARIOS: list[tuple[str, dict, str]] = [
    (
        "Is it safe at the ramp right now?",
        {"site_id": "PHX-SKY", "date": DATE},
        "SNAPSHOT — the one question a single hour genuinely answers.",
    ),
    (
        "How many hours were they above the danger threshold?",
        {"site_id": "PHX-27TH", "date": DATE, "threshold_f": 103.0},
        "DURATION -> analytic_type=exceedance. The layer the default would have missed.",
    ),
    (
        "Tell me about the worst at this site",
        {"site_id": "PHX-27TH", "date": DATE, "threshold_f": 103.0},
        "ESCALATION — 'worst' is an authoritative duration marker that matches no "
        "comparison phrasing, so the classifier said SNAPSHOT and the marker rule "
        "overrode it. `escalated_from` records that it did.",
    ),
    (
        "Which of our sites is worst today?",
        {"site_id": "PHX-27TH", "date": DATE, "threshold_f": 103.0},
        "COMPARISON, site 1 of 3 — ranking by duration, at one held-constant granularity.",
    ),
    (
        "Which of our sites is worst today?",
        {"site_id": "PHX-L202", "date": DATE, "threshold_f": 103.0},
        "COMPARISON, site 2 of 3.",
    ),
    (
        "Which of our sites is worst today?",
        {"site_id": "PHX-ENCA", "date": DATE, "threshold_f": 103.0},
        "COMPARISON, site 3 of 3.",
    ),
    (
        "Is this site chronically dangerous?",
        {"site_id": "PHX-CHASE", "date": DATE},
        "REFUSAL, WRONG_LAYER_WOULD_MISLEAD — the differentiator. The API would have "
        "answered this happily; one day cannot support a claim about many.",
    ),
    (
        "How long were they above the band at 2pm?",
        {"site_id": "PHX-CHASE", "date": DATE, "threshold_f": 103.0},
        "REFUSAL, WRONG_LAYER_WOULD_MISLEAD — duration cannot be measured in an instant.",
    ),
    (
        "Is it safe right now?",
        {"site_id": "PHX-SKY", "date": "2021-07-15"},
        "REFUSAL, BEFORE_2021 — outside measured coverage. This date returns Completed "
        "with zero tiles and is billed 4,220 credits, so refusing is a cost control.",
    ),
]


def main() -> int:
    # Point the agent's log at the sample file and start it empty, so the run is a
    # regeneration rather than an accumulation.
    agent.DECISIONS_LOG = OUT
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("", encoding="utf-8")

    print(f"offline           : {os.environ.get('HEATGUARD_OFFLINE')}")
    print(f"writing           : {OUT.relative_to(ROOT)}")
    print(f"scenarios         : {len(SCENARIOS)}\n")

    answered = refused = 0
    for question, kwargs, why in SCENARIOS:
        # narrate=False keeps this free of any Anthropic dependency: the sample must be
        # reproducible by a judge with no keys of any kind.
        out = agent.answer(question, narrate=False, **kwargs)
        choice = out["choice"]

        if choice.refused:
            refused += 1
            verdict = f"REFUSED  {choice.refusal.value}"
        else:
            answered += 1
            verdict = (f"{choice.question_type.value} -> "
                       f"{choice.analytic_type.value if choice.analytic_type else '-'}"
                       f"  ft={choice.filter_type}")
        escalated = (f"  (escalated from {choice.escalated_from.value})"
                     if choice.escalated_from else "")
        print(f"  {kwargs['site_id']:<11} {verdict}{escalated}")
        print(f"    {question}")
        print(f"    {why}\n")

    records = [json.loads(line)
               for line in OUT.read_text(encoding="utf-8").splitlines() if line.strip()]

    print(f"{len(records)} records — {answered} answered, {refused} refused")
    print(f"refusal reasons : "
          f"{sorted({r['refusal'] for r in records if r['refusal']})}")
    print(f"layers used     : "
          f"{sorted({r['analytic_type'] for r in records if r['analytic_type']})}")
    print(f"escalations     : "
          f"{sum(1 for r in records if r['escalated_from'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
