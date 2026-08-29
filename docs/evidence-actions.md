# What the evidence changes, and the prompts to do it

*Compiled 29 August 2026. Derived from [`impact-evidence.md`](impact-evidence.md) and
[`practice-and-efficacy-evidence.md`](practice-and-efficacy-evidence.md). Those two documents
are the **only** permitted source of external figures for the changes below. Nothing here
introduces a number that is not already sourced in one of them.*

---

## 0. One decision you have to make first

`docs/video-script.md:79` and `docs/video/recording-plan.md:34` both require the **`$55/hour`
slider and the `$35,363` figure to be in frame**. If the pitch video is already recorded,
changing the slider default breaks the correspondence between the video and the live app.

| Option | Consequence |
|---|---|
| **A — change default to `$51.23`** (recommended) | App shows a sourced number. Video shows `$55` / `$35,363`, which now reads as *a judge moving the slider* — which is exactly what the slider is for. Add one line to `README.md` noting the video predates the sourcing. |
| **B — keep `$55` default, add the citation as a caption** | Video matches exactly. But the headline number stays uncited, which is the thing the evidence pack flagged. |
| C — re-record | Costs the most time for the least marginal gain. |

**Recommendation: A.** The prompts below assume A and include the README note. If you pick B,
drop step 2 of Prompt 2.

---

## 1. The change set

### A. Corrections — things that are currently wrong or unsupportable

| # | Change | Where | Why | Evidence |
|---|---|---|---|---|
| **A1** | Replace the thesis sentence *"Peak temperature is a poor predictor of harm. Duration above a threshold is the signal."* | `README.md:26`, `app.py:182–183`, `CLAUDE.md:35`, `src/heatguard/router.py:31` | **Not supportable as an empirical claim.** No occupational study has ever used hours-above-threshold as an exposure variable; the one worker study testing hourly WBGT was null on all three metrics; the largest US intensity-vs-duration test found intensity significant and duration not. | practice-and-efficacy §5 |
| **A2** | `$55/h` → **`$51.23/h`**; `≈$35,000` → **`≈$33,000`** | `README.md:62`, `app.py:598,604` | The `$55` is the only uncited number in the submission. BLS ECEC gives a real, current figure. | impact §3.4 |
| **A3** | Present the phantom-exposure cost as a **bounded range**, not a point | `README.md`, `app.py` "What that is worth" | A single figure assumes full stop-work, which the mandate objection defeats. A range with both ends sourced survives it. | impact §3.4, §9 |

**A1 replacement text** (claim about standards architecture, not epidemiology — airtight):

> Every occupational heat limit in force — NIOSH's RAL and REL, ACGIH's TLV, ISO 7933 — is
> defined as *time at a condition*, and NIOSH removed its peak-temperature ceiling limit in
> 2016. A daily peak cannot be compared against any of them. Hours above a threshold can.

**A3 range:**

| Bound | Basis | Value |
|---|---|---|
| Lower | 643 worker-hours × 12.5% mandated rest (15 min per 2 h at the high heat trigger) × $51.23 | **≈$4,120/day** |
| Upper | 643 worker-hours fully idle × $51.23 | **≈$32,941/day** |

### B. Additions — the Impact & Relevance section is 40% of the score and currently has no external evidence in it at all

| # | Add | Where | Why |
|---|---|---|---|
| **B1** | **154,320** outdoor workers in the Phoenix MSA; **1,364,770** across 16 US Sun Belt metros, built bottom-up from BLS OEWS May 2025 | `README.md`, `docs/submission-summary-v2.md` | This is the direct answer to the judge's "can this impact 100 people or thousands of millions?" It is currently absent. Bottom-up, per the mentor's warning about analyst reports. |
| **B2** | **48** US worker deaths from environmental heat in 2024, **40** outdoors; OSHA's own **14×** undercount factor | both | Establishes stakes with a primary federal source. |
| **B3** | The OSHA-NIOSH Heat Safety Tool, fed by NWS data, **identified 0%** of high or extreme risk conditions against on-site WBGT (682 matched hourly pairs); authors: *"not protective of workers… not recommended"* | `README.md` "Why anyone would pay" | **The strongest counterfactual fact in the pack.** It is the only published evaluation of the incumbent free tool, and it is devastating. |
| **B4** | **64%** of Maricopa County's 430 heat-related deaths in 2025 fell on days NWS HeatRisk was *not* Major or Extreme | both | Attacks the incumbent alert rather than describing the problem. **Must carry its [GEN POP] caveat every time.** |
| **B5** | **87%** of US contractors use weather forecasts, **42%** any direct jobsite measurement, **13%** WBGT (n=323, Oct–Dec 2025) | both | Documents current practice — supports "no incumbent solves it" with a number instead of an assertion. |
| **B6** | OSHA PEA footnote 81: assuming full-shift exceedance *"may overstate the number of breaks employers need to provide"* | `README.md` | The regulator makes the over-warning argument, in writing, against its own cost estimate. Best single citation for the commercial thesis. |

