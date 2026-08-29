"""
Structural checks on `app.py` — the live surface.

The engine has 349 tests. The surface had none, and it shipped a bug that made two of
four tabs render empty on a cold visit, including the one carrying the strongest evidence
for the 35% judging criterion. Nothing caught it because no test imports app.py and the
bug is invisible to `ast.parse`.

These are cheap structural assertions, not a UI test. They catch the specific class of
mistake that is silent, survives a syntax check, and only shows up to someone actually
clicking the deployed app.
"""

import ast
import json
import re
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app.py"
SOURCE = APP.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


def test_app_parses():
    """`pytest` never imports app.py, so a syntax error in it passes every other test.

    That happened: a scripted edit put literal newlines inside two f-strings, leaving the
    file unparseable while the suite stayed green, because nothing loaded it.
    """
    assert TREE is not None


def test_no_st_stop_anywhere():
    """THE REGRESSION.

    `st.stop()` halts the ENTIRE script run, not the current tab or column. Streamlit
    re-executes this file top to bottom on every interaction, so a stop inside an early
    tab silently prevents every tab defined LATER in the file from being populated at all.

    That shipped. "The trap" and "How it decides" were empty on a cold visit and only
    appeared after the user pressed a button in a different tab, which skipped the stop.

    Use `return` from a helper function instead. If you genuinely need to halt the whole
    app — you almost certainly do not — delete this test deliberately and say why.
    """
    calls = [
        node for node in ast.walk(TREE)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "stop"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "st"
    ]
    assert not calls, (
        f"st.stop() called at line(s) {[c.lineno for c in calls]}. It halts the whole "
        f"script, so every tab defined after it renders empty. Use `return` instead."
    )


def test_every_tab_variable_is_actually_used():
    """A tab created but never opened with `with` is an empty tab in the UI."""
    created = re.search(r"^(\w[\w,\s]*?)\s*=\s*st\.tabs\(", SOURCE, re.M)
    assert created, "no st.tabs() call found"
    names = [n.strip() for n in created.group(1).split(",") if n.strip()]
    assert len(names) >= 2
    for name in names:
        assert re.search(rf"^with {re.escape(name)}:", SOURCE, re.M), (
            f"{name} is created by st.tabs() but never opened with `with {name}:` — "
            f"it would render as an empty tab"
        )


def test_the_deployment_is_offline_by_default():
    """A deployed app that can reach the API can be made to spend 4,220 credits a click.
    Going online must require an explicit opt-in, never be the default."""
    assert 'os.environ["HEATGUARD_OFFLINE"] = "1"' in SOURCE
    assert 'os.environ.get("HEATGUARD_ONLINE"' in SOURCE


def test_no_api_key_is_read_or_printed_in_the_surface():
    """The key belongs to tools.py and must never surface in client code or a video frame."""
    for forbidden in ("FORTYGUARD_API_KEY", "api-key", "api_key"):
        assert forbidden not in SOURCE, f"{forbidden!r} appears in app.py"


MARKDOWN_CALLS = ("markdown", "info", "success", "warning", "error", "caption")


def _markdown_literals() -> list[tuple[int, str]]:
    """Each markdown-family call's string content, joined across its concatenated parts.

    Joining matters: the bug that motivated this test had its two `$` on different source
    lines of one implicitly-concatenated f-string, so a line-by-line scan skipped it
    entirely and the test never ran.
    """
    found: list[tuple[int, str]] = []
    for node in ast.walk(TREE):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in MARKDOWN_CALLS):
            continue
        for arg in node.args:
            parts: list[str] = []
            for piece in ast.walk(arg):
                if isinstance(piece, ast.Constant) and isinstance(piece.value, str):
                    parts.append(piece.value)
            if parts:
                found.append((node.lineno, "".join(parts)))
    return found


def test_paired_dollar_signs_in_markdown_are_escaped():
    """Streamlit reads `$…$` as LaTeX math and silently eats the currency symbol AND the
    bold markers around it — "**$35,363**" rendered as "**35,363**" until this was found.

    Two or more unescaped `$` in one markdown string opens a math span.
    """
    offenders = [
        (lineno, text) for lineno, text in _markdown_literals()
        if len(re.findall(r"(?<!\\)\$", text)) >= 2
    ]
    assert not offenders, "\n".join(
        f"  line {lineno}: unescaped $…$ pair renders as LaTeX math — {text[:80]!r}"
        for lineno, text in offenders
    )


def test_the_dollar_check_has_something_to_check():
    """Guards the guard. If app.py stops mentioning money the test above silently becomes
    vacuous, and a future reader would trust a check that cannot fail."""
    with_dollars = [t for _, t in _markdown_literals() if "$" in t]
    assert with_dollars, "no markdown call mentions $ — the escaping test is now vacuous"


# ------------------------------------------------- the plan artefact and the one rule

def _app_module():
    import os
    os.environ["HEATGUARD_OFFLINE"] = "1"
    import app
    return app


