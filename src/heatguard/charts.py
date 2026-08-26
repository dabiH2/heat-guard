"""
charts.py — hand-built SVG for the two figures the pitch actually turns on.

Streamlit's default chart widgets encode a dataframe. These two encode an *argument*,
which is a different job:

  the_day()        WHY the 92% over-count happens. The danger band sits at 13:00–20:00
                   and almost every shift on the roster misses it. This is the figure
                   that makes the headline number obvious instead of asserted.

  phantom_bars()   WHAT that costs. Per site, claimed worker-hours against real ones,
                   so the 701 → 58 collapse is visible per crew rather than in aggregate.

Both are inline SVG with no JS and no chart library: they must render inside Streamlit,
inside a screenshot, and inside a video frame, on a machine with no network.

Colour follows the job rather than taste. Neither figure has categorical *series* — both
encode a binary state (exposed / not exposed), so they use the reserved status palette
with position and direct labels carrying the meaning, never hue alone. Text stays in ink
tokens; only the marks are coloured.
"""

from __future__ import annotations

from html import escape

# ---------------------------------------------------------------- design tokens
# Light values first; the dark column of the same roles is emitted in a media query so
# the figures survive a viewer in dark mode. Roles, not raw hex, throughout the body.
TOKENS_LIGHT = {
    "surface": "#fcfcfb",
    "ink": "#0b0b0b",
    "ink2": "#52514e",
    "muted": "#898781",
    "grid": "#e1e0d9",
    "axis": "#c3c2b7",
    "safe": "#c3c2b7",       # a shift hour nobody is exposed in
    "danger": "#d03b3b",     # status/critical — reserved, never a series colour
    "band": "rgba(208,59,59,0.10)",
    "ghost": "#dedcd4",      # the claim: whole-day exposure
}
TOKENS_DARK = {
    "surface": "#1a1a19",
    "ink": "#ffffff",
    "ink2": "#c3c2b7",
    "muted": "#898781",
    "grid": "#2c2c2a",
    "axis": "#383835",
    "safe": "#4a4a46",
    "danger": "#d03b3b",
    "band": "rgba(208,59,59,0.18)",
    "ghost": "#33332f",
}

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def _style(scope: str) -> str:
    """Token block for one figure, light + both dark scopes."""
    def block(tokens: dict) -> str:
        return "".join(f"--{k}:{v};" for k, v in tokens.items())

    return (
        f"<style>"
        f".{scope}{{{block(TOKENS_LIGHT)}font-family:{FONT};}}"
        f"@media (prefers-color-scheme: dark){{"
        f":root:where(:not([data-theme='light'])) .{scope}{{{block(TOKENS_DARK)}}}}}"
        f":root[data-theme='dark'] .{scope}{{{block(TOKENS_DARK)}}}"
        f"</style>"
    )


def _hhmm_to_hours(value: str) -> float:
    hh, mm = value.split(":")
    return int(hh) + int(mm) / 60.0


# ================================================================= figure 1: the day