### C. Positioning — three reframes that cost nothing and change how the project reads

| # | Change | Why |
|---|---|---|
| **C1** | State plainly: **HeatGuard is an API, not a sensor.** No hardware, no calibration, no per-site instrument. | The Construction Industry Safety Coalition told OSHA on the record that WBGT equipment is *"not only expensive, but also complex… requires regular calibration"* and asked for simpler methods. This is a direct answer to the buyer's stated objection, and it is a property the build already has. |
| **C2** | Reframe the "zero customer discovery" limitation. **Keep the admission** — still say zero interviews — but add what was used instead: named employers' sworn testimony from OSHA docket OSHA-2021-0009 (12 hearing days, 16 Jun – 2 Jul 2025) plus two contractor surveys. | Converts the weakest line in the submission into a demonstration of research rigour, without claiming interviews that did not happen. |
| **C3** | Add to the roadmap: **trigger on deviation from local normal**, not an absolute band. | Kwest Group's EHS manager under oath: the operative signal is *"a significant change or deviation from what that normal heat index is in that location."* The CISC then formally proposed exactly that to OSHA, citing the urban heat island by name. A buyer-validated feature — list it as roadmap, **not as built**. |

### D. Honesty — say it before a judge does

| # | Add | Why |
|---|---|---|
| **D1** | **No tool of this class has ever been shown to reduce heat illness.** Zero wearable outcome studies worldwide; the only US RCT of a worker heat-decision app was null; the one strong positive (−21.9%, Italy 2024) came from a legally mandated work ban, not the platform. **And OSHA is in the same position** — its 95%/65% effectiveness figures are stated assumptions traced to marathon runners and military heat-stroke patients. | Pre-empts the killer question, and the OSHA parallel makes the gap defensible rather than disqualifying. |
| **D2** | Duration has **not** been shown to out-predict peak. Nobody has tested it. This is a gap, not a finding. | Follows from A1. Saying it first is worth more than hoping nobody checks. |
| **D3** | Counter-evidence, named: a contractor testified the free NWS forecast is *"all I need"*; contractor app use **fell 35% → 22%** between 2023 and 2025. | Two facts that cut against the product. Naming them is the same discipline already applied in "What we got wrong". |

### E. What does *not* change

The measured result (1.96 °F peak spread, 2.62 h duration spread, 643 phantom worker-hours,
92%), the unit trap, the six silent-failure modes, the deterministic router, the 349 tests, and
the failed site-selection hypothesis. **All of that is your own measurement and it stands.**
What changes is the framing around it and the sourcing beneath it.

---

## 2. The system: make citations testable

Ad-hoc footnotes drift. The project already treats correctness as something a test enforces —
apply the same discipline to evidence, so a claim can never silently detach from its source.

### `data/evidence/claims.json`

One registry. Every external factual claim gets an ID, and every place the claim appears
references that ID rather than restating the number.

```json
{
  "schema_version": 1,
  "compiled": "2026-08-29",
  "claims": [
    {
      "id": "HARM-01",
      "claim": "US worker deaths from exposure to environmental heat",
      "value": "48",
      "scope": "OCCUPATIONAL",
      "source_title": "BLS Census of Fatal Occupational Injuries, Table A-9",
      "source_url": "https://www.bls.gov/iif/fatal-injuries-tables/fatal-occupational-injuries-table-a-9-2024.htm",
      "data_year": "2024",
      "stale": false,
      "quote": null,
      "doc": "impact-evidence.md#1.1"
    }
  ]
}
```

**Field contract**