def test_the_plan_names_what_was_not_measured():
    """The section most tools omit. A plan that lists only what it knows, and is silent
    about its gaps, is more dangerous than no plan — the reader assumes the gaps are
    clear. These four strings are the integrity surface of the artefact."""
    app = _app_module()
    day = app.shift_exposure("2025-07-15")
    analysis = app.day_analysis("2025-07-15")
    arows = {r["site_id"]: r for r in analysis["rows"]}

    sheet = []
    for r in day["rows"]:
        call_id, call_text = app._call_for(r, arows.get(r["site_id"]))
        window, _, _ = app._measured_window(r["shift"], r["night"])
        sheet.append({
            "call_id": call_id, "Crew": r["name"], "Crew size": r["crew"],
            "Shift": r["shift"], "Call today": call_text,
            ">=103 °F in shift": f"{r['in_shift_hours']:.1f} h",
            ">=103 °F all day": f"{r['whole_day_hours']:.1f} h",
            "Window measured": window,
        })
    plan = app.plan_text("2025-07-15", sheet, 103.0)

    for claim in ("NOT AN ALL-CLEAR", "UNMEASURED, NOT CLEAR",
                  "COUNTS, NOT TIMES", "HEAT INDEX, NOT WBGT",
                  "4,220 credits", "analytic_type=exceedance"):
        assert claim in plan, f"{claim!r} missing from the shift plan"
    assert "Received by" in plan, "no acknowledgement line — this goes to a foreman"


def test_the_call_never_says_fifty_ten_without_in_shift_hours():
    """THE INVARIANT THE WHOLE SHEET RESTS ON.

    The tighter rung must follow hours measured INSIDE the crew's own shift. Keying it on
    the day's peak instead returns 50:10 for ten of twelve sites — the sheet degenerates
    into one call printed twelve times, which is precisely the failure this project
    exists to argue against.
    """
    app = _app_module()
    day = app.shift_exposure("2025-07-15")
    analysis = app.day_analysis("2025-07-15")
    arows = {r["site_id"]: r for r in analysis["rows"]}

    calls = {}
    for r in day["rows"]:
        call_id, _ = app._call_for(r, arows.get(r["site_id"]))
        calls[r["site_id"]] = call_id
        if call_id == "rest_breaks_50_10":
            assert r["in_shift_hours"] > 0, (
                f"{r['site_id']} got the tighter rung with zero in-shift hours")
        if r["in_shift_hours"] > 0:
            assert call_id == "rest_breaks_50_10", (
                f"{r['site_id']} had in-shift exposure and did not get the tighter rung")

    assert len(set(calls.values())) > 1, (
        "every crew got the same call — the sheet is not separating anything, which is "
        "what a peak-driven rule would produce")


def test_the_bound_is_withheld_where_it_cannot_be_computed():
    """The 91 °F floor needs a whole-day total for the SAME 24 hours the shift spans. A
    night shift spans two dates and the cache holds 16 July only as the tail of these very
    shifts, so there is no whole-day figure. Printing one would mean stretching a 15 July
    measurement across a day nobody measured."""
    app = _app_module()
    for night in (True, False):
        result = app._bound_91(8.5, 20.0, night)
        if night:
            assert result is None, "a bound was invented for a shift crossing midnight"
        else:
            assert result == pytest.approx(4.5)


def test_the_measured_window_reports_the_floored_edge():
    """`hhmm()` floors BOTH shift edges despite a docstring claiming it rounds outward, so
    a shift ending at 13:30 was measured to 13:00 and the last half hour — the hottest
    part of a Phoenix day shift — was never looked at. The UI must say so."""
    app = _app_module()
    label, measured, unmeasured = app._measured_window("05:00-13:30", False)
    assert measured == 8.0 and unmeasured == pytest.approx(0.5)
    assert "unmeasured" in label

    label, measured, unmeasured = app._measured_window("21:00-05:30", True)
    assert measured == 7.0, "night shift is two calls: 21:00-23:00 and 00:00-05:00"
    assert unmeasured == pytest.approx(1.5), "the 23:00-00:00 hour is in neither call"


def test_the_app_does_not_quote_a_stale_test_count():
    """The tab that argues the build is sound cannot be wrong about the build.

    Three numbers on it had drifted — 336, 349, and "4 question shapes" against 6 offered.
    Quoting a count fifty short on the tab making the 35%-criterion case is the cheapest
    possible way to lose it.

    The claim is a FLOOR ("over 400"), not an exact count, and deliberately so. An exact
    count is wrong the moment anyone adds a test — this very test broke on the run that
    introduced it, because collecting it changed the number it was checking. A floor
    degrades gracefully: it stays true as tests are added and fails loudly only if the
    suite actually shrinks past it, which is the thing worth knowing.
    """
    import re
    import subprocess
    import sys

    out = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        capture_output=True, text=True, cwd=str(APP.parent),
    ).stdout
    match = re.search(r"(\d+) tests? collected", out)
    assert match, f"could not read the collected count from pytest: {out[-300:]}"
    collected = int(match.group(1))

    floors = [int(n) for n in re.findall(r"[Oo]ver (\d{3}) (?:offline )?tests", SOURCE)]
    assert floors, "app.py no longer states a test-count floor at all"
    for floor in floors:
        assert collected >= floor, (
            f"app.py claims over {floor} tests; pytest collects {collected}")
        assert collected < floor * 1.5, (
            f"app.py claims over {floor} but there are {collected} — the claim has gone "
            f"stale in the other direction and is now underselling the suite")


def test_no_exact_test_count_is_quoted():
    """Exact counts rot on the next commit. Guards the floor above from being 'helpfully'
    replaced by a precise number that will be wrong within the hour."""
    import re
    exact = re.findall(r"(?<![Oo]ver )\b(\d{3}) (?:offline )?tests\b", SOURCE)
    assert not exact, (
        f"app.py quotes exact test counts {exact}; state a floor instead")


# ======================================================================= the evidence
#
# Two kinds of number are rendered on this page and the whole point is that they stay
# distinguishable:
#
#   MEASURED — the peak spread, the phantom worker-hours, the 92%, the 17-hour unit trap,
#   the 4,220 credits, the site and crew counts. This project measured them from its own
#   committed fixtures. They carry NO external citation, because there is none.
#
#   EXTERNAL — the loaded labour rate, the standards architecture, the mandated rest
#   fraction, the status of the proposed rule. Every one belongs to somebody else's
#   document, resolves through `data/evidence/claims.json`, and MUST reach the page with
#   its source link attached.
#
# The failure these tests exist for is silent in exactly the way this repo's other bugs
# were: a claim id that resolves to nothing, or a registry-backed figure printed with no
# way to check it. Both render as ordinary confident prose. Neither raises. `ast.parse`
# sees nothing wrong, and a judge reading the page cannot tell.

