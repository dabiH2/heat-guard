"""
Actually RUNS app.py, including pressing the button.

Two bugs shipped to the live demo in one day, both invisible to every other test:

  1. `st.stop()` inside the second tab halted the whole script, so the third and fourth
     tabs rendered empty on a cold visit.
  2. The fix introduced a `NameError` — the helper was defined *after* its module-level
     call site, so a cold load was fine and **pressing the button killed the app**,
     taking every tab with it.

Both were found by a human clicking the deployed app. Neither was reachable by
`ast.parse`, by the engine's tests, or by any static check, because the failure only
exists when Streamlit executes the script and the user interacts with it.

`AppTest` runs the real script in-process. These tests are slow relative to the rest of
the suite and worth every millisecond: the live link is the primary judged artefact.
"""

import pytest
from pathlib import Path

from streamlit.testing.v1 import AppTest

# Absolute: AppTest resolves a relative path against the *calling* file, i.e. tests/.
APP = str(Path(__file__).resolve().parents[1] / "app.py")
TIMEOUT = 90          # cold run parses fixtures and builds three SVG figures


def run(**session_state) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    for key, value in session_state.items():
        at.session_state[key] = value
    return at.run()


# --------------------------------------------------------------- locating a tab
# BY LABEL, never by index. These were `ask_tab(at)` until the Ask tab had to become tab
# one to defuse a tab-reset defect (see test_the_ask_tab_is_first), and every one of them
# broke at once. A test that fails because the tabs were reordered is testing the order,
# not the behaviour it claims to check.

def _tab(at, fragment: str):
    for t in at.tabs:
        if fragment.lower() in t.label.lower():
            return t
    raise AssertionError(
        f"no tab matching {fragment!r}; tabs are {[t.label for t in at.tabs]}")


def ask_tab(at):
    return _tab(at, "Ask a question")


def morning_tab(at):
    return _tab(at, "morning call")


def trap_tab(at):
    return _tab(at, "trap")


def method_tab(at):
    return _tab(at, "How it decides")


@pytest.fixture(scope="module")
def cold() -> AppTest:
    """A cold visit: the app as a judge first sees it, nothing clicked."""
    return run()


# ------------------------------------------------------------------ it runs at all

def test_the_app_runs_without_raising(cold):
    assert not cold.exception, (
        f"app.py raised on a cold run: "
        f"{[f'{e.type}: {e.message}' for e in cold.exception]}"
    )


def test_all_four_tabs_exist(cold):
    labels = [t.label for t in cold.tabs]
    assert len(cold.tabs) == 4, f"expected 4 tabs, got {labels}"
    for expected in ("morning call", "Ask a question", "trap", "How it decides"):
        assert any(expected in l for l in labels), f"{expected!r} missing from {labels}"


# ------------------------------- THE COLD-VISIT REGRESSION: later tabs must have content

def test_every_tab_has_content_on_a_cold_visit(cold):
    """THE st.stop() REGRESSION.

    `st.stop()` halts the entire script, so tabs defined later in the file rendered
    empty until a button in an earlier tab was pressed. A judge opening the app cold saw
    two blank tabs, including the one carrying the 35%-criterion evidence.
    """
    for tab in cold.tabs:
        blocks = len(tab.markdown) + len(tab.subheader) + len(tab.metric) + len(tab.table)
        assert blocks > 0, (
            f"tab {tab.label!r} is EMPTY on a cold visit — something halted the script "
            f"before it. Check for st.stop()."
        )


def test_the_last_tab_carries_the_engineering_evidence(cold):
    """'How it decides' is the 35%-criterion tab and was one of the two that went blank."""
    last = method_tab(cold)
    text = " ".join(m.value for m in last.markdown)
    for expected in ("Built to be relied on", "Refusals are a feature",
                     "does not choose the layer"):
        assert expected in text, f"{expected!r} missing from the final tab"


def test_the_trap_tab_carries_the_seventeen_hours(cold):
    trap = trap_tab(cold)
    text = " ".join(m.value for m in trap.markdown)
    assert "17" in text and "0.0" in text, "the trap figures are missing"


# ----------------------------------- THE BUTTON REGRESSION: pressing it must not crash

