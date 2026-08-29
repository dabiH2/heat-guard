"""
theme.py — the visual layer. A leaf: imports `bands` and nothing else of ours.

WHY THIS EXISTS, AND WHY IT IS NOT DECORATION
=============================================
`.streamlit/config.toml` used to carry a comment arguing that custom styling would be the
over-engineering the judge's "Builder's Trap" talk warns about. That was right about
decoration and wrong about one specific thing, which turned out to be a defect:

    primaryColor = "#C1440E"        # burnt orange

Streamlit paints EVERY interactive control in `primaryColor` — buttons, focus rings,
selected radio dots, slider tracks, the active tab underline. Burnt orange sits squarely
inside the heat ramp. So in a tool whose entire job is to signal thermal danger, the
colour of "danger" was also the colour of "this is a button". A supervisor scanning the
screen for red had no way to tell an alarm from a control.

Colour that carries meaning has to be spent, not sprinkled. So:

  * The interface accent is TEAL. It appears on things you can click and nowhere else.
    It is deliberately outside the heat ramp, which frees amber/orange/red/magenta to
    mean exactly one thing.
  * The heat ramp follows the published NWS heat-index chart, so a supervisor who has
    seen that chart on a wall recognises the colours without a legend.
  * `HEAT_COLOURS` is keyed by the band ids in config/thresholds.yaml and is checked
    against them by a test. A band with no colour would render as an uncoloured chip —
    the same failure shape as a band lookup returning None, which bands.py already
    refuses to allow.

NO WEBFONT, DELIBERATELY
========================
The whole deployment argument is that nothing on the page depends on a network call at
view time — the API key expires five days after judging ends and the app serves from a
committed fixture cache. Pulling a typeface from Google Fonts would put a third-party
request back on the critical path of the one artefact judges are guaranteed to open.
The system stack renders instantly and looks native on every machine a judge will use.

LIGHT IS PINNED
===============
`base = "light"` in config.toml is deterministic on purpose: the demo video and the
judged screenshots must match. Viewers can still switch via the Streamlit menu.
"""

from __future__ import annotations

from .bands import load_thresholds

# --------------------------------------------------------------------------- palette

#: Interface accent. Outside the heat ramp BY CONSTRUCTION — see the module docstring and
#: `tests/test_theme.py::test_the_interface_accent_is_not_inside_the_heat_ramp`.
ACCENT = "#0E6E7E"

#: Heat severity, approximating the NWS heat-index chart. Keyed by `nws_bands` ids and by
#: `osha_actions` ids from config/thresholds.yaml — both tables, because the UI shows both
#: and they do NOT share breakpoints (NWS splits at 90/103/125, OSHA at 91/103/115).
HEAT_COLOURS: dict[str, str] = {
    # nws_bands
    # Slate, not blue. "Below caution" is the ABSENCE of a signal, and a saturated blue
    # reads as one. It was blue until a test measured it 83 RGB units from the teal
    # interface accent — close enough that a cool chip and a clickable control could be
    # confused, which is the exact defect this palette was rebuilt to remove.
    "below_caution":   "#6E7C8A",
    "caution":         "#D9A21B",   # amber
    "extreme_caution": "#DD7327",   # orange
    "danger":          "#C6342C",   # red
    "extreme_danger":  "#8E2751",   # magenta, as NWS uses for its top band
    # osha_actions
    "normal":          "#6E7C8A",
    "basic":           "#D9A21B",
    "moderate":        "#DD7327",
    "high":            "#C6342C",
    "very_high":       "#8E2751",
}

#: Everything the heat ramp owns. Nothing in the interface chrome may use these.
RESERVED_FOR_HEAT = frozenset(HEAT_COLOURS.values())


def colour_for_band(band_id: str) -> str:
    """The colour for a band id, or the accent-neutral grey if it is unknown.

    Unknown ids do not raise: a missing colour is a cosmetic defect, and crashing the
    page over one would be a worse outcome than a grey chip. The TEST is what keeps the
    table complete; this fallback only stops a typo taking the app down mid-demo.
    """
    return HEAT_COLOURS.get(band_id, "#9AA5B1")