REGISTRY = APP.parent / "data" / "evidence" / "claims.json"

#: A claim id inside a STRING literal — how app.py names a claim. Ids in comments are
#: deliberately not matched: a comment renders nothing, so it cites nothing.
QUOTED_CLAIM_ID = re.compile(r"[\"']([A-Z]{3,5}-\d{2})[\"']")

#: The marker form used in README.md / CLAUDE.md / the submission summary. app.py uses
#: real links instead, but if a marker ever lands here it is a citation too and is checked.
EV_MARKER = re.compile(r"\[\[EV:([A-Z]{3,5}-\d{2})\]\]")

#: Every `evidence` entry point that emits the claim's source URL. An id may only reach
#: the page through one of these — `CitationLog` deliberately offers no way to record a
#: claim without linking it.
LINKING_CALLS = ("cite", "link", "source_link")


def _registry_claims() -> list[dict]:
    assert REGISTRY.exists(), f"{REGISTRY} is missing — nothing app.py cites can resolve"
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["claims"]


def _registry_by_id() -> dict[str, dict]:
    return {claim["id"]: claim for claim in _registry_claims()}


def _ids_named_in_app() -> set[str]:
    """Every claim id app.py mentions in a string literal or an [[EV:]] marker."""
    return set(QUOTED_CLAIM_ID.findall(SOURCE)) | set(EV_MARKER.findall(SOURCE))


def _ids_rendered_with_a_link() -> set[str]:
    """Ids passed to a call that emits the source URL alongside the figure."""
    found: set[str] = set()
    for node in ast.walk(TREE):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in LINKING_CALLS):
            continue
        if (node.args and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)):
            found.add(node.args[0].value)
    return found


def _first_number(text: str) -> float:
    """The leading number in a registry `value`, e.g. "$51.23" or "12.5% (15 min…)"."""
    match = re.search(r"-?\d+(?:,\d{3})*(?:\.\d+)?", text)
    assert match, f"no number to read out of {text!r}"
    return float(match.group(0).replace(",", ""))


def _call_keywords(attr: str, *, label_fragment: str) -> dict[str, ast.expr]:
    """The keyword arguments of the `st.<attr>` call whose first argument names it."""
    for node in ast.walk(TREE):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == attr):
            continue
        first = node.args[0] if node.args else None
        if isinstance(first, ast.Constant) and label_fragment in str(first.value):
            return {kw.arg: kw.value for kw in node.keywords if kw.arg}
    raise AssertionError(
        f"no st.{attr}() whose first argument contains {label_fragment!r}")


def _constant(node):
    return node.value if isinstance(node, ast.Constant) else None


# --------------------------------------------------------------- the checks can fail

def test_the_citation_checks_have_something_to_check():
    """Guards the two tests below. If app.py stops naming claim ids, or stops routing them
    through a linking call, both would pass by having nothing to inspect — and a future
    reader would trust a check that cannot fail. Same shape as the dollar-escape guard."""
    assert _ids_named_in_app(), (
        "app.py names no claim ids at all — the citation tests are now vacuous")
    assert _ids_rendered_with_a_link(), (
        "no claim id reaches app.py through cite()/link()/source_link() — the "
        "source-link test is now vacuous")


# ---------------------------------------------------- an id that resolves to nothing

def test_every_claim_id_named_in_app_resolves_to_the_registry():
    """An unresolvable citation reads exactly like a real one.

    `evidence.claim()` raises on an unknown id at RENDER time, which is the right
    behaviour and not sufficient: a typo in a branch a judge never clicks still ships. This
    reads the ids statically, so a stale id fails the build rather than the page.
    """
    unresolved = sorted(_ids_named_in_app() - set(_registry_by_id()))
    assert not unresolved, (
        f"app.py cites {unresolved}, which the registry does not hold. Add the claim to "
        f"data/evidence/claims.json from the evidence pack, or fix the id — never leave a "
        f"citation that resolves to nothing on the page.")


def test_every_registry_backed_figure_carries_its_source_link():
    """THE POINT OF THE WHOLE EXERCISE.

    A figure taken from somebody else's document and printed with no way to reach that
    document is worse than an uncited figure, because it is then indistinguishable from
    one this project measured. So an id may only enter app.py through a call that emits
    the source URL with it; naming a claim any other way — a bare string, a value pulled
    out and rendered alone — fails here.
    """
    unlinked = sorted(_ids_named_in_app() - _ids_rendered_with_a_link())
    assert not unlinked, (
        f"app.py names {unlinked} without rendering the source link. Route the figure "
        f"through evidence.cite() or evidence.link(); each of {LINKING_CALLS} emits the "
        f"claim's source_url and data_year beside the value.")


def test_an_unknown_claim_id_raises_rather_than_rendering_nothing():
    """The registry contract the surface rests on.

    `bands.band_for` raises rather than returning None for the same reason: a lookup that
    can quietly return nothing in a tool arguing from evidence is a citation quietly not
    made. Every real id must also render its URL and its data year.
    """
    from heatguard import evidence

    with pytest.raises(evidence.UnknownClaimError):
        evidence.claim("ZZZZ-99")

    for claim_id, row in _registry_by_id().items():
        rendered = evidence.cite(claim_id)
        assert row["source_url"] in rendered, (
            f"evidence.cite({claim_id!r}) rendered no source url")
        assert row["data_year"] in rendered, (
            f"evidence.cite({claim_id!r}) rendered no data year")