def test_pressing_ask_heatguard_does_not_crash():
    """THE NameError REGRESSION.

    The helper was defined after its module-level call site. A cold load took the else
    branch and looked fine; pressing the button called a name that did not exist yet,
    the script died, and every tab's content vanished.
    """
    at = run()
    buttons = [b for b in at.button if "Ask HeatGuard" in b.label]
    assert buttons, "the Ask HeatGuard button is missing"

    after = buttons[0].click().run(timeout=TIMEOUT)
    assert not after.exception, (
        f"pressing Ask HeatGuard raised: "
        f"{[f'{e.type}: {e.message}' for e in after.exception]}"
    )


def test_the_tabs_survive_pressing_the_button():
    """The reported symptom: clicking made the other tabs' content disappear."""
    at = run()
    after = [b for b in at.button if "Ask HeatGuard" in b.label][0].click().run(
        timeout=TIMEOUT)
    assert len(after.tabs) == 4
    for tab in after.tabs:
        blocks = (len(tab.markdown) + len(tab.subheader)
                  + len(tab.metric) + len(tab.table))
        assert blocks > 0, f"tab {tab.label!r} lost its content after the button press"


def test_the_answer_actually_renders_after_the_press():
    """Not just 'no exception' — the answer has to appear.

    UPDATED for the Ask-tab rebuild. It used to look for the heading "The layer, and
    why", which was a `####` above an info box, a four-column parameter row and two
    separate expanders spread down the page. That whole region is now ONE collapsed
    mechanism expander sitting directly under the answer, so the old string is gone by
    design and asserting on it would be asserting on deleted copy.

    What replaces it is stronger, because it checks the two things the rebuild promises
    rather than one heading: an answer headline exists, and the mechanism that produced
    it is adjacent to it.
    """
    at = run()
    after = [b for b in at.button if "Ask HeatGuard" in b.label][0].click().run(
        timeout=TIMEOUT)
    ask = ask_tab(after)
    text = " ".join(m.value for m in ask.markdown)

    assert "### " in text, f"no answer headline rendered; markdown was {text[:200]!r}"
    assert ask.metric or ask.dataframe, (
        "pressing the button produced neither a metric nor a ranking table")
    assert ask.table, (
        "the mechanism definition list is missing — the audit trail must sit with the "
        "answer, not in another tab")


# ------------------------------------------------------------------ money and safety

def test_the_headline_numbers_are_on_the_first_tab(cold):
    """701 -> 58 and 92% are the pitch. If they are missing, the demo has no argument."""
    values = " ".join(str(m.value) for m in morning_tab(cold).metric)
    assert "701" in values, f"701 missing from the first tab's metrics: {values}"
    assert "58" in values, f"58 missing: {values}"
    assert "92" in values, f"92% missing: {values}"


def test_the_offline_banner_is_shown(cold):
    """A judge must be able to see that clicking around cannot spend a credit."""
    text = " ".join(m.value for m in cold.markdown) + " ".join(
        i.value for i in cold.info)
    assert "cached fixture set" in text


# ------------------------------------- THE DATE REGRESSION: every offered date must work

def test_every_offered_date_answers_without_crashing():
    """THE 2025-07-16 REGRESSION.

    `cached_dates()` listed every date appearing anywhere in the fixture index. 2025-07-16
    is in there only as the post-midnight tail of night shifts starting on the 15th — five
    `exceedance` calls, no `env_params`. Selecting it and pressing the button routed to the
    snapshot layer, found no heat index, and raised `KeyError: 'peak'`, which killed the
    script and blanked all four tabs.

    Two defects, both fixed: the dropdown offered a date it could not answer, and the
    render path never checked `out["error"]` before indexing the result.

    Anything the UI OFFERS, the UI must survive. Found by a human clicking the deployed app.
    """
    at = run()
    dates = [sb for sb in at.selectbox if sb.label == "Date"]
    assert dates, "the Date selectbox is missing"
    options = list(dates[0].options)
    assert options, "no dates are offered at all"

    for date in options:
        fresh = run()
        [sb for sb in fresh.selectbox if sb.label == "Date"][0].set_value(date)
        fresh = fresh.run(timeout=TIMEOUT)
        after = [b for b in fresh.button if "Ask HeatGuard" in b.label][0].click().run(
            timeout=TIMEOUT)
        assert not after.exception, (
            f"date {date!r} is offered in the dropdown but crashes on the button press: "
            f"{[f'{e.type}: {e.message}' for e in after.exception]}"
        )


