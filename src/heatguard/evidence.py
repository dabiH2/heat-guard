"""
evidence.py — the external-claim registry, and the only way a figure gets a source link.

A leaf module: it reads `data/evidence/claims.json` and nothing else of ours. `app.py` is
its only caller today; anything else that renders an external figure should become one.

WHY THIS EXISTS
===============
Two kinds of number appear on the surface, and telling them apart is the entire point:

  * MEASURED — the 1.9 °F peak spread, the 643 phantom worker-hours, the 92%, the 17
    hours in the unit trap, the site and crew counts. This project measured those from
    its own committed fixtures. They carry NO external source, because there is none:
    attaching one would be borrowing authority the number does not have.
  * EXTERNAL — the loaded labour rate, the standards architecture, the mandated rest
    fraction. Every one of these belongs to somebody else's document, and a reader has to
    be able to reach that document in one click.

The registry holds the second kind, keyed by id; this module is how a caller renders one.
A figure typed straight into the UI is a figure that detaches from its source the moment
the source is edited — silently, and in the direction that flatters us.

THE CONTRACT
============
`claim()` is TOTAL over known ids and RAISES on everything else. Same discipline as
`bands.band_for`: a lookup that can return None in a tool arguing from evidence is a
citation quietly not made, and an uncited figure on screen reads exactly like a cited one.
A wrong id is a bug in the caller, so it crashes here rather than rendering a number with
nothing behind it.

`tests/test_evidence.py` owns the registry's own integrity — required fields, https
sources, the staleness flag, the GENERAL_POPULATION caveat. This module owns getting a
claim onto the page without losing its source on the way.

NO NETWORK, NO KEY. One committed JSON file, read once. The app has to work offline from
fixtures with no API key at all, and citations are no exception to that.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "evidence" / "claims.json"

#: The scope that must never be read as an occupational figure. Maricopa County does not
#: record occupation, so a general-population death count is not a worker death count —
#: which is why every claim carrying this scope also carries a caveat, and why the caveat
#: is rendered with the claim rather than left to whoever remembers it.
GENERAL_POPULATION = "GENERAL_POPULATION"

#: Fields `tests/test_evidence.py` requires of every claim. Restated here because this
#: module refuses to BUILD a claim that is missing one, rather than filling the blank with
#: None and rendering a link to nowhere.
REQUIRED_FIELDS = (
    "id", "claim", "value", "scope", "source_title", "source_url", "data_year",
)

#: Inline link labels. Long enough to survive `source_title`s that open with a bare
#: "OSHA," or "NIOSH 2016-106,"; short enough that the link does not outrun the figure it
#: qualifies. The full title is always shown in the Sources block, so nothing is lost.
MIN_LABEL_CHARS = 16
MAX_LABEL_CHARS = 52


class EvidenceError(ValueError):
    """The registry is missing, malformed, or self-inconsistent."""


class UnknownClaimError(EvidenceError):
    """A claim id with nothing behind it.

    Deliberately an exception rather than a None or an empty string. The failure mode this
    prevents is a citation marker that renders as ordinary prose: the reader sees a figure
    that looks sourced, follows nothing, and checks nothing.
    """


def _escape_dollars(text: str) -> str:
    """Escape `$` so Streamlit renders currency instead of an equation.

    Streamlit reads `$…$` as LaTeX math and silently eats both currency symbols AND the
    bold markers between them — `**$35,363**` rendered as `35,363` in this very app until
    it was found. COST-01's own claim text carries three `$` (value, wages, benefits), so
    a Sources block that did not escape would turn its own citation into an equation.
    """
    return re.sub(r"(?<!\\)\$", r"\\$", text)


def _short_source(source_title: str) -> str:
    """A link label: the publisher and document, without the page or table number.

    Split on the first comma, then keep taking segments while the label is too short to
    identify anything — "OSHA, Heat Injury and Illness Prevention NPRM" says something;
    "OSHA" alone does not.
    """
    segments = [part.strip() for part in source_title.split(",") if part.strip()]
    label = segments[0] if segments else source_title.strip()
    for extra in segments[1:]:
        if len(label) >= MIN_LABEL_CHARS:
            break
        label = f"{label}, {extra}"
    if len(label) > MAX_LABEL_CHARS:
        clipped = label[:MAX_LABEL_CHARS].rsplit(" ", 1)[0].rstrip(" ,;:—·(")
        # A truncation that lands inside a parenthetical leaves a dangling "(", which
        # reads as a rendering fault rather than as an abbreviation. Drop the fragment.
        if clipped.count("(") > clipped.count(")"):
            clipped = clipped[:clipped.rindex("(")].rstrip(" ,;:—·")
        label = f"{clipped}…"
    return label


@dataclass(frozen=True)
class Claim:
    """One external claim, exactly as the registry holds it.

    `value` is rendered, never recomputed. The registry is the single place the figure
    lives; a caller that does arithmetic on it has forked the source.
    """
    id: str
    claim: str
    value: str
    scope: str
    source_title: str
    source_url: str
    data_year: str
    stale: bool = False
    quote: str | None = None
    doc: str = ""
    caveat: str | None = None

    @property
    def short_source(self) -> str:
        """The inline link label. Never empty — `source_title` is a required field."""
        return _short_source(self.source_title)

    @property
    def is_general_population(self) -> bool:
        return self.scope == GENERAL_POPULATION

    def link(self) -> str:
        """`[short source](url), data year` — markdown, safe to drop inline."""
        return (f"[{_escape_dollars(self.short_source)}]({self.source_url}), "
                f"{_escape_dollars(self.data_year)}")

    def cite(self) -> str:
        """`value (linked short source, data year)` — the inline citation form.

        The data year is the year the DATA refers to, not the year the document was
        published. A 2026 report about 2017 data is a 2017 figure, and the reader is told
        so at the point of use rather than in a footnote nobody opens.
        """
        return f"{_escape_dollars(self.value)} ({self.link()})"

    def bullet(self) -> str:
        """One entry in the Sources block: id, value, claim, full source, data year.

        Carries the two flags that change how the figure should be read — `STALE` for data
        older than three years, and the general-population caveat, which is the specific
        conflation this project must not make.
        """
        lines = [
            f"- **`{self.id}`** · {_escape_dollars(self.value)} — "
            f"{_escape_dollars(self.claim)}",
            f"  [{_escape_dollars(self.source_title)}]({self.source_url}) · data year "
            f"**{_escape_dollars(self.data_year)}** · `{self.doc}`",
        ]
        if self.stale:
            lines.append(
                f"  ⚠️ **STALE** — the newest data behind this claim is from "
                f"{_escape_dollars(self.data_year)}, more than three years before this "
                f"registry was compiled. Read the date, not the flag."
            )
        if self.is_general_population:
            lines.append("  🚩 **GENERAL POPULATION — NOT A WORKER FIGURE.**")
        if self.caveat:
            lines.append(f"  {_escape_dollars(self.caveat)}")
        # Two trailing spaces: a CommonMark HARD line break. A bare newline inside a list
        # item is a soft break, which renders the source url, the staleness flag and the
        # caveat as one run-on paragraph — and a caveat that has to be hunted for inside a
        # sentence is a caveat that will not be read.
        return "  \n".join(lines)


@dataclass(frozen=True)
class Registry:
    """The parsed registry. Built once, validated on the way in."""
    schema_version: int
    compiled: str
    sources: tuple[str, ...]
    claims: tuple[Claim, ...]
    by_id: dict[str, Claim] = field(default_factory=dict, repr=False, compare=False)

    def get(self, claim_id: str) -> Claim:
        """The claim, or a raise naming what was asked for and what exists.

        The error lists the known ids because the realistic mistake is a typo or a stale
        marker left behind by an edit, and both are fixed by seeing the real id.
        """
        try:
            return self.by_id[claim_id]
        except KeyError:
            raise UnknownClaimError(
                f"no claim {claim_id!r} in {REGISTRY_PATH.name}. An unresolvable citation "
                f"renders exactly like a real one, so this raises rather than returning "
                f"nothing. Known ids: {', '.join(sorted(self.by_id))}"
            ) from None


def _build_claim(row: dict, *, index: int) -> Claim:
    for name in REQUIRED_FIELDS:
        value = row.get(name)
        if not (isinstance(value, str) and value.strip()):
            raise EvidenceError(
                f"claim {index} ({row.get('id')!r}) has an empty or missing {name!r}. A "
                f"figure with no source url or no data year is a figure nobody can check."
            )
    stale = row.get("stale", False)
    if not isinstance(stale, bool):
        raise EvidenceError(
            f"{row['id']}: `stale` is {stale!r}, not a boolean. A staleness lie is worse "
            f"than stale data — it is the flag a reader trusts instead of the date."
        )
    if row["scope"] == GENERAL_POPULATION and not (row.get("caveat") or "").strip():
        raise EvidenceError(
            f"{row['id']} is {GENERAL_POPULATION} with no caveat. Maricopa County does not "
            f"record occupation, so the caveat has to travel with the number rather than "
            f"with whoever remembers to add it."
        )
    return Claim(
        id=row["id"],
        claim=" ".join(str(row["claim"]).split()),
        value=" ".join(str(row["value"]).split()),
        scope=row["scope"],
        source_title=" ".join(str(row["source_title"]).split()),
        source_url=row["source_url"].strip(),
        data_year=" ".join(str(row["data_year"]).split()),
        stale=stale,
        quote=row.get("quote"),
        doc=str(row.get("doc") or ""),
        caveat=(" ".join(str(row["caveat"]).split()) if row.get("caveat") else None),
    )


@lru_cache(maxsize=1)
def load_registry(path: Path | None = None) -> Registry:
    """Read and validate `data/evidence/claims.json`. Cached; `.cache_clear()` in tests.

    Once per process, not once per render. Streamlit re-executes `app.py` top to bottom on
    every interaction, and a citation system that re-read and re-parsed a JSON file for
    every link on the page would be paying for its own honesty on every click.
    """
    source = path or REGISTRY_PATH
    if not source.exists():
        raise EvidenceError(
            f"{source} is missing. Every external figure in this project resolves through "
            f"it; without it a citation cannot be rendered and must not be faked."
        )
    raw = json.loads(source.read_text(encoding="utf-8"))

    rows = raw.get("claims")
    if not rows:
        raise EvidenceError(f"{source.name} holds no claims")

    claims = tuple(_build_claim(row, index=i) for i, row in enumerate(rows, 1))
    by_id: dict[str, Claim] = {}
    for item in claims:
        if item.id in by_id:
            raise EvidenceError(
                f"duplicate claim id {item.id!r} — a citation would resolve to whichever "
                f"copy happened to be last"
            )
        by_id[item.id] = item

    return Registry(
        schema_version=int(raw.get("schema_version", 0)),
        compiled=str(raw.get("compiled", "")),
        sources=tuple(raw.get("sources") or ()),
        claims=claims,
        by_id=by_id,
    )


# --------------------------------------------------------------------------- lookup

def claim(claim_id: str) -> Claim:
    """The claim behind an id. TOTAL over known ids; raises on anything else."""
    return load_registry().get(claim_id)


def claim_ids() -> tuple[str, ...]:
    """Every id the registry holds, sorted. For tests and for the error above."""
    return tuple(sorted(load_registry().by_id))


def source_link(claim_id: str) -> str:
    """`[short source](url), data year` — the source alone, for a value already on screen."""
    return claim(claim_id).link()


def cite(claim_id: str) -> str:
    """`value (linked short source, data year)` — value and source together, inline."""
    return claim(claim_id).cite()


def sources_markdown(claim_ids_in_view: tuple[str, ...] | list[str]) -> str:
    """The Sources block for exactly the claims named, in the order given.

    Deliberately NOT the whole registry. Thirty claims under a page that rendered four is
    a bibliography, and a reader cannot tell which of them any figure on screen rests on.
    """
    seen: list[str] = []
    for claim_id in claim_ids_in_view:
        if claim_id not in seen:
            seen.append(claim_id)
    if not seen:
        return (
            "_Nothing on this page rests on an external claim — every figure above was "
            "measured by this project from its own committed fixtures._"
        )
    return "\n".join(claim(claim_id).bullet() for claim_id in seen)


# ------------------------------------------------------------------------- collection

class CitationLog:
    """The external claims one pass of the page actually rendered, in render order.

    Streamlit re-executes `app.py` top to bottom on every interaction, so a log created at
    module scope in that file is a FRESH log per pass. That is what lets the Sources block
    at the foot list what the reader is looking at rather than everything that exists.

    Every method that records an id also renders its link. There is deliberately no way to
    record a claim without linking it: a figure that reached the page from the registry but
    printed no source is precisely the state this module exists to prevent, and
    `tests/test_app_surface.py` asserts that every id `app.py` names arrives through one of
    these calls.
    """

    def __init__(self) -> None:
        self._ids: list[str] = []

    def _record(self, claim_id: str) -> Claim:
        found = claim(claim_id)          # raises before anything is recorded
        if claim_id not in self._ids:
            self._ids.append(claim_id)
        return found

    def cite(self, claim_id: str) -> str:
        """Record and render `value (linked source, data year)`."""
        return self._record(claim_id).cite()

    def link(self, claim_id: str) -> str:
        """Record and render the source link alone."""
        return self._record(claim_id).link()

    def ids(self) -> tuple[str, ...]:
        """The ids rendered so far, first use first."""
        return tuple(self._ids)

    def claims(self) -> tuple[Claim, ...]:
        return tuple(claim(claim_id) for claim_id in self._ids)

    def markdown(self) -> str:
        """The Sources block for this pass. Total: an empty log renders a sentence."""
        return sources_markdown(self._ids)

    def __len__(self) -> int:
        return len(self._ids)

    def __contains__(self, claim_id: object) -> bool:
        return claim_id in self._ids