# ---------------------------------------------------- the loaded rate, and the 55 trap

def test_the_loaded_rate_defaults_to_the_sourced_figure_not_an_invented_one():
    """`$55/h` was the only uncited number in the submission. It is now the BLS figure for
    the construction industry, and app.py has to keep agreeing with the registry about it —
    a default that drifts from COST-01 is the exact detachment the registry exists to stop.
    """
    app = _app_module()
    expected = _first_number(_registry_by_id()["COST-01"]["value"])
    assert app.DEFAULT_LOADED_RATE_USD_PER_HOUR == pytest.approx(expected), (
        f"the slider defaults to {app.DEFAULT_LOADED_RATE_USD_PER_HOUR}, COST-01 says "
        f"{expected}")

    kwargs = _call_keywords("slider", label_fragment="Loaded labour rate")
    default = kwargs.get("value")
    assert isinstance(default, ast.Name), (
        "the slider's default must be the named constant, so the UI and this test cannot "
        "disagree about what the rate is")
    assert default.id == "DEFAULT_LOADED_RATE_USD_PER_HOUR"
    assert _constant(kwargs.get("min_value")) == 25.0, "the slider lost its lower bound"
    assert _constant(kwargs.get("max_value")) == 100.0, "the slider lost its upper bound"
    assert isinstance(_constant(kwargs.get("step")), float), (
        "51.23 is not reachable on an integer step — the slider has to be a float slider, "
        "or the sourced default silently snaps to something nobody chose")


def test_the_mandated_rest_fraction_matches_the_registry():
    """The floor of the cost range is 12.5% of the phantom hours. That percentage is
    COST-02 — 15 minutes per 120 — and hard-coding it is only safe while it agrees."""
    app = _app_module()
    expected = _first_number(_registry_by_id()["COST-02"]["value"]) / 100.0
    assert app.MANDATED_REST_FRACTION == pytest.approx(expected), (
        f"app.py uses {app.MANDATED_REST_FRACTION}, COST-02 says {expected}")


def test_the_work_rest_ratio_strings_survived_the_rate_change():
    """THE `55` TRAP.

    The loaded rate moved from 55 to 51.23. app.py also carries `rest_breaks_55_5` and the
    crew-facing string `55:5 work/rest`, which are OSHA work/rest ratios with nothing to do
    with money — and `tests/test_app_runs.py` asserts on that literal. A global replace of
    "55" would silently have rewritten a call a foreman reads at 05:00.
    """
    for survivor in ('"rest_breaks_55_5"', '"55:5 work/rest"', "50:10 work/rest"):
        assert survivor in SOURCE, (
            f"{survivor} is gone from app.py — a work/rest ratio was rewritten as though "
            f"it were a dollar rate")

    kwargs = _call_keywords("slider", label_fragment="Loaded labour rate")
    assert _constant(kwargs.get("value")) != 55, "the slider is back on the invented rate"


# --------------------------------------------------------------------- the cost range

def test_the_cost_is_a_range_with_both_ends_and_the_proposed_caveat():
    """A point estimate assumes the employer stops work outright — the aggressive reading,
    and the one the mandate objection defeats. Both ends belong on the page, and the
    provision the floor rests on has to be marked proposed rather than in force."""
    app = _app_module()
    assert "cost_floor" in SOURCE and "cost_ceiling" in SOURCE, (
        "the cost is back to a single point figure")
    assert "MANDATED_REST_FRACTION" in SOURCE, (
        "the floor no longer applies the mandated rest fraction")
    assert app.MANDATED_REST_FRACTION < 1.0, "the floor is not a fraction of the hours"

    named = _ids_named_in_app()
    for claim_id in ("COST-01", "COST-02", "REG-02", "REG-05"):
        assert claim_id in named, (
            f"{claim_id} is not cited on the page, and the cost range rests on it")
    assert "PROPOSED" in SOURCE, (
        "the page no longer says the break provision is proposed and not in force")


# ------------------------------------------------ measured is not the same as cited

def test_the_measured_and_cited_distinction_is_stated_and_held():
    """The distinction IS the argument. A page where a measured result and a borrowed
    figure look identical overclaims by omission, and this project's own measurements are
    strong enough not to need anybody else's authority attached to them."""
    assert "Two kinds of number" in SOURCE, (
        "the legend explaining linked-vs-unlinked figures is gone")
    assert SOURCE.count("Measured here") >= 2, (
        "the measured figures are no longer marked as measured — they now read as uncited "
        "external claims rather than as this project's own work")


def test_the_sources_expander_lists_only_what_the_page_rendered():
    """Thirty claims under a page that cited seven is a bibliography, not a citation: a
    reader cannot tell which of them any figure on screen actually rests on."""
    assert "SOURCES.markdown()" in SOURCE, "the Sources block no longer renders the log"
    assert "expander" in SOURCE and "Sources" in SOURCE, "the Sources expander is gone"
    for dump_the_lot in ("claim_ids()", "load_registry(", "all_claims("):
        assert dump_the_lot not in SOURCE, (
            f"app.py appears to enumerate the whole registry via {dump_the_lot!r} — the "
            f"expander must list only the claims this pass actually rendered")


# ------------------------------------------------------------- the thesis correction

