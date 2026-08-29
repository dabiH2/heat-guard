"""
Tests for the visual layer.

These do NOT test that the app is pretty — that is not testable and not the point. They
test the two things about the styling that carry MEANING, and would fail silently:

  1. Colour in this app is a signal, not decoration. If the interface accent drifts back
     into the heat ramp, a supervisor scanning for red cannot tell an alarm from a button.
     That is what the previous theme did for four days.
  2. Every band the tool can report must have a colour. A missing one renders as a grey
     chip — the same failure shape as a band lookup returning None, which bands.py
     already refuses to allow.
"""

import re
import tomllib
from pathlib import Path

import pytest

from heatguard import theme
from heatguard.bands import load_thresholds

ROOT = Path(__file__).resolve().parents[1]
CONFIG_TOML = ROOT / ".streamlit" / "config.toml"


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    raw = value.lstrip("#")
    return tuple(int(raw[i:i + 2], 16) for i in (0, 2, 4))


def _distance(a: str, b: str) -> float:
    """Plain Euclidean distance in RGB. Crude, and sufficient: the question is not
    "are these perceptually identical" but "could a hurried person confuse them"."""
    return sum((x - y) ** 2 for x, y in zip(_hex_to_rgb(a), _hex_to_rgb(b))) ** 0.5


# ------------------------------------------------- colour means one thing at a time

def test_every_band_the_tool_can_report_has_a_colour():
    """Both tables. They do NOT share breakpoints — NWS splits at 90/103/125, OSHA at
    91/103/115 — and the UI shows both, so both need covering."""
    t = load_thresholds()
    for table_name, table in (("nws_bands", t.nws_bands), ("osha_actions", t.osha_actions)):
        for band in table:
            assert band.id in theme.HEAT_COLOURS, (
                f"{table_name} band {band.id!r} has no colour, so it would render as a "
                f"grey chip and lose the only signal the chip exists to carry"
            )


def test_the_interface_accent_is_not_inside_the_heat_ramp():
    """THE REGRESSION THIS FILE EXISTS FOR.

    `primaryColor` was "#C1440E", burnt orange. Streamlit paints every interactive
    control in it — buttons, focus rings, selected radio dots, slider tracks, the active
    tab marker. Burnt orange sits inside the heat ramp, so in a heat-safety tool the
    colour of "danger" was also the colour of "this is a button".

    Colour that carries meaning has to be spent, not sprinkled.
    """
    for band_id, ramp_colour in theme.HEAT_COLOURS.items():
        distance = _distance(theme.ACCENT, ramp_colour)
        assert distance > 90, (
            f"the interface accent {theme.ACCENT} is only {distance:.0f} away from the "
            f"{band_id!r} severity colour {ramp_colour}. Chrome and alarm must not be "
            f"confusable."
        )


def test_the_configured_primary_colour_matches_the_accent():
    """config.toml and theme.py must agree, or Streamlit's own controls are painted one
    colour while everything this module styles is painted another."""
    config = tomllib.loads(CONFIG_TOML.read_text(encoding="utf-8"))
    assert config["theme"]["primaryColor"].upper() == theme.ACCENT.upper()


def test_the_ramp_is_ordered_from_cool_to_hot():
    """below_caution must be visibly cooler than danger, or the ramp reads as arbitrary
    and the reader has to consult the legend every time."""
    cool = _hex_to_rgb(theme.HEAT_COLOURS["below_caution"])
    hot = _hex_to_rgb(theme.HEAT_COLOURS["danger"])
    assert cool[2] > cool[0], "below_caution should stay on the cool side"
    assert hot[0] > hot[2], "danger should be red-dominant"


def test_the_severity_bands_are_distinguishable_from_each_other():
    """Five bands that look alike are one band with extra steps."""
    ramp = [theme.HEAT_COLOURS[b] for b in
            ("below_caution", "caution", "extreme_caution", "danger", "extreme_danger")]
    for lower, upper in zip(ramp, ramp[1:]):
        assert _distance(lower, upper) > 45, (
            f"{lower} and {upper} are adjacent bands and too close to tell apart")


# ------------------------------------------------------------------ rendering contract

def test_a_chip_carries_its_colour_inline_not_only_in_a_variable():
    """The chip must not depend on CSS `color-mix()`, which needs Chrome 111 / Safari
    16.2 / Firefox 113. Where it is unsupported the declaration is dropped, the chip
    renders transparent with an invisible border, and the signal is gone — on the one
    artefact judges are guaranteed to open, in whatever browser they happen to have."""
    html = theme.band_chip("danger", "Danger")
    assert "color-mix" not in theme.CSS, "color-mix() is back in the stylesheet"
    assert "background:rgb(" in html and "border:1px solid rgb(" in html
    assert theme.HEAT_COLOURS["danger"] in html


def test_an_unknown_band_renders_grey_rather_than_raising():
    """A typo in a band id is a cosmetic defect. Taking the page down mid-demo over one
    would be worse than a grey chip; the test above is what keeps the table complete."""
    html = theme.band_chip("not_a_real_band", "Unknown")
    assert "hg-chip" in html
    assert "#9AA5B1" in html


def test_the_legend_covers_every_nws_band_in_order():
    legend = theme.heat_scale_legend()
    positions = [legend.find(b.id.replace("_", " ")) for b in load_thresholds().nws_bands]
    assert all(p >= 0 for p in positions), "a band is missing from the legend"
    assert positions == sorted(positions), "the legend is not in temperature order"


