# Routing spec — the decision table

> Stub. T6 + T7 fill this in. It is the implementable form of §3 of `../../08-spec-p3.md`.

| # | Operator question | Trigger patterns | Layer | Endpoint | filter_type | Rationale template | Wrong answer if snapshot |
|---|---|---|---|---|---|---|---|
| 1 | Is it safe right now? | | snapshot | | 1 | | genuinely a snapshot question |
| 2 | When to start/stop today? | | intraday | | 2 | | one number, no schedule |
| 3 | Will we cross soon? | | forecast | | 1–2 within +12h | | historical average hides today |
| 4 | How long above the band? | | duration | | 2 or 3 | | max says how hot, never how long |
| 5 | Chronically dangerous? | | persistence | | 4 or 5 | | one bad day looks structural |
| 6 | Which site is worst? | | comparison | | held constant | | ranks by clock, not by heat |

## Refusals

| Trigger | Reason | Message |
|---|---|---|

## Baseline for "unsafe exposure-hours avoided"

> T7. Define the counterfactual, the formula, and its limitations here. Without a
> stated baseline the headline number invites "avoided versus what?" and the 40%
> Impact criterion wobbles.