def test_the_unsupportable_thesis_sentence_is_gone():
    """"Peak temperature is a poor predictor of harm. Duration above a threshold is the
    signal." was an empirical claim nobody has tested: no occupational study has used
    hours-above-threshold as an exposure variable, and the largest intensity-vs-duration
    test found intensity significant and duration not.

    What replaces it is a claim about the ARCHITECTURE of the standards, which is airtight
    because the standards say it in their own text — and which is cited to them.

    Scanned over RENDERED strings rather than the whole file: the comment above the new
    sentence quotes the old one so the next reader knows why it went, and a check that
    could not tell a warning from a relapse would force that comment to be deleted.
    """
    rendered = " ".join(text for _, text in _markdown_literals())
    for unsupportable in ("poor predictor of harm", "Duration above a threshold is the"):
        assert unsupportable not in rendered, (
            f"{unsupportable!r} is rendered by app.py again; it is not supportable as an "
            f"empirical claim (practice-and-efficacy-evidence.md section 5)")

    assert "time at a condition" in rendered, (
        "the standards-architecture claim is missing from the page")
    named = _ids_named_in_app()
    for claim_id in ("NIOSH-01", "NIOSH-02", "ISO-01"):
        assert claim_id in named, (
            f"the thesis no longer cites {claim_id} — it is the sentence that most needs "
            f"its source, because it is the one a judge who knows the literature checks")


# ===================================================================== the Ask tab
#
# THE BUG THIS SECTION EXISTS FOR: every question rendered the same panel. Peak on the
# left, an optional hours tile beside it, the same heading, the same chips. A judge could
# ask a snapshot question and a duration question about the same crew on the same day and
# see the same screen twice — which is exactly the silent-wrong-answer failure the router
# exists to prevent, reproduced one layer up, in the interface.
#
# The answer shaping now lives in `src/heatguard/ask.py` and is pure, so the claim "these
# are three different answers" is checked here in milliseconds instead of by a human
# clicking a deployed app. Everything below reads committed files only.

DEMO_DATE = "2025-07-15"

QUESTIONS = {
    "snapshot": "How hot is it at this crew's site right now?",
    "duration": "How many hours were they above the threshold today?",
    "comparison": "Which of these crews is worst today?",
}

REFUSING_QUESTIONS = {
    "intraday": "When should we start and stop today?",
    "forecast": "Will we cross the threshold in the next few hours?",
    "persistence": "Is this site chronically dangerous?",
}


def _fixtures(app, threshold_f: float = 103.0):
    """Roster plus the two committed roll-ups the Ask tab ranks from."""
    return {
        "roster": app.sites(),
        "analysis": app.day_analysis(DEMO_DATE),
        "shift_data": app.shift_exposure(DEMO_DATE),
        "threshold_f": threshold_f,
    }


def _shape(app, question: str, crew_ids, threshold_f: float = 103.0):
    """Route a question and shape the answer, exactly as the tab does — no rendering."""
    from heatguard import ask
    from heatguard.router import route

    site = app.sites()[crew_ids[0]]
    choice = route(question, lat=float(site["lat"]), lon=float(site["lon"]),
                   date=DEMO_DATE, threshold_f=threshold_f)
    facts = ask.crew_facts(crew_ids, **_fixtures(app, threshold_f))
    return choice, ask.build(choice.question_type, facts, threshold_f=threshold_f)


def test_the_three_answerable_shapes_are_visibly_different():
    """THE REGRESSION THE REBUILD EXISTS FOR.

    Same crew, same date, same threshold — three questions, and the answers must not be
    interchangeable. A snapshot is one number, a duration is two, a comparison is an
    ordering. If any two of these headlines collide, the tab is back to answering every
    question with the same panel and the whole routing argument is invisible to a reader.
    """
    app = _app_module()
    headlines, kinds, metric_counts = {}, {}, {}
    for name, question in QUESTIONS.items():
        choice, answer = _shape(app, question, ["PHX-SKY"])
        assert not choice.refused, f"{name!r} refused; it is one of the answerable three"
        assert choice.question_type.value == name, (
            f"{question!r} routed to {choice.question_type} rather than {name}")
        headlines[name] = answer.headline
        kinds[name] = answer.kind
        metric_counts[name] = len(answer.metrics)

    assert len(set(headlines.values())) == 3, (
        f"two questions produced the same headline for the same crew: {headlines}")
    assert kinds["snapshot"] == kinds["duration"] == "card"
    assert kinds["comparison"] == "ranking", (
        "a comparison must rank even with one crew selected — printing a card in reply "
        "to 'which crew is worst' quietly answers a different question")
    assert metric_counts["snapshot"] == 1 and metric_counts["duration"] == 2, (
        f"a snapshot has no duration to show and a duration has two figures; got "
        f"{metric_counts}")
    for name, headline in headlines.items():
        assert len(headline) <= 110, f"{name} headline is not a headline: {headline!r}"


def test_no_answer_carries_more_than_two_metrics():
    """Two tiles maximum. A third dilutes whichever one actually decides, and the old
    panel's third tile said the NWS band twice — once as a number, once as a chip."""
    app = _app_module()
    for question in QUESTIONS.values():
        for crews in (["PHX-SKY"], ["PHX-27TH", "PHX-CHASE", "PHX-UNHL"]):
            _, answer = _shape(app, question, crews)
            assert len(answer.metrics) <= 2, (
                f"{question!r} over {len(crews)} crew(s) rendered "
                f"{len(answer.metrics)} metrics")


