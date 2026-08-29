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
