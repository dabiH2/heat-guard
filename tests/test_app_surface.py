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