def test_more_than_one_crew_always_ranks():
    """The complaint that started the rebuild: being allowed one site while being offered
    a comparison question is not sound. Two or more crews is a ranking, whatever the
    layer, and the ranking column is the number the ROUTED layer measures."""
    app = _app_module()
    crews = ["PHX-27TH", "PHX-CHASE", "PHX-UNHL"]
    _, snapshot = _shape(app, QUESTIONS["snapshot"], crews)
    _, duration = _shape(app, QUESTIONS["duration"], crews)

    assert snapshot.kind == duration.kind == "ranking"
    assert len(snapshot.rows) == len(duration.rows) == 3
    assert "Peak" in snapshot.rank_column, (
        f"a snapshot question must rank by what the snapshot layer measures; ranked by "
        f"{snapshot.rank_column!r}")
    assert "Hours" in duration.rank_column, (
        f"a duration question must rank by hours; ranked by {duration.rank_column!r}")
    assert snapshot.rank_column in snapshot.rows[0], "the ranking column is not a column"
    assert snapshot.headline != duration.headline, (
        "ranking by peak and ranking by duration produced the same headline")


def test_the_ranking_is_worst_first_and_a_coverage_gap_is_never_safest():
    """PHX-DVT returned zero tiles, Completed, billed 4,220 credits. Sorting it as 0.0
    hours would rank the one crew nobody measured as the safest on the roster — the worst
    available wrong answer for a heat-safety tool, and the exact conversion of silence
    into safety the morning sheet refuses to make."""
    from heatguard import ask
    app = _app_module()
    crews = ["PHX-DVT", "PHX-UNHL", "PHX-27TH"]
    _, answer = _shape(app, QUESTIONS["comparison"], crews)

    order = [row["Crew"] for row in answer.rows]
    values = [row[answer.rank_column] for row in answer.rows]
    assert "no reading" in values[-1], (
        f"the crew with no tiles is not last: {list(zip(order, values))}")

    facts = ask.crew_facts(crews, **_fixtures(app))
    ranked = ask.rank(facts, None)
    hours = [f.day_hours for f in ranked if f.day_hours is not None]
    assert hours == sorted(hours, reverse=True), f"not worst-first: {hours}"


def test_a_coverage_gap_never_wears_a_severity_chip():
    """PHX-DVT returned zero tiles and was billed for it. The call chip is coloured from
    the OSHA rung, and `no_reading` is not a rung — falling back to the lowest band would
    print "OSHA below caution risk" beside the one crew nobody measured, which is silence
    rendered as safety."""
    from heatguard import ask
    app = _app_module()
    _, answer = _shape(app, QUESTIONS["duration"], ["PHX-DVT"])

    assert answer.kind == "no_reading"
    assert answer.call_text == "NO READING"
    assert answer.action_id is None, (
        f"a coverage gap was given the {answer.action_id!r} severity colour")
    assert answer.band_id is None, "a coverage gap was given an NWS band"
    assert ask.rung_band_id("no_reading") is None
    assert ask.rung_band_id("rest_breaks_50_10") == "high"


def test_the_answer_names_the_morning_sheet_when_it_disagrees():
    """DECISION 2, ON SCREEN. The layer the question routes to decides the answer, and
    where that gives a DIFFERENT rung from the morning call sheet for the same crew on the
    same day, one line has to say why.

    Sky Harbor is the case that proves it: peak 104.3 °F puts it on OSHA's high rung, and
    it spent zero hours above 103 °F inside its own 05:00-13:30 shift, so the sheet says
    55:5. Both are right about different questions, and an interface that shows one
    without naming the other is hiding the only interesting thing it knows.
    """
    app = _app_module()
    _, snapshot = _shape(app, QUESTIONS["snapshot"], ["PHX-SKY"])
    assert snapshot.call_text == "50:10 work/rest", (
        f"the peak no longer drives the snapshot call: {snapshot.call_text!r}")
    assert "55:5 work/rest" in snapshot.note, (
        f"the snapshot answer does not name the sheet's different call: {snapshot.note!r}")
    assert "different layer" in snapshot.note.lower(), (
        "the divergence is stated without saying WHY the two differ")

    _, duration = _shape(app, QUESTIONS["duration"], ["PHX-SKY"])
    assert duration.call_text == "55:5 work/rest", (
        "the duration answer must follow hours inside the shift, like the sheet")
    assert duration.note, "the duration answer says nothing about the sheet at all"


def test_the_ask_tab_and_the_morning_sheet_apply_the_same_rule():
    """`heatguard.ask` carries its own copy of the shift rule so the two tabs are free to
    diverge as products. This is what stops that freedom becoming a silent contradiction:
    on the demo day, at the threshold the sheet was measured at, every crew gets the same
    rung from both. The claim "the same rule, and the same answer" is checked, not
    assumed."""
    from heatguard import ask
    app = _app_module()
    facts = ask.crew_facts(list(app.sites()), **_fixtures(app))
    shift_rows = {r["site_id"]: r for r in app.shift_exposure(DEMO_DATE)["rows"]}
    analysis_rows = {r["site_id"]: r for r in app.day_analysis(DEMO_DATE)["rows"]}

    for fact in facts:
        sheet_id, _ = app._call_for(shift_rows[fact.site_id],
                                    analysis_rows.get(fact.site_id))
        assert fact.call_id == sheet_id, (
            f"{fact.site_id}: the Ask tab says {fact.call_id!r} and the morning sheet "
            f"says {sheet_id!r} for the same crew on the same day")