def _mix_with_white(hex_colour: str, weight: float) -> str:
    """Blend `weight` of the colour into white. Plain rgb output.

    Done here rather than with CSS `color-mix()`, which needs Chrome 111 / Safari 16.2 /
    Firefox 113. On anything older `color-mix` fails to parse, the declaration is dropped,
    and the chip renders transparent with an invisible border -- losing exactly the signal
    the chip exists to carry. Colour is the meaning; it does not get to depend on a recent
    CSS feature.
    """
    raw = hex_colour.lstrip("#")
    r, g, b = (int(raw[i:i + 2], 16) for i in (0, 2, 4))
    blend = lambda c: round(c * weight + 255 * (1 - weight))
    return f"rgb({blend(r)}, {blend(g)}, {blend(b)})"


def band_chip(band_id: str, label: str) -> str:
    """An inline severity chip. Colour carries the meaning, text carries the detail.

    EVERY colour is written inline, including the text colour and the dot. The first
    version set one CSS custom property inline and read it back from the stylesheet with
    `color: var(--chip)`. Measured on the deployed app: the tint and border arrived, and
    the TEXT came back rgb(18, 24, 31) -- inherited ink, not the band colour. Streamlit
    sanitises the HTML it accepts under `unsafe_allow_html`, and the custom property does
    not survive it, so `var(--chip)` resolved to nothing and fell through to inheritance.

    The chip still looked plausible, which is the problem: a red-tinted pill with
    black text on a DANGER reading is a signal quietly not sent. Nothing here may depend
    on a declaration that a sanitiser is free to drop.
    """
    colour = colour_for_band(band_id)
    tint = _mix_with_white(colour, 0.11)
    edge = _mix_with_white(colour, 0.34)
    return (
        f'<span class="hg-chip" style="color:{colour};background:{tint};'
        f'border:1px solid {edge}">'
        f'<span class="hg-chip-dot" style="background:{colour}"></span>{label}</span>'
    )


def heat_scale_legend() -> str:
    """The full ramp, in order, as a single row. Shown once so the colours are readable
    everywhere else without repeating themselves."""
    bands = load_thresholds().nws_bands
    items = "".join(
        f'<div class="hg-legend-item">'
        f'<span class="hg-legend-swatch" style="background:{colour_for_band(b.id)}"></span>'
        f'<span class="hg-legend-label">{b.id.replace("_", " ")}</span>'
        f'<span class="hg-legend-range">'
        f'{"&lt; 80" if b.min_f < 0 else (f"{b.min_f:.0f}+" if b.max_f > 900 else f"{b.min_f:.0f}–{b.max_f:.0f}")}'
        f' °F</span></div>'
        for b in bands
    )
    return f'<div class="hg-legend">{items}</div>'


# ------------------------------------------------------------------------------- css
#
# SELECTORS ARE VERIFIED LIVE, NOT GUESSED.
#
# The first version of this stylesheet targeted `[data-baseweb="tab-list"]`,
# `[data-baseweb="tab"]` and `[data-baseweb="select"]`. It shipped, the tests passed, and
# every one of those rules was dead: **Streamlit 1.62 removed BaseWeb entirely** --
# `document.querySelectorAll('[data-baseweb]')` returns nothing on the deployed app. The
# tab bar simply kept its stock appearance, which is indistinguishable from "the CSS did
# not load", which is indistinguishable from "this is how I wanted it to look".
#
# Every id below was read out of the live DOM at https://heat-fortyguard.streamlit.app
# on 2026-08-29 against Streamlit 1.62, and `tests/test_theme.py` refuses any selector
# that is not in this set. Adding one means checking it in a browser first.
#
# Tabs in 1.62 are react-aria: a `[role="tablist"]` containing `[data-testid="stTab"]`
# DIVs (not buttons) carrying `aria-selected`, plus a `.react-aria-SelectionIndicator`
# element for the sliding underline, which this stylesheet hides.