def test_the_night_shift_tail_date_is_not_offered_as_a_date():
    """Pins the specific data shape that caused it, so a future cache refill cannot
    silently reintroduce a date that has heatmap tiles but no heat index."""
    import app as heatguard_app
    from src.heatguard import tools

    combos = tools.cached_combinations()
    tail = {p["date"] for p in combos
            if p.get("date") and p.get("endpoint") == "/v1/heatmap"} - {
           p["date"] for p in combos
           if p.get("date") and p.get("endpoint") == "/v1/env_params"}

    offered = set(heatguard_app.cached_dates())
    assert not (tail & offered), (
        f"{sorted(tail & offered)} have heatmap tiles but no env_params, so the snapshot "
        f"layer cannot answer them — they must not appear in the Date box"
    )
    assert offered, "filtering removed every date; the app now offers nothing"


# --------------------------------------------------- the audit trail must be reachable

def test_the_decision_log_is_visible_and_downloadable(cold):
    """CLAUDE.md calls decisions.jsonl the compliance evidence. It was gitignored and the
    deployed copy lives in ephemeral container storage, so a judge could not reach it —
    the app asserted "Logged to data/decisions.jsonl" and offered no way to check."""
    text = " ".join(m.value for m in method_tab(cold).markdown)
    assert "The audit trail" in text, "the audit-trail section is missing"

    names = [d.label for d in cold.download_button]
    assert any("decision log" in n.lower() for n in names), (
        f"no download button for the decision log; found {names}")


def test_the_audit_view_is_never_empty_on_a_cold_container():
    """The sample is committed precisely so a judge arriving before clicking sees records.
    If the live log is gitignored AND the sample stops loading, the tab shows nothing and
    the compliance claim becomes unverifiable again."""
    import app as heatguard_app
    assert heatguard_app.DECISIONS_SAMPLE.exists(), "the committed sample is gone"
    assert heatguard_app.recent_decisions(5), "no decisions readable from any source"
    assert heatguard_app.decisions_bytes(), "the download would serve an empty file"


def test_an_unrecognised_question_refuses_in_the_ui_without_crashing():
    """The unrecognised refusal carries `question_type=None` BY CONSTRUCTION. Every place
    the UI reads `.question_type.value` is a crash waiting for the first judge who types
    something vague — the same class of bug as the two found by clicking today.

    Exercised through the real widget, both on the live preview and after the press.

    UPDATED for the Ask-tab rebuild: the box used to be labelled "…or ask in your own
    words" because it sat beneath a six-row preset selectbox that it was an alternative
    to. That selectbox is gone — free text is now the only input — so the label is just
    "Question". The behaviour asserted is unchanged.
    """
    at = run()
    box = [t for t in at.text_input if t.label == "Question"][0]
    at = box.set_value("safe?").run(timeout=TIMEOUT)
    assert not at.exception, (
        f"typing an unrecognised question crashed the preview: "
        f"{[f'{e.type}: {e.message}' for e in at.exception]}")

    warned = " ".join(w.value for w in at.warning)
    assert "six question types" in warned, f"no refusal preview shown; warnings: {warned}"

    after = [b for b in at.button if "Ask HeatGuard" in b.label][0].click().run(
        timeout=TIMEOUT)
    assert not after.exception, (
        f"pressing the button on an unrecognised question crashed: "
        f"{[f'{e.type}: {e.message}' for e in after.exception]}")
    for tab in after.tabs:
        blocks = (len(tab.markdown) + len(tab.subheader)
                  + len(tab.metric) + len(tab.table))
        assert blocks > 0, f"tab {tab.label!r} lost its content"


# ------------------------------------------------- the shift plan: the actual product

def test_the_morning_call_leads_with_a_call_per_crew(cold):
    """The landing tab used to open with a statistic about a methodology. A supervisor at
    04:40 needs the calls, without clicking anything."""
    t0 = morning_tab(cold)
    text = " ".join(m.value for m in t0.markdown) + " ".join(s.value for s in t0.success)
    for expected in ("50:10 work/rest", "55:5 work/rest", "no reading"):
        assert expected in text, f"{expected!r} missing from the morning call"
    assert t0.dataframe, "the call sheet is missing"