def test_the_rollup_the_ranking_uses_agrees_with_the_live_call():
    """A ranking over twelve crews is built from `data/fixtures/t8`, not from twenty-four
    calls. That is only honest while the roll-up says what the calls say, and nothing
    else in the build checks it — the roll-up was generated by a script that could be
    edited, and a drifted figure would render as ordinary confident prose.

    Every site, both thresholds, offline, no credits.
    """
    import os
    os.environ["HEATGUARD_OFFLINE"] = "1"
    from heatguard import ask
    from heatguard.agent import answer

    app = _app_module()
    for threshold_f in (91.0, 103.0):
        facts = {f.site_id: f
                 for f in ask.crew_facts(list(app.sites()), **_fixtures(app, threshold_f))}
        for site_id, fact in facts.items():
            out = answer(QUESTIONS["duration"], site_id=site_id, date=DEMO_DATE,
                         threshold_f=threshold_f, narrate=False)
            peak = (out["result"].get("peak") or {}).get("max_f")
            hours = out["result"].get("hours")
            if peak is None:
                assert not fact.has_data, (
                    f"{site_id} returns no tiles but the roll-up shows data for it")
                continue
            assert fact.peak_f == pytest.approx(peak, abs=0.01), (
                f"{site_id}: roll-up peak {fact.peak_f} vs live {peak}")
            assert fact.day_hours == pytest.approx(hours, abs=0.01), (
                f"{site_id} at {threshold_f:.0f} °F: roll-up {fact.day_hours} h vs "
                f"live {hours} h")


def test_the_in_shift_figure_is_a_bound_when_it_is_not_a_measurement():
    """`shift_exposure_*.json` was measured at ONE threshold. At any other, hours inside
    the shift are a pigeonhole floor, and every rendering of a floor has to say "at
    least" — a bound printed as a measurement is the same overclaim as a measured figure
    wearing somebody else's citation."""
    from heatguard import ask
    app = _app_module()

    measured = {f.site_id: f for f in ask.crew_facts(
        ["PHX-SKY", "PHX-CHASE"], **_fixtures(app, 103.0))}
    assert measured["PHX-SKY"].in_shift_hours is not None
    assert measured["PHX-SKY"].in_shift_text.endswith("h")
    assert "at least" not in measured["PHX-SKY"].in_shift_text

    bounded = {f.site_id: f for f in ask.crew_facts(
        ["PHX-SKY", "PHX-CHASE"], **_fixtures(app, 91.0))}
    assert bounded["PHX-SKY"].in_shift_hours is None
    assert "at least" in bounded["PHX-SKY"].in_shift_text, (
        f"a pigeonhole floor is being printed as a measurement: "
        f"{bounded['PHX-SKY'].in_shift_text!r}")
    assert bounded["PHX-CHASE"].in_shift_floor is None, (
        "a bound was invented for a shift that crosses midnight")
    assert "not derivable" in bounded["PHX-CHASE"].in_shift_text


def test_the_floor_and_the_call_rule_match_the_morning_tab_helpers():
    """`ask` re-implements two things app.py already had, so the two tabs can move
    independently. Both must still agree arithmetically, or the same crew gets two
    different bounds depending on which tab is open."""
    from heatguard import ask
    app = _app_module()
    for night in (True, False):
        assert ask.shift_floor_hours(8.5, 20.0, night) == app._bound_91(8.5, 20.0, night)


def test_a_refused_question_is_never_given_an_answer_shape():
    """`persistence`, `forecast` and `intraday` refuse in router.py. The tab must not
    invent a shape for any of them — the honest set is exactly three, and a fourth would
    mean fabricating an answer the fixtures cannot support."""
    from heatguard import ask
    from heatguard.router import QuestionType, route

    app = _app_module()
    site = app.sites()["PHX-SKY"]
    for name, question in REFUSING_QUESTIONS.items():
        choice = route(question, lat=float(site["lat"]), lon=float(site["lon"]),
                       date=DEMO_DATE, threshold_f=103.0)
        assert choice.refused, f"{name!r} no longer refuses; the tab has no shape for it"

    assert set(ask.ANSWERABLE) == {QuestionType.SNAPSHOT, QuestionType.DURATION,
                                   QuestionType.COMPARISON}


def test_the_mechanism_carries_the_whole_audit_trail_for_one_answer():
    """Adjacent to the answer, structured, and complete. The parameters, the reason, the
    counterfactual and the unit conversion used to be four separate regions spread down
    the page; a reader checking one number should not have to hunt for how it was made."""
    from heatguard import ask
    from heatguard.agent import answer

    app = _app_module()
    out = answer(QUESTIONS["duration"], site_id="PHX-SKY", date=DEMO_DATE,
                 threshold_f=103.0, narrate=False)
    rows = dict(ask.mechanism_rows(out["choice"], out["result"], ranked_over=3))

    for field in ("Question read as", "Endpoint", "filter_type", "analytic_type",
                  "granularity", "Why this layer", "What a snapshot would have said",
                  "Unit conversion", "Calls made", "Logged to"):
        assert field in rows, f"{field!r} missing from the mechanism"
    assert "°C" in rows["Unit conversion"] and "heat index" in rows["Unit conversion"]

    snap = answer(QUESTIONS["snapshot"], site_id="PHX-SKY", date=DEMO_DATE,
                  threshold_f=103.0, narrate=False)
    snap_rows = dict(ask.mechanism_rows(snap["choice"], snap["result"]))
    assert "Unit conversion" not in snap_rows, (
        "a snapshot sends no threshold, so a conversion row would describe a step that "
        "never happened")


def test_the_mechanism_of_a_refusal_says_no_call_was_made():
    """A refusal has a mechanism too, and the fact that matters most about it is that
    nothing was spent."""
    from heatguard import ask
    from heatguard.router import route

    app = _app_module()
    site = app.sites()["PHX-SKY"]
    choice = route(REFUSING_QUESTIONS["forecast"], lat=float(site["lat"]),
                   lon=float(site["lon"]), date=DEMO_DATE, threshold_f=103.0)
    rows = dict(ask.mechanism_rows(choice, None))
    assert "refused" in rows["Outcome"]
    assert "none" in rows["Calls made"] and "credit" in rows["Calls made"]
    assert rows["Why"], "the refusal does not carry the reason it refused"