| Field | Rule |
|---|---|
| `id` | `^[A-Z]{3,5}-\d{2}$`, unique. Prefixes: `HARM`, `POP`, `REG`, `COST`, `REACH`, `CTR`, `PRAC`, `EFF` |
| `value` | The figure exactly as it should be rendered. Never recomputed downstream. |
| `scope` | One of `OCCUPATIONAL`, `GENERAL_POPULATION`, `AMBIENT`, `ECONOMY_WIDE`, `PRACTICE`, `REGULATORY`, `ACCURACY` |
| `source_url` | Required, `https://`, non-empty |
| `data_year` | Required. Year the **data** refers to, not the publication date |
| `stale` | Must be `true` if `data_year` < 2023 |
| `quote` | Verbatim text where the claim rests on wording rather than a number; else `null` |
| `doc` | Anchor back into the evidence pack, so the full caveat is one click away |

### `tests/test_evidence.py`

The test is the system. It must assert:

1. Every claim has non-empty `id`, `claim`, `value`, `scope`, `source_url`, `data_year`.
2. `id` matches the pattern and is unique.
3. `source_url` starts with `https://`.
4. `scope` is in the allowed set.
5. `stale` is `true` whenever `data_year` < 2023 — **a staleness lie fails the build**.
6. Every `[[EV:ID]]` marker appearing in `README.md`, `docs/submission-summary-v2.md`,
   `app.py` and `CLAUDE.md` resolves to a claim in the registry. **An unresolvable citation
   fails the build.**
7. Any claim with `scope == "GENERAL_POPULATION"` carries a non-empty `caveat` field —
   because that is the specific error this project must not make.

Runs offline, no network, no key — same standard as the rest of the suite.

### `scripts/render_evidence.py`

Expands `[[EV:ID]]` into a numbered markdown footnote and appends a **Sources** block; `--check`
mode verifies without writing, for CI. Keeps the prose readable while the link stays bound to
the claim.

---

## 3. The prompts

Run in order. Each assumes a fresh Claude Code session at the repo root. Each ends by running
`pytest`.

---

### Prompt 1 — Build the evidence registry and its test