# ------------------------------------------------------------------------ the stylesheet

def test_the_stylesheet_is_one_style_block():
    assert theme.CSS.count("<style>") == 1 and theme.CSS.count("</style>") == 1


def test_the_accent_placeholder_was_substituted():
    """CSS is a template with ACCENT_HEX in it. If the substitution is ever removed the
    variable resolves to nothing and every accented element silently loses its colour."""
    assert "ACCENT_HEX" not in theme.CSS
    assert theme.ACCENT in theme.CSS


def test_no_webfont_is_fetched():
    """The deployment argument is that nothing on the page needs a network call at view
    time — the API key expires five days after judging ends and the app serves from a
    committed cache. A webfont would put a third-party request back on that path."""
    for host in ("fonts.googleapis.com", "fonts.gstatic.com", "@import", "typekit"):
        assert host not in theme.CSS, f"{host!r} is a network dependency at view time"


def test_the_stylesheet_stacks_columns_on_a_narrow_viewport():
    """A supervisor checking this before a 5am shift is on a phone. Streamlit columns do
    not reliably collapse on their own."""
    assert "@media (max-width: 768px)" in theme.CSS
    narrow = theme.CSS.split("@media (max-width: 768px)", 1)[1]
    assert "flex-direction: column" in narrow


def test_important_is_used_sparingly():
    """`!important` is how a stylesheet stops being maintainable. A handful is the cost of
    overriding Streamlit's inline styles; a drift upward means the selectors are wrong."""
    count = theme.CSS.count("!important")
    assert count <= 12, f"{count} uses of !important — the selectors have gone wrong"


# ------------------------------------------------- selectors must exist in the DOM
#
# These replace three earlier tests that asserted "the stylesheet mentions stMetric" and
# similar. Those passed while the tab styling was entirely dead, because they checked that
# a selector was PRESENT in the CSS, never that it MATCHED anything. Streamlit 1.62 had
# removed BaseWeb, so `[data-baseweb="tab-list"]` and `[data-baseweb="tab"]` selected
# nothing and the tab bar kept its stock appearance -- which looks exactly like "the CSS
# did not load", which looks exactly like "this is how it was meant to look".

def test_no_baseweb_selectors_survive():
    """THE DEAD-SELECTOR REGRESSION.

    Streamlit 1.62 removed BaseWeb entirely: on the deployed app
    `document.querySelectorAll('[data-baseweb]')` returns zero elements. Any rule keyed to
    one is silently inert. Tabs are react-aria now -- `[role="tablist"]` around
    `[data-testid="stTab"]` divs carrying `aria-selected`.
    """
    assert "data-baseweb" not in theme.CSS, (
        "a data-baseweb selector is back. BaseWeb is gone from Streamlit 1.62 and the "
        "rule will do nothing while looking perfectly reasonable in the source."
    )


def test_every_testid_selector_is_one_verified_against_the_live_dom():
    """An allow-list, not a spell-check.

    `VERIFIED_TESTIDS` was read out of the deployed app on 2026-08-29 against Streamlit
    1.62. Inventing a plausible-looking id is the failure this catches: it costs nothing
    at import, nothing at render, and produces an app that quietly ignores the rule.
    """
    used = set(re.findall(r'data-testid="([^"]+)"', theme.CSS))
    unverified = sorted(used - theme.VERIFIED_TESTIDS)
    assert not unverified, (
        f"{unverified} are not in VERIFIED_TESTIDS. Open the deployed app, confirm the "
        f"selector matches something, then add it to the set with the date."
    )


def test_the_tab_bar_targets_the_react_aria_markup():
    """The specific rules that were dead. Pin the shape, not just the absence."""
    assert '[data-testid="stTabs"] [role="tablist"]' in theme.CSS
    assert '[data-testid="stTab"][aria-selected="true"]' in theme.CSS
    assert ".react-aria-SelectionIndicator" in theme.CSS, (
        "the sliding indicator is still drawn under the segmented control")


def test_no_emotion_hash_class_selectors():
    """e.g. `.css-1d391kg` / `.st-emotion-cache-1ofqig9` -- build artefacts that differ
    per Streamlit release. The live DOM is full of them; none may be depended on."""
    hashed = re.findall(r"\.(?:css|st-emotion-cache)-[0-9a-z]{4,}", theme.CSS)
    assert not hashed, f"version-fragile class selectors: {hashed}"


def test_a_chip_does_not_depend_on_a_custom_property_surviving_sanitisation():
    """THE STRIPPED-VARIABLE REGRESSION.

    The chip used to set `--chip` in its inline style and read it back from the stylesheet
    with `color: var(--chip)`. Measured on the deployed app: the tint and border arrived,
    the TEXT came back rgb(18, 24, 31) -- inherited ink. Streamlit sanitises HTML passed
    under `unsafe_allow_html` and the custom property does not survive.

    It still looked plausible, which is the whole problem: a red-tinted pill with black
    text on a DANGER reading is a signal quietly not sent.
    """
    html = theme.band_chip("danger", "NWS danger")
    colour = theme.HEAT_COLOURS["danger"]
    assert "var(--chip)" not in theme.CSS, "the chip reads a custom property again"
    assert "--chip:" not in html, "the chip writes a custom property again"
    assert f"color:{colour}" in html, "the chip text is not explicitly coloured"
    assert f'class="hg-chip-dot" style="background:{colour}"' in html, (
        "the dot is not explicitly coloured")