# ---------------------------------------------------- what the tab no longer renders

def test_the_question_type_preset_selectbox_is_gone():
    """DECISION 1: free text in, routing as audit out.

    A six-row menu labelled "Start from one of the six question types" taught that the
    layer is something the USER picks. It is not — the router reads the words, and the
    classification is output, not input. Presenting it as a control made the one genuinely
    interesting thing in the app look like a dropdown."""
    for gone in ("Start from one of the six question types",
                 "EXAMPLE_QUESTIONS", "or ask in your own words"):
        assert gone not in SOURCE, (
            f"{gone!r} is back in app.py — the preset menu makes free-text routing look "
            f"like a mode selector")


def test_the_crews_control_is_a_multiselect_of_crews():
    """A crew IS a site: crew_size, shift_start, shift_end and night_shift are columns on
    config/sites.csv. Being allowed exactly one while being offered "which site is worst"
    was the complaint that started this rebuild."""
    kwargs = _call_keywords("multiselect", label_fragment="Crews")
    assert "default" in kwargs, "the crew control offers no default at all"
    assert "format_func" in kwargs, (
        "the options would render as raw site ids; each one has to read as a crew")

    with pytest.raises(AssertionError):
        _call_keywords("selectbox", label_fragment="Site")


def test_the_landing_panel_is_gone_from_the_ask_tab():
    """The answer column used to be filled, before anything was asked, by three
    paragraphs explaining the routing argument to somebody who had not used the tool yet.
    That argument belongs on "How it decides"; the empty state has to say what to DO."""
    rendered = " ".join(text for _, text in _markdown_literals())
    for landing_copy in ("What this shows",
                         "The router classifies the question against a decision table"):
        assert landing_copy not in rendered, (
            f"{landing_copy!r} is rendered again — the Ask tab is back to explaining "
            f"itself instead of working")
    assert "Press Ask HeatGuard" in rendered, "the empty state no longer tells anyone "\
        "what to do"


def test_the_ask_tab_still_previews_the_routing_for_free():
    """The best thing in the app: the layer is named before any call is made, so a reader
    can watch the classification change as they retype. Losing it to a tidy-up would cost
    more than every paragraph the rebuild deleted."""
    assert "_preview = route(" in SOURCE, "the free live routing preview is gone"
    assert SOURCE.index("_preview = route(") < SOURCE.index('st.button("Ask HeatGuard"'), (
        "the routing preview must render BEFORE the button, or it is not a preview")


# ---------------------------------------------------------------- the tab-reset defect

def _example_chip_button_calls() -> list[ast.Call]:
    """Every `st.button` / `col.button` call that renders an example-question chip."""
    found = []
    for node in ast.walk(TREE):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "button"):
            continue
        # The chips are the only buttons keyed "eg_..."; Ask HeatGuard is keyless.
        for kw in node.keywords:
            if kw.arg == "key" and "eg_" in ast.unparse(kw.value):
                found.append(node)
    return found


def test_the_example_chips_do_not_use_an_on_click_callback():
    """MEASURED on the deployed app, 29 Aug 2026: clicking any example chip reset the
    page to the FIRST tab.

    The chips wrote `st.session_state["ask_question"]` from an `on_click` callback, and
    that string was the question box's own widget `key`. Mutating a widget's key from a
    callback remounts the widget, and the remount takes `st.tabs` with it — whose selected
    tab is client-side state with no server record. Pressing `Ask HeatGuard`, a plain
    button with no callback, did NOT reset the tab, which is what isolated the cause.

    On camera this was fatal: three of the nine pitch-video takes are chip clicks, and
    each one bounced the viewer out of the tab being demonstrated.
    """
    chips = _example_chip_button_calls()
    assert chips, "the example chips are gone entirely"
    for call in chips:
        kwargs = {kw.arg for kw in call.keywords}
        assert "on_click" not in kwargs, (
            "an example chip uses on_click= again. It writes session state BEFORE the "
            "rerun, which remounts the question box and resets st.tabs to tab one. Use "
            "`if col.button(...):` with the st.empty() slot instead.")


def test_the_question_box_is_not_keyed_to_mutated_state():
    """The other half of the same defect: the box must not own the key the chips write.

    `st.empty()` reserves the box's position before the chips run, so the chips can write
    plain (non-widget) state and the box is BUILT afterwards from it — rendering above
    them regardless. If someone re-adds `key=` here, the remount comes back.
    """
    assert "_q_slot = st.empty()" in SOURCE, (
        "the reserved slot is gone; the question box can no longer be built after the "
        "chips, so the callback will come back with it")
    assert SOURCE.index("_q_slot = st.empty()") < SOURCE.index("eg_"), (
        "the slot must be reserved BEFORE the chips render")
    assert SOURCE.index("eg_") < SOURCE.index("_q_slot.text_input("), (
        "the chips must run BEFORE the box is built, or their text lands one rerun late")
    # AST, not a string search: the point is that the Question widget carries no `key=`
    # at all. A comment mentioning the old defect must not be able to fail this.
    for node in ast.walk(TREE):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "text_input"
                and any(isinstance(a, ast.Constant) and a.value == "Question"
                        for a in node.args)):
            kwargs = {kw.arg for kw in node.keywords}
            assert "key" not in kwargs, (
                "the Question box has a `key=` again. Whatever writes that key from a "
                "callback will remount it and reset st.tabs to tab one.")
            assert "value" in kwargs, (
                "the box must take its text from `value=` so a chip press rebuilds it")
            break
    else:
        raise AssertionError("no text_input labelled 'Question' found at all")