def the_day(rows: list[dict], *, band_start: float = 13.0, band_end: float = 20.0,
            threshold_f: float = 103.0) -> str:
    """Every shift on the roster against the one window that was actually dangerous.

    `rows` are shift_exposure records: name, shift, crew, night, worker_hours.

    A shift crossing midnight is drawn as two segments on a single 00:00–24:00 axis
    rather than being silently unwrapped — the crew genuinely is outside during both,
    and hiding the split would misrepresent when they are exposed.
    """
    scope = "hg-day"
    left, right, top = 268, 108, 56
    crew_x = 16
    row_h, bar_h = 28, 13
    width = 980
    plot_w = width - left - right
    height = top + len(rows) * row_h + 40

    def x_of(hour: float) -> float:
        return left + (hour / 24.0) * plot_w

    parts: list[str] = [_style(scope)]
    parts.append(
        f'<svg class="{scope}" viewBox="0 0 {width} {height}" width="100%" '
        f'role="img" aria-label="Each crew shift against the 13:00 to 20:00 window '
        f'above {threshold_f:.0f} degrees Fahrenheit heat index" '
        f'style="background:var(--surface);border-radius:8px">'
    )

    # the danger band, behind everything
    bx, bw = x_of(band_start), x_of(band_end) - x_of(band_start)
    parts.append(f'<rect x="{bx:.1f}" y="{top - 20}" width="{bw:.1f}" '
                 f'height="{height - top - 8}" fill="var(--band)"/>')
    parts.append(f'<line x1="{bx:.1f}" y1="{top - 20}" x2="{bx:.1f}" '
                 f'y2="{height - 28}" stroke="var(--danger)" stroke-width="1.5"/>')
    parts.append(f'<line x1="{bx + bw:.1f}" y1="{top - 20}" x2="{bx + bw:.1f}" '
                 f'y2="{height - 28}" stroke="var(--danger)" stroke-width="1.5"/>')
    parts.append(
        f'<text x="{bx + bw / 2:.1f}" y="{top - 28}" text-anchor="middle" '
        f'font-size="12.5" font-weight="600" fill="var(--danger)">'
        f'above {threshold_f:.0f} °F · 13:00–20:00</text>'
    )

    # hour gridlines every 3 h
    for hour in range(0, 25, 3):
        gx = x_of(hour)
        parts.append(f'<line x1="{gx:.1f}" y1="{top - 20}" x2="{gx:.1f}" '
                     f'y2="{height - 28}" stroke="var(--grid)" stroke-width="1"/>')
        parts.append(f'<text x="{gx:.1f}" y="{height - 12}" text-anchor="middle" '
                     f'font-size="11" fill="var(--muted)">{hour:02d}:00</text>')

    # Exposed crews first. The eye lands on the four rows that carry the decision,
    # and the run of "no exposure" beneath them is the 92% made visible.
    ordered = sorted(rows, key=lambda r: (-r["worker_hours"], r["name"]))

    for i, row in enumerate(ordered):
        y = top + i * row_h
        cy = y + bar_h / 2
        exposed = row["worker_hours"] > 0

        name = row["name"]
        name = name if len(name) <= 32 else name[:31] + "…"
        parts.append(
            f'<text x="{left - 14}" y="{cy + 4:.1f}" text-anchor="end" font-size="12.5" '
            f'fill="var(--ink)">{escape(name)}</text>'
        )
        parts.append(
            f'<text x="{crew_x}" y="{cy + 4:.1f}" font-size="11.5" fill="var(--muted)" '
            f'style="font-variant-numeric:tabular-nums">'
            f'{row["crew"]:>2}{" 🌙" if row["night"] else ""}</text>'
        )

        start = _hhmm_to_hours(row["shift"].split("-")[0])
        end = _hhmm_to_hours(row["shift"].split("-")[1])
        segments = [(start, 24.0), (0.0, end)] if end <= start else [(start, end)]

        for seg_start, seg_end in segments:
            parts.append(
                f'<rect x="{x_of(seg_start):.1f}" y="{y}" '
                f'width="{x_of(seg_end) - x_of(seg_start):.1f}" height="{bar_h}" '
                f'rx="4" fill="var(--safe)" opacity="0.55"/>'
            )

        # The exposed portion is drawn from the MEASURED in-shift hours, not from the
        # geometric overlap with the band. The band is derived from one site's hour-range
        # probes; per-site measurements differ slightly, and drawing geometry would paint
        # a red bar on a site whose own measurement says zero. Where they disagree, the
        # measurement wins and the picture stays honest.
        measured = row.get("in_shift_hours", 0.0)
        if measured > 0:
            for seg_start, seg_end in segments:
                ov_start = max(seg_start, band_start)
                if min(seg_end, band_end) > ov_start:
                    parts.append(
                        f'<rect x="{x_of(ov_start):.1f}" y="{y}" '
                        f'width="{x_of(ov_start + measured) - x_of(ov_start):.1f}" '
                        f'height="{bar_h}" rx="4" fill="var(--danger)"/>'
                    )
                    break

        label = (f'{row["worker_hours"]:.0f} worker-hours' if exposed else "no exposure")
        colour = "var(--danger)" if exposed else "var(--muted)"
        weight = "600" if exposed else "400"
        parts.append(
            f'<text x="{width - right + 10}" y="{cy + 4:.1f}" font-size="11.5" '
            f'font-weight="{weight}" fill="{colour}">{label}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


# ============================================================ figure 2: 701 vs 58

def phantom_bars(rows: list[dict]) -> str:
    """Claimed worker-hours against real ones, per site.

    The aggregate 701 → 58 is easy to disbelieve. Per site it is obvious: the claim bar
    is drawn for every crew, and the real bar exists for four of them.
    """
    scope = "hg-phantom"
    left, right, top = 268, 116, 44
    row_h, bar_h = 30, 10
    width = 980
    plot_w = width - left - right
    height = top + len(rows) * row_h + 26

    claimed = [(r, r["whole_day_hours"] * r["crew"]) for r in rows]
    claimed.sort(key=lambda pair: -pair[1])
    biggest = max(value for _, value in claimed) or 1.0

    def bar_w(value: float) -> float:
        return (value / biggest) * plot_w

    parts: list[str] = [_style(scope)]
    parts.append(
        f'<svg class="{scope}" viewBox="0 0 {width} {height}" width="100%" '
        f'role="img" aria-label="Claimed versus real unsafe worker-hours per site" '
        f'style="background:var(--surface);border-radius:8px">'
    )
    parts.append(
        f'<text x="{left}" y="20" font-size="12.5" fill="var(--ink2)">'
        f'<tspan fill="var(--ghost)">■</tspan> claimed by the city-wide figure   '
        f'<tspan fill="var(--danger)">■</tspan> real, inside the shift</text>'
    )

    for i, (row, claim) in enumerate(claimed):
        y = top + i * row_h
        real = row["worker_hours"]

        name = row["name"]
        name = name if len(name) <= 32 else name[:31] + "…"
        parts.append(
            f'<text x="{left - 14}" y="{y + 11:.1f}" text-anchor="end" font-size="12.5" '
            f'fill="var(--ink)">{escape(name)}</text>'
        )
        parts.append(f'<rect x="{left}" y="{y}" width="{bar_w(claim):.1f}" '
                     f'height="{bar_h}" rx="4" fill="var(--ghost)"/>')
        # 2px surface gap between the two marks, per the mark spec
        parts.append(f'<rect x="{left}" y="{y + bar_h + 2}" width="{bar_w(real):.1f}" '
                     f'height="{bar_h}" rx="4" fill="var(--danger)"/>')

        parts.append(
            f'<text x="{width - right + 8}" y="{y + 15:.1f}" font-size="11.5" '
            f'fill="var(--ink2)" style="font-variant-numeric:tabular-nums">'
            f'{claim:,.0f} → <tspan font-weight="700" '
            f'fill="{"var(--danger)" if real else "var(--muted)"}">{real:,.0f}</tspan>'
            f'</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


# =========================================================== figure 3: the unit trap

def unit_trap() -> str:
    """17.0 h against 0.0 h — the same call, one unit apart.

    A bar pair rather than two numbers side by side, because the point is the *size* of
    the gap between a real answer and a confidently formatted all-clear.
    """
    scope = "hg-trap"
    width, height = 940, 172
    left, plot_w = 300, 480

    parts: list[str] = [_style(scope)]
    parts.append(
        f'<svg class="{scope}" viewBox="0 0 {width} {height}" width="100%" '
        f'role="img" aria-label="Converted threshold returns 17 hours; unconverted '
        f'returns 0 hours" style="background:var(--surface);border-radius:8px">'
    )

    for i, (label, sub, hours, colour) in enumerate([
        ("threshold = 35.00", "95 °F, converted to °C", 17.0, "var(--danger)"),
        ("threshold = 95", "95 °F sent raw → read as 95 °C", 0.0, "var(--muted)"),
    ]):
        y = 44 + i * 62
        parts.append(f'<text x="{left - 16}" y="{y + 12}" text-anchor="end" '
                     f'font-size="14" font-weight="600" fill="var(--ink)" '
                     f'style="font-family:ui-monospace,monospace">{label}</text>')
        parts.append(f'<text x="{left - 16}" y="{y + 29}" text-anchor="end" '
                     f'font-size="11.5" fill="var(--muted)">{sub}</text>')

        w = (hours / 17.0) * plot_w
        if w > 0:
            parts.append(f'<rect x="{left}" y="{y}" width="{w:.1f}" height="20" '
                         f'rx="4" fill="{colour}"/>')
        else:
            parts.append(f'<line x1="{left}" y1="{y + 10}" x2="{left + 22}" '
                         f'y2="{y + 10}" stroke="var(--axis)" stroke-width="2"/>')
        parts.append(f'<text x="{left + max(w, 22) + 12:.0f}" y="{y + 15}" '
                     f'font-size="16" font-weight="700" fill="{colour}">'
                     f'{hours:.1f} h</text>')
        parts.append(f'<text x="{left + max(w, 22) + 78:.0f}" y="{y + 15}" '
                     f'font-size="11.5" fill="var(--muted)">status: Completed · '
                     f'4,220 credits</text>')

    parts.append(f'<text x="{left}" y="{height - 16}" font-size="12.5" '
                 f'font-weight="600" fill="var(--danger)">'
                 f'Same endpoint, area, date, filter_type, analytic_type, direction. '
                 f'Nothing raised.</text>')
    parts.append("</svg>")
    return "".join(parts)
