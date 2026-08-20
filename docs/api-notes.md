# API notes — verified behaviour

> Stub. T3 + T4. Record what the API *actually does*, not what the handbook says.
> Flag any divergence loudly.

## Plan & credits
- Plan:
- Credits remaining:
- Premium endpoints available:

## Observed async behaviour
- Typical latency, submit → terminal:
- Terminal status strings seen:
- Shape of `data.result`:

## Constraint failure modes

| Constraint | How it fails | Status code | Fails loudly or silently? | What the code catches |
|---|---|---|---|---|
| Non-US location | | | | |
| Date before 2021-01-01 | | | | |
| Forecast beyond +12h | | | | |
| AOI > ~130 km² | | | | |

## filter_type, verified
Same site, same date, `filter_type=1` vs `filter_type=3` — difference in shape and value:

## Divergences from the handbook