```
Read docs/impact-evidence.md and docs/practice-and-efficacy-evidence.md in full. They are the
ONLY permitted source of external figures in this repo. Do not introduce any figure, quote or
URL that does not already appear in one of them.

Build a citation system so that no claim in this project can silently detach from its source.

1. Create data/evidence/claims.json with schema_version 1, a "compiled" date of 2026-08-29,
   and a "claims" array. Populate it from the two evidence docs with exactly these claims,
   using the IDs given. Take value, source_url and data_year verbatim from the docs — do not
   paraphrase a URL, do not round a value, do not infer a year.

   HARM-01  48 US worker deaths from environmental heat, 2024, BLS CFOI Table A-9  [OCCUPATIONAL]
   HARM-02  40 of those occurred outdoors (OIICS 5312), 2024, same source          [OCCUPATIONAL]
   HARM-03  OSHA's undercount factor for heat fatalities: 14, 89 FR 70698          [OCCUPATIONAL]
   POP-01   Maricopa County heat-related deaths 2025: 430, MCDPH April 2026 report [GENERAL_POPULATION]
   POP-02   64.0% of those 430 fell on days NWS HeatRisk was not Major/Extreme
            (275 of 430, MCDPH Table F)                                            [GENERAL_POPULATION]
   REG-01   OSHA Heat NEP CPL 03-00-024, effective 10 Apr 2026                     [REGULATORY]
   REG-02   Federal heat standard RIN 1218-AD39 still at Proposed Rule Stage as of
            Aug 2026; Supplemental NPRM projected 12/2026                          [REGULATORY]
   REG-03   Arizona has no enforceable state heat standard                         [REGULATORY]
   REG-04   OSHA PEA footnote 81 — assuming full-shift exceedance "may overstate
            the number of breaks employers need to provide". Include the verbatim
            quote in the "quote" field.                                            [REGULATORY]
   REG-05   Proposed high heat trigger: heat index 90 F, requiring a 15-minute paid
            rest break at least every two hours                                    [REGULATORY]
   COST-01  BLS ECEC construction industry total compensation $51.23/hour,
            March 2026                                                             [OCCUPATIONAL]
   REACH-01 154,320 outdoor workers, Phoenix-Mesa-Chandler MSA, BLS OEWS May 2025  [OCCUPATIONAL]
   REACH-02 1,364,770 outdoor workers across 16 US Sun Belt metros, same release   [OCCUPATIONAL]
   REACH-03 Phoenix MSA total employment 2,375,760 (154,320 = 6.50%)               [OCCUPATIONAL]
   CTR-01   OSHA-NIOSH Heat Safety Tool identified 0% of high or extreme risk
            conditions vs on-site WBGT; "not protective of workers... not
            recommended". Include the verbatim quote.                              [ACCURACY]
   CTR-02   NWS HeatRisk is one value per 24-hour period                           [ACCURACY]
   CTR-03   NDFD maximum temperature is defined over 7 AM - 7 PM LST               [ACCURACY]
   CTR-04   Worksite heat index ran ~7.3 C above the regional station heat index
            (40.6 C vs 33.3 C), Florida farmworkers                                [ACCURACY]
   CTR-05   Phoenix neighbourhood-to-neighbourhood air temperature differences of
            10 F or more on summer days. Include the verbatim quote.               [AMBIENT]
   PRAC-01  87% of US contractors use weather forecasts to assess heat risk,
            n=323, fielded Oct-Dec 2025                                            [PRACTICE]
   PRAC-02  42% use any direct jobsite measurement, same survey                    [PRACTICE]
   PRAC-03  13% use WBGT, same survey                                              [PRACTICE]
   PRAC-04  Mobile heat safety app use fell from 35% (2023) to 22% (2025)          [PRACTICE]
   PRAC-05  Kwest Group testimony: the operative signal is deviation from local
            normal, not an absolute threshold. Include the verbatim quote.         [PRACTICE]
   EFF-01   Zero wearable heat monitor studies measuring a health outcome
            (0 of 19 in the scoping review)                                        [ACCURACY]
   EFF-02   The only US RCT of a worker heat decision-support app was null on
            physiological strain (p = 0.11)                                        [ACCURACY]
   EFF-03   OSHA states it is ASSUMING 95% fatality / 65% HRI effectiveness.
            Include the verbatim quote.                                            [REGULATORY]

   Every claim needs: id, claim, value, scope, source_title, source_url, data_year, stale,
   quote (or null), doc (anchor back into the evidence doc, e.g. "impact-evidence.md#1.1").
   Set stale=true for any claim whose data_year is earlier than 2023.
   Every claim with scope GENERAL_POPULATION additionally needs a non-empty "caveat" field
   stating that it is not a worker figure and that Maricopa County does not record occupation.

2. Create tests/test_evidence.py asserting all seven rules in docs/evidence-actions.md section
   2 "tests/test_evidence.py". It must run fully offline with no network and no API key, in
   keeping with the rest of the suite. In particular it must fail the build if a [[EV:ID]]
   marker anywhere in README.md, docs/submission-summary-v2.md, app.py or CLAUDE.md does not
   resolve to a claim in the registry, and if any claim with data_year before 2023 is not
   flagged stale.

3. Create scripts/render_evidence.py which expands [[EV:ID]] markers in a given markdown file
   into numbered footnotes plus a "Sources" block, and supports --check to verify without
   writing. Follow the style of the existing scripts in scripts/.

4. Run pytest. All existing tests must still pass. Report the new total.

Do not modify README.md, app.py or any other file in this prompt. This prompt only builds the
system.
```

---

### Prompt 2 — Corrections