def test_the_shift_plan_is_downloadable(cold):
    """The artefact is the thing that LEAVES the browser — what a foreman reads at 05:00
    and what sits in the file if an inspector asks what the employer knew and when."""
    labels = [d.label for d in cold.download_button]
    assert any("shift plan" in l.lower() for l in labels), (
        f"no shift-plan download; found {labels}")


def test_the_empty_site_is_never_reported_as_safe(cold):
    """PHX-DVT returned zero tiles, Completed, and was billed 4,220 credits. A coverage
    gap must not be rendered as 0 hours, which reads as an all-clear."""
    t0 = morning_tab(cold)
    warned = " ".join(w.value for w in t0.warning)
    assert "not an all-clear" in warned.lower()
    assert "4,220" in warned


def test_the_headline_metrics_survive_the_rewrite(cold):
    """701 / 58 / 92% are pinned figures and the rewrite must not disturb them; they moved
    below the call sheet, they did not change."""
    values = " ".join(str(m.value) for m in morning_tab(cold).metric)
    for figure in ("701", "58", "92"):
        assert figure in values, f"{figure} lost in the rewrite: {values}"


# ============================================================== the Ask tab, driven
#
# The tab is a working form now, so these drive it: type a question, press the button,
# read what came back. `tests/test_app_surface.py` checks the answer SHAPES in
# milliseconds against `heatguard.ask`; these prove the shapes survive the round trip
# through real widgets, which is where the last two shipped bugs lived.

SNAPSHOT_Q = "How hot is it at this crew's site right now?"
DURATION_Q = "How many hours were they above the threshold today?"
COMPARISON_Q = "Which of these crews is worst today?"
REFUSING_Q = "When should we start and stop today?"


def _ask(question: str, crews=None) -> AppTest:
    """Set the crews and the question through the real widgets, then press the button."""
    at = run()
    if crews is not None:
        [m for m in at.multiselect if m.label == "Crews"][0].set_value(crews)
        at = at.run(timeout=TIMEOUT)
    box = [t for t in at.text_input if t.label == "Question"][0]
    at = box.set_value(question).run(timeout=TIMEOUT)
    return [b for b in at.button if "Ask HeatGuard" in b.label][0].click().run(
        timeout=TIMEOUT)


def _answer_text(at: AppTest) -> str:
    tab = ask_tab(at)
    return " ".join(m.value for m in tab.markdown)


def test_three_questions_render_three_different_answers_for_one_crew():
    """THE BUG THE REBUILD FIXES, end to end through the widgets.

    Same crew, same date, same threshold. Three questions. Before this rebuild all three
    produced the same panel — peak on the left, an optional hours tile beside it — so a
    judge could ask a snapshot question and a duration question and watch nothing change.
    That is the silent-wrong-answer failure the router exists to prevent, reproduced in
    the interface.
    """
    headlines = {}
    for name, question in (("snapshot", SNAPSHOT_Q), ("duration", DURATION_Q),
                           ("comparison", COMPARISON_Q)):
        at = _ask(question, crews=["PHX-SKY"])
        assert not at.exception, (
            f"{name} question raised: "
            f"{[f'{e.type}: {e.message}' for e in at.exception]}")
        lines = [m.value for m in ask_tab(at).markdown if m.value.startswith("### ")]
        assert lines, f"{name} question rendered no answer headline"
        headlines[name] = lines[0]

    assert len(set(headlines.values())) == 3, (
        f"two of the three questions produced the same headline: {headlines}")
    assert "peak" in headlines["snapshot"].lower()
    assert "hours above" in headlines["duration"].lower()
    assert "compare" in headlines["comparison"].lower(), (
        f"a comparison over one crew must say there is nothing to compare it against: "
        f"{headlines['comparison']!r}")


def test_a_snapshot_and_a_duration_answer_carry_different_numbers_of_tiles():
    """A snapshot has no duration to show. A fixed tile row was how the two answers came
    to look identical in the first place."""
    snapshot = _ask(SNAPSHOT_Q, crews=["PHX-SKY"])
    duration = _ask(DURATION_Q, crews=["PHX-SKY"])
    assert len(ask_tab(snapshot).metric) == 1, "a snapshot answer grew a second figure"
    assert len(ask_tab(duration).metric) == 2, (
        "a duration answer must show the whole day AND the hours inside the shift")


