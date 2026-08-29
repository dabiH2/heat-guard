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
    exact = re.findall(r"(?<![Oo]ver )(\d{3}) (?:offline )?tests", SOURCE)
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