```
Read docs/impact-evidence.md, docs/practice-and-efficacy-evidence.md and docs/evidence-actions.md.
Apply change set A (Corrections). Use ONLY figures already present in those documents.

1. THESIS SENTENCE. The sentence "Peak temperature is a poor predictor of harm. Duration above
   a threshold is the signal." is not supportable as an empirical claim — see
   practice-and-efficacy-evidence.md section 5. It appears in four places:
     README.md around line 26
     app.py lines 182-183
     CLAUDE.md around line 35
     src/heatguard/router.py around line 31 (module docstring)
   Replace each with the standards-architecture claim, adapted to the surrounding register:

     "Every occupational heat limit in force — NIOSH's RAL and REL, ACGIH's TLV, ISO 7933 — is
     defined as time at a condition, and NIOSH removed its peak-temperature ceiling limit in
     2016. A daily peak cannot be compared against any of them. Hours above a threshold can."

   In README.md and app.py, cite it with [[EV:...]] markers for the NIOSH and ISO claims if you
   added registry entries for them; if you did not, add them to data/evidence/claims.json now,
   sourced from practice-and-efficacy-evidence.md section 5, before citing.

2. LOADED RATE. Change the default loaded labour rate from 55 to 51.23 (app.py around lines
   598 and 604) and update the derived figure from ~$35,000 to ~$33,000 in README.md around
   line 62.

   CRITICAL: do NOT global-replace the string "55". The repo contains "55:5 work/rest" in
   app.py and tests/test_app_runs.py, and "55 high-risk industries" in the evidence docs.
   Change only the slider default and the dollar figures. Verify by running pytest afterwards —
   tests/test_app_runs.py asserts on the literal string "55:5 work/rest".

   Label the rate in the UI with its source: BLS Employer Costs for Employee Compensation,
   construction industry, March 2026 — [[EV:COST-01]]. Keep it a slider; the point is that a
   buyer who disagrees can move it.

3. Add one line to README.md noting that the pitch video was recorded before this rate was
   sourced and therefore shows $55/h and $35,363.

4. BOUNDED RANGE. In README.md and in the app's "What that is worth" section, present the
   phantom-exposure cost as a range rather than a point:
     Lower bound ~$4,120/day  = 643 worker-hours x 12.5% mandated rest x $51.23
                                (15 min per 2 h at the proposed high heat trigger [[EV:REG-05]])
     Upper bound ~$32,941/day = 643 worker-hours x $51.23 [[EV:COST-01]]
   State that the truth lies between them and depends on what the employer actually does, and
   that no published figure exists for the cost of precautionary work stoppage
   (impact-evidence.md section 6 item 8).

5. Run pytest. All tests must pass, including the new tests/test_evidence.py.
```

---

### Prompt 3 — Additions, with every citation bound

```
Read docs/impact-evidence.md, docs/practice-and-efficacy-evidence.md and docs/evidence-actions.md.
Apply change sets B (Additions), C (Positioning) and D (Honesty) to README.md and
docs/submission-summary-v2.md.

Every external figure you add MUST carry a [[EV:ID]] marker resolving to data/evidence/claims.json.
Do not add any figure that is not in the registry. If a figure you need is missing, add it to the
registry from the evidence docs first — never inline an uncited number.

B — ADDITIONS
  - Add a short Impact section carrying: 48 US worker deaths from environmental heat in 2024,
    40 of them outdoors [[EV:HARM-01]] [[EV:HARM-02]], with OSHA's own 14x undercount factor
    [[EV:HARM-03]].
  - Add the bottom-up reach: 154,320 outdoor workers in the Phoenix MSA [[EV:REACH-01]] and
    1,364,770 across 16 US Sun Belt metros [[EV:REACH-02]], built from BLS OEWS May 2025. Show
    that Phoenix figure as 6.50% of metro employment [[EV:REACH-03]]. Link to
    impact-evidence.md section 4 for the step-by-step arithmetic. State plainly that this counts
    jobs, not customers, and that OEWS excludes the self-employed.
  - In "Why anyone would pay for this", add the strongest counterfactual fact: the OSHA-NIOSH
    Heat Safety Tool, fed by NWS data, identified 0% of high or extreme risk conditions when
    checked against on-site WBGT; the authors' verdict was "not protective of workers... not
    recommended" [[EV:CTR-01]]. This is the only published evaluation of the incumbent free tool.
  - Add: 64% of Maricopa County's 430 heat-related deaths in 2025 occurred on days NWS HeatRisk
    was not Major or Extreme [[EV:POP-01]] [[EV:POP-02]]. IMPORTANT: this is a general-population
    figure and Maricopa County does not record occupation. State that caveat inline, every time,
    and frame the claim as being about the ALERT's discriminating power, not about the
    decedents' jobs.
  - Add current practice: 87% of US contractors use weather forecasts, 42% do any direct
    jobsite measurement, 13% use WBGT [[EV:PRAC-01]] [[EV:PRAC-02]] [[EV:PRAC-03]].
  - Add OSHA PEA footnote 81 [[EV:REG-04]] as the citation for the over-warning argument, with
    its verbatim quote.

C — POSITIONING
  - State plainly that HeatGuard is an API, not a sensor: no hardware, no calibration, no
    per-site instrument. Note that the Construction Industry Safety Coalition told OSHA that
    WBGT equipment is "not only expensive, but also complex... requires regular calibration"
    and asked for simpler methods (practice-and-efficacy-evidence.md section 6).
  - Rewrite the "No customer discovery has happened" limitation. KEEP the admission that zero
    interviews were conducted — do not soften or obscure it. Add what was used instead: named
    employers' sworn testimony from OSHA docket OSHA-2021-0009 (12 hearing days, 16 Jun -
    2 Jul 2025) and two contractor surveys, documented in
    docs/practice-and-efficacy-evidence.md. Say that the roster is still constructed and that
    five conversations with Phoenix safety supervisors remain the next step.
  - Add to the roadmap, explicitly as NOT BUILT: trigger on deviation from local normal rather
    than an absolute band, citing Kwest Group's testimony [[EV:PRAC-05]] and the CISC's formal
    proposal of the same basis to OSHA.

D — HONESTY
  - Add to the limitations section: no tool of this class has ever been shown to reduce heat
    illness. Zero wearable outcome studies exist [[EV:EFF-01]]; the only US RCT of a worker
    heat decision-support app was null [[EV:EFF-02]]; the one strong positive result (Italy
    2024, -21.9% construction injuries) came from a legally mandated work ban, not the
    forecasting platform. Note that OSHA is in the same position — it states it is ASSUMING
    95% and 65% effectiveness [[EV:EFF-03]].
  - Add: duration has not been shown to out-predict peak temperature for worker harm. Nobody
    has tested it. State this as a gap, not a finding.
  - Add the counter-evidence: a contractor testified to OSHA that the free NWS forecast is
    "all I need to change work hours, days off, job assignments, production, and timelines",
    and contractor use of mobile heat safety apps fell from 35% to 22% between 2023 and 2025
    [[EV:PRAC-04]].

Keep the existing voice — plain, specific, no superlatives, limitations stated first-person.
Do not inflate. The submission summary has a 500-word budget; if you exceed it, cut adjectives
and keep numbers.

Run scripts/render_evidence.py --check on both files, then run pytest. All must pass.
```