#: Read out of the deployed DOM on 2026-08-29, Streamlit 1.62. The test uses this as an
#: allow-list, so an unverified selector fails rather than silently doing nothing.
VERIFIED_TESTIDS = frozenset({
    "stAlert", "stAlertContainer", "stAlertContentError", "stAlertContentInfo",
    "stAlertContentSuccess", "stAlertContentWarning", "stApp", "stAppViewContainer",
    "stBaseButton-primary", "stBaseButton-secondary", "stButton", "stCaptionContainer",
    "stColumn", "stDataFrame", "stDownloadButton", "stElementContainer", "stExpander",
    "stExpanderDetails", "stHeader", "stHeading", "stHorizontalBlock", "stLayoutWrapper",
    "stMain", "stMainBlockContainer", "stMarkdown", "stMarkdownContainer", "stMetric",
    "stMetricLabel", "stMetricValue", "stRadio", "stRadioGroup", "stRadioOption",
    "stSelectbox", "stSlider", "stTab", "stTabPanel", "stTable", "stTabs", "stTextInput",
    "stTextInputField", "stTextInputRootElement", "stTooltipIcon", "stVerticalBlock",
    "stWidgetLabel",
})
#: `stAlertContentWarning` is the one id not observed directly -- no warning was on screen
#: during the sweep. It is included on the symmetry of the other three alert contents, and
#: the cost of being wrong is one untinted left border.