def test_several_crews_render_a_ranked_table_not_a_card():
    """The complaint that started the rebuild: one site selectbox against a question that
    asks which site is worst. Two or more crews is a ranking, worst first."""
    at = _ask(COMPARISON_Q, crews=["PHX-27TH", "PHX-CHASE", "PHX-UNHL"])
    assert not at.exception
    frames = ask_tab(at).dataframe
    assert frames, "no ranked table rendered for three crews"
    table = frames[0].value
    assert len(table) == 3, f"expected one row per crew, got {len(table)}"
    assert any("▸" in str(column) for column in table.columns), (
        f"the ranking column is not marked as the one that decides: {list(table.columns)}")
    assert "Morning call" in table.columns, (
        "the ranking does not show what the morning sheet says about the same crews")


def test_a_refused_question_renders_a_refusal_and_spends_nothing():
    """`intraday` refuses in router.py — the only layer that fits returns the hour each
    tile peaks and no schedule at all. The panel has to render that as an answer, not as
    a crash and not as a blank."""
    at = _ask(REFUSING_Q)
    assert not at.exception, (
        f"a refusing question raised: "
        f"{[f'{e.type}: {e.message}' for e in at.exception]}")
    text = _answer_text(at)
    assert "Refused" in text, f"no refusal headline; markdown was {text[:200]!r}"

    errors = " ".join(e.value for e in ask_tab(at).error)
    assert "no credit was spent" in errors, "the refusal does not say nothing was spent"
    assert not ask_tab(at).metric, "a refusal produced a figure, which it cannot have"
    for tab in at.tabs:
        blocks = (len(tab.markdown) + len(tab.subheader)
                  + len(tab.metric) + len(tab.table))
        assert blocks > 0, f"tab {tab.label!r} lost its content on a refusal"


def test_the_mechanism_sits_with_the_answer_and_names_the_layer():
    """Collapsed by default, adjacent to the answer, and complete when opened. It used to
    be a heading, an info box, a four-column parameter row and two expanders spread down
    the page."""
    at = _ask(DURATION_Q, crews=["PHX-SKY"])
    tables = ask_tab(at).table
    assert tables, "the mechanism definition list is missing from the Ask tab"
    rendered = tables[0].value.to_string()
    for field in ("filter_type", "analytic_type", "Unit conversion",
                  "What a snapshot would have said"):
        assert field in rendered, f"{field!r} missing from the mechanism"


def test_the_example_chips_fill_the_question_box():
    """A cold visitor must not face an empty box with no idea what to type. The chips are
    examples, not a mode selector — the text they write is then editable, and the router
    reads the words."""
    at = run()
    chips = [b for b in at.button if b.label in ("Right now", "Hours above",
                                                 "Worst crew")]
    assert len(chips) == 3, f"the example chips are missing; buttons: " \
                            f"{[b.label for b in at.button]}"
    after = chips[0].click().run(timeout=TIMEOUT)
    assert not after.exception
    box = [t for t in after.text_input if t.label == "Question"][0]
    assert "right now" in box.value.lower(), (
        f"clicking an example did not fill the question box: {box.value!r}")


def test_the_ask_tab_is_lean_at_first_glance(cold):
    """THE TEXT DISCIPLINE, measured.

    The brief for this tab is that at first glance it shows the input controls, the
    answer and the mechanism header — and nothing else. It used to open with a
    three-paragraph "What this shows" panel filling the answer column before anything had
    been asked, which is a landing page rather than a tool.

    A character budget rather than a string match, because the failure mode is not one
    sentence coming back — it is prose accumulating a paragraph at a time until the
    controls are below the fold again. Long COMMENTS in app.py are not counted; nothing
    here looks at the source.
    """
    tab = ask_tab(cold)
    rendered = "".join(
        [m.value for m in tab.markdown] + [c.value for c in tab.caption]
        + [i.value for i in tab.info] + [w.value for w in tab.warning]
        + [e.value for e in tab.error] + [s.value for s in tab.success]
    )
    assert len(rendered) < 700, (
        f"the Ask tab renders {len(rendered)} characters before anything is asked. The "
        f"controls, the routing readout and a short empty state are the budget:\n"
        f"{rendered[:600]}")
    assert not tab.subheader, (
        "the Ask tab is back to sectioning itself with subheaders instead of answering")