---

### Prompt 4 — Surface the evidence in the running app

```
Read docs/evidence-actions.md and data/evidence/claims.json.

Make the evidence visible and checkable inside the running app, not just in the docs. The app
must still run fully offline from committed fixtures with no API key and no network.

1. Add a small helper in src/heatguard/ that loads data/evidence/claims.json once and exposes
   a lookup by claim ID returning value, source_title, source_url and data_year.

2. Anywhere app.py renders an EXTERNAL figure (as opposed to a figure measured from the
   fixtures), render a source link beside it using that helper. At minimum: the loaded rate
   [[EV:COST-01]], the OSHA band thresholds, and any harm or reach figure you added in
   Prompt 3. Measured figures from the fixtures must NOT get an external citation — they are
   this project's own measurement and should stay visibly distinct from cited external claims.

3. Add a "Sources" expander at the foot of the app listing every claim actually rendered in
   the current view, with its data year and link. Do not list the whole registry — only what
   the user is looking at.

4. Extend tests/test_app_surface.py so it fails if app.py renders a registry-backed figure
   without its source link, and if any claim ID referenced by app.py is missing from the
   registry.

5. Run pytest. All tests must pass offline, no credits, no key. Report the new total and
   confirm zero cache misses on the offline path.
```

---

## 4. Order and expected effect

| Prompt | Touches | Risk | Why it matters |
|---|---|---|---|
| 1 — registry | new files only | none | Foundation. Nothing else can cite safely without it. |
| 2 — corrections | README, app.py, CLAUDE.md, router.py | **medium** — router.py is core IP, and the "55" collision is a real trap | Removes the one unsupportable claim and the one uncited number. |
| 3 — additions | README, submission summary | low | Where the Impact & Relevance score actually moves. |
| 4 — app surface | app.py, new helper, tests | low | Makes the citation system visible to a judge clicking around. |

**If time is short, run 1 and 3.** Prompt 3 is where the 40% category is scored; Prompt 1 is
what makes its citations trustworthy. Prompt 2's thesis fix matters most against a judge who
knows the literature — which, given one of them is a VC principal who asked for statistics, is
a live risk rather than a theoretical one.

---

*Every figure referenced in this document traces to `impact-evidence.md` or
`practice-and-efficacy-evidence.md`. No new external claim is introduced here.*