_CSS = """
<style>
:root {
  --hg-ink:            #12181F;
  --hg-ink-soft:       #47545F;
  --hg-ink-faint:      #74828E;
  --hg-surface:        #FFFFFF;
  --hg-panel:          #F5F7F9;
  --hg-panel-2:        #EAEFF3;
  --hg-border:         #DBE2E9;
  --hg-border-strong:  #BFCAD4;
  --hg-accent:         ACCENT_HEX;
  --hg-accent-dark:    #0A5361;
  --hg-accent-wash:    #E6F1F3;
  --hg-radius:         8px;
  --hg-sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
             "Helvetica Neue", Arial, sans-serif;
  --hg-mono: ui-monospace, "SF Mono", "Cascadia Mono", "Roboto Mono", Menlo,
             Consolas, monospace;
}

[data-testid="stApp"], [data-testid="stAppViewContainer"] {
  font-family: var(--hg-sans);
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

/* Streamlit's default top padding costs most of the first screenful, and the first
   screenful is the entire time-to-value budget. */
[data-testid="stMainBlockContainer"] {
  padding-top: 2.2rem;
  padding-bottom: 4rem;
  max-width: 1180px;
}

/* ------------------------------------------------------------------ type hierarchy */

[data-testid="stHeading"] h1 {
  font-size: 2.05rem;
  font-weight: 680;
  letter-spacing: -0.021em;
  color: var(--hg-ink);
  margin-bottom: 0.15rem;
}
[data-testid="stHeading"] h2 {
  font-size: 1.42rem; font-weight: 640; letter-spacing: -0.014em; color: var(--hg-ink);
}
[data-testid="stHeading"] h3 {
  font-size: 1.12rem; font-weight: 640; letter-spacing: -0.008em; color: var(--hg-ink);
}
[data-testid="stMarkdownContainer"] h3 { font-size: 1.12rem; font-weight: 640; }
[data-testid="stMarkdownContainer"] h4 {
  font-size: 0.97rem; font-weight: 660; color: var(--hg-ink); margin-top: 1.5rem;
}

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
  color: var(--hg-ink-soft);
  line-height: 1.62;
  font-size: 0.945rem;
}
[data-testid="stMarkdownContainer"] strong { color: var(--hg-ink); font-weight: 640; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
  color: var(--hg-ink-faint);
  font-size: 0.815rem;
  line-height: 1.5;
}

/* Inline code is load-bearing here -- filter_type=3, analytic_type=exceedance. It should
   read as a precise machine value, not as decorated prose. */
[data-testid="stMarkdownContainer"] code {
  font-family: var(--hg-mono);
  font-size: 0.845em;
  background: var(--hg-panel-2);
  color: var(--hg-accent-dark);
  border: 1px solid var(--hg-border);
  border-radius: 5px;
  padding: 0.09em 0.36em;
  white-space: nowrap;
}

hr { border: none; border-top: 1px solid var(--hg-border); margin: 1.6rem 0 1.35rem; }

/* ------------------------------------------------------------------------- tabs */
/* A segmented control. 1.62 tabs are react-aria: [role="tablist"] wrapping
   [data-testid="stTab"] DIVs with aria-selected, plus a sliding indicator element.
   The stock underline is easy to miss, and "which tab am I on" is the most common
   orientation failure in a multi-tab Streamlit app. */

[data-testid="stTabs"] [role="tablist"] {
  gap: 0.28rem;
  background: var(--hg-panel);
  border: 1px solid var(--hg-border);
  border-radius: 10px;
  padding: 0.3rem;
  margin-bottom: 1.35rem;
  overflow-x: auto;
  scrollbar-width: thin;
}
[data-testid="stTab"] {
  height: auto;
  padding: 0.5rem 0.95rem;
  border-radius: 7px;
  color: var(--hg-ink-soft);
  white-space: nowrap;
  transition: background 120ms ease, color 120ms ease;
}
[data-testid="stTab"] [data-testid="stMarkdownContainer"] p {
  font-size: 0.9rem;
  font-weight: 560;
  color: inherit;
  margin: 0;
}
[data-testid="stTab"]:hover { background: var(--hg-panel-2); color: var(--hg-ink); }
[data-testid="stTab"][aria-selected="true"] {
  background: var(--hg-surface);
  color: var(--hg-accent-dark);
  box-shadow: 0 1px 2px rgba(18, 24, 31, 0.10), 0 0 0 1px var(--hg-border-strong);
}
[data-testid="stTab"][aria-selected="true"] [data-testid="stMarkdownContainer"] p {
  font-weight: 640;
}
.react-aria-SelectionIndicator { display: none; }

/* ---------------------------------------------------------------------- metrics */
/* Instrument panel, not infographic: bordered, aligned, unambiguous. */

[data-testid="stMetric"] {
  background: var(--hg-surface);
  border: 1px solid var(--hg-border);
  border-radius: var(--hg-radius);
  padding: 0.85rem 0.95rem 0.9rem;
  box-shadow: 0 1px 2px rgba(18, 24, 31, 0.04);
  height: 100%;
}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p {
  font-size: 0.775rem !important;
  font-weight: 600;
  letter-spacing: 0.035em;
  text-transform: uppercase;
  color: var(--hg-ink-faint) !important;
  line-height: 1.35;
}
[data-testid="stMetricValue"] {
  font-size: 1.72rem;
  font-weight: 660;
  letter-spacing: -0.02em;
  color: var(--hg-ink);
  font-variant-numeric: tabular-nums;
}

/* --------------------------------------------------------------------- controls */

[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-secondary"],
[data-testid="stDownloadButton"] button {
  border-radius: 7px;
  font-weight: 600;
  font-size: 0.9rem;
  padding: 0.52rem 1.05rem;
  transition: background 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
}
[data-testid="stBaseButton-primary"] {
  background: var(--hg-accent);
  border: 1px solid var(--hg-accent);
  color: #FFFFFF;
}
[data-testid="stBaseButton-primary"]:hover {
  background: var(--hg-accent-dark);
  border-color: var(--hg-accent-dark);
}
[data-testid="stBaseButton-secondary"], [data-testid="stDownloadButton"] button {
  background: var(--hg-surface);
  border: 1px solid var(--hg-border-strong);
  color: var(--hg-ink);
}
[data-testid="stBaseButton-secondary"]:hover,
[data-testid="stDownloadButton"] button:hover {
  border-color: var(--hg-accent);
  color: var(--hg-accent-dark);
  background: var(--hg-accent-wash);
}

[data-testid="stWidgetLabel"] p {
  font-size: 0.845rem !important;
  font-weight: 600 !important;
  color: var(--hg-ink) !important;
}

[data-testid="stSelectbox"] > div > div,
[data-testid="stTextInputRootElement"] {
  border-radius: 7px;
  border-color: var(--hg-border-strong);
  font-size: 0.9rem;
}
[data-testid="stTextInputRootElement"]:focus-within {
  border-color: var(--hg-accent) !important;
  box-shadow: 0 0 0 2px var(--hg-accent-wash) !important;
}
[data-testid="stRadioOption"] { font-size: 0.885rem; }

/* ----------------------------------------------------------------------- alerts */
/* A left rule instead of a full wash. Full-bleed tinted blocks read as decoration and,
   at this density, three stacked ones look like an error state. */

[data-testid="stAlertContainer"] {
  border-radius: 0 var(--hg-radius) var(--hg-radius) 0;
  border: 1px solid var(--hg-border);
  border-left-width: 3px;
  padding: 0.78rem 1rem;
}
[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {
  font-size: 0.905rem;
  line-height: 1.58;
}
[data-testid="stAlertContentInfo"]    { border-left-color: var(--hg-accent); }
[data-testid="stAlertContentSuccess"] { border-left-color: #2E7D5B; }
[data-testid="stAlertContentWarning"] { border-left-color: #DD7327; }
[data-testid="stAlertContentError"]   { border-left-color: #C6342C; }

[data-testid="stExpander"] details {
  border: 1px solid var(--hg-border);
  border-radius: var(--hg-radius);
  background: var(--hg-surface);
}
[data-testid="stExpander"] summary { font-size: 0.885rem; font-weight: 580; }

/* ------------------------------------------------------------------ data display */

[data-testid="stDataFrame"], [data-testid="stTable"] {
  border: 1px solid var(--hg-border);
  border-radius: var(--hg-radius);
  overflow: hidden;
}
[data-testid="stDataFrame"] { overflow-x: auto; }

/* ------------------------------------------------------ severity chips + legend */
/* Colours arrive INLINE, per chip -- see band_chip(). Streamlit's HTML sanitiser drops
   inline CSS custom properties, so anything read back with var() silently loses its
   value. This block owns geometry only. */

.hg-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.16rem 0.6rem 0.16rem 0.5rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 620;
  line-height: 1.5;
  white-space: nowrap;
}
.hg-chip-dot { width: 0.44rem; height: 0.44rem; border-radius: 999px; flex: none; }

.hg-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 1.15rem;
  padding: 0.7rem 0.9rem;
  background: var(--hg-panel);
  border: 1px solid var(--hg-border);
  border-radius: var(--hg-radius);
  margin: 0.35rem 0 0.9rem;
}
.hg-legend-item { display: flex; align-items: baseline; gap: 0.42rem; font-size: 0.79rem; }
.hg-legend-swatch {
  width: 0.62rem; height: 0.62rem; border-radius: 2px; align-self: center; flex: none;
}
.hg-legend-label { font-weight: 620; color: var(--hg-ink); text-transform: capitalize; }
.hg-legend-range { color: var(--hg-ink-faint); font-variant-numeric: tabular-nums; }

/* --------------------------------------------------------------- responsiveness */
/* Streamlit columns do not always collapse on a narrow viewport, and a supervisor
   checking this before a shift is on a phone. Below 768px everything goes single file,
   wide content scrolls inside its own box, and the page body never scrolls sideways. */

[data-testid="stAppViewContainer"] { overflow-x: hidden; }

@media (max-width: 768px) {
  [data-testid="stMainBlockContainer"] {
    padding-left: 1rem; padding-right: 1rem; padding-top: 1.4rem;
  }
  [data-testid="stHorizontalBlock"] { flex-direction: column; gap: 0.75rem; }
  [data-testid="stColumn"] { width: 100% !important; flex: 1 1 100% !important; min-width: 0; }
  [data-testid="stHeading"] h1 { font-size: 1.62rem; }
  [data-testid="stMetricValue"] { font-size: 1.42rem; }
  [data-testid="stTab"] { padding: 0.45rem 0.7rem; }
  [data-testid="stTab"] [data-testid="stMarkdownContainer"] p { font-size: 0.85rem; }
  .hg-legend { gap: 0.3rem 0.8rem; }
}

@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
</style>
"""

CSS = _CSS.replace("ACCENT_HEX", ACCENT)

#: Session-state key. Streamlit re-executes the script top to bottom on every interaction,
#: so an unguarded inject appends another <style> block per click; after a demo's worth of
#: clicking that is dozens of identical blocks in the DOM.
_INJECTED_KEY = "_hg_theme_injected"


def inject(st) -> bool:
    """Write the stylesheet into the page. Idempotent within a session.

    Takes `st` as an argument rather than importing streamlit, so this module stays
    importable — and testable — without a Streamlit runtime.

    Returns True if it wrote the block, False if it was already there.
    """
    try:
        if st.session_state.get(_INJECTED_KEY):
            return False
        st.session_state[_INJECTED_KEY] = True
    except Exception:
        # No script-run context (bare import, a test, a doc build). Style anyway; the
        # only cost of a duplicate <style> is a duplicate <style>.
        pass
    st.markdown(CSS, unsafe_allow_html=True)
    return True
