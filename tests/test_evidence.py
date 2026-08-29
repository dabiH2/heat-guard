"""
Pins `data/evidence/claims.json` — the evidence registry, and the citations that point at it.

Every external figure in this project is supposed to trace to `docs/impact-evidence.md` or
`docs/practice-and-efficacy-evidence.md`. Nothing enforces that by itself: a number copied
into README today drifts from its source the moment either file is edited, and a citation
marker outlives the claim it was written for. So the registry is the single place a figure
lives, and this file is the thing that stops it detaching.

Four failures this is written to catch, all of them silent otherwise:

  1. A claim with no source URL or no data year — a figure nobody can check.
  2. A claim whose data is older than three years and is not flagged `stale`. A staleness
     lie is worse than stale data, because it is the flag a reader trusts instead of
     reading the date.
  3. A GENERAL_POPULATION claim with no caveat. Maricopa County's death counts are large,
     local, vivid, and NOT worker figures — the county does not record occupation. Passing
     one off as occupational is the single most likely error in this domain, so the caveat
     is a schema requirement rather than an editorial habit.
  4. A `[[EV:ID]]` marker in README.md, docs/submission-summary-v2.md, app.py or CLAUDE.md
     that resolves to nothing. An unresolvable citation reads exactly like a real one.

Zero markers is a pass, not a skip: an empty set of references trivially resolves. The
citing files are asserted to exist so that a rename cannot quietly turn rule 4 into a
no-op.

Reads committed files only — no network, no key, same standard as the rest of the suite.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "evidence" / "claims.json"

# Files allowed to cite the registry. Rule 4 scans exactly these.
CITING_FILES = (
    "README.md",
    "docs/submission-summary-v2.md",
    "app.py",
    "CLAUDE.md",
)

MARKER = re.compile(r"\[\[EV:([A-Z]{3,5}-\d{2})\]\]")
CLAIM_ID = re.compile(r"^[A-Z]{3,5}-\d{2}$")
YEAR = re.compile(r"(?<!\d)(\d{4})(?!\d)")

# `stale` means "the most recent available data is older than three years", measured
# against the 29 Aug 2026 compilation date of the evidence pack.
STALE_BEFORE = 2023

ALLOWED_SCOPES = {
    "OCCUPATIONAL",
    "GENERAL_POPULATION",
    "AMBIENT",
    "ECONOMY_WIDE",
    "PRACTICE",
    "REGULATORY",
    "ACCURACY",
}

REQUIRED_FIELDS = (
    "id", "claim", "value", "scope", "source_title", "source_url", "data_year",
)


def latest_year(data_year: str) -> int | None:
    """The last year a `data_year` string refers to.

    `data_year` is prose, not a number — "2024", "May 2025", "2011–2022", "2015–16" all
    appear in the evidence pack and all are copied across verbatim rather than normalised,
    because normalising is where a year gets invented. Staleness is judged on the most
    recent year mentioned, so a range is only stale once its newest end is stale.
    """
    years = [int(y) for y in YEAR.findall(data_year)]
    return max(years) if years else None


@pytest.fixture(scope="module")
def registry() -> dict:
    assert REGISTRY.exists(), (
        f"{REGISTRY.relative_to(ROOT)} is missing — every cited figure in this repo "
        f"resolves through it"
    )
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def claims(registry) -> list[dict]:
    return registry["claims"]


# --------------------------------------------------------------------- well-formedness

def test_the_registry_carries_its_envelope(registry):
    """schema_version and the source list are what make a stale registry detectable."""
    assert registry["schema_version"] == 1
    assert registry["compiled"], "an undated registry cannot be judged stale"
    assert registry["sources"], "the registry must name the docs it was compiled from"
    for source in registry["sources"]:
        assert (ROOT / source).exists(), f"claims.json cites a missing source: {source}"


def test_the_registry_is_not_trivially_small(claims):
    assert len(claims) >= 20, "too few claims to carry the submission's figures"


# ------------------------------------------------------------------- rule 1: completeness

def test_every_claim_carries_every_required_field(claims):
    """A figure with no URL or no data year is a figure nobody can check."""
    for i, claim in enumerate(claims, 1):
        for field in REQUIRED_FIELDS:
            assert field in claim, f"claim {i} ({claim.get('id')}) has no {field!r}"
            value = claim[field]
            assert isinstance(value, str) and value.strip(), (
                f"claim {i} ({claim.get('id')}) has an empty {field!r}"
            )


def test_every_claim_anchors_back_into_the_evidence_pack(claims):
    """`doc` is what makes the full caveat one click away from the number."""
    for claim in claims:
        anchor = claim.get("doc", "")
        assert isinstance(anchor, str) and anchor.strip(), (
            f"{claim['id']} has no doc anchor"
        )
        assert anchor.startswith(("impact-evidence.md", "practice-and-efficacy-evidence.md")), (
            f"{claim['id']} anchors outside the evidence pack: {anchor!r}"
        )


def test_quote_is_verbatim_text_or_null(claims):
    """Never an empty string — that reads as "no quote exists" and "the quote is blank"
    at the same time."""
    for claim in claims:
        assert "quote" in claim, f"{claim['id']} has no quote field"
        quote = claim["quote"]
        assert quote is None or (isinstance(quote, str) and quote.strip()), (
            f"{claim['id']} has an empty quote — use null"
        )


# --------------------------------------------------------------- rules 2 and 3: identity

def test_every_id_matches_the_pattern(claims):
    for claim in claims:
        assert CLAIM_ID.match(claim["id"]), (
            f"{claim['id']!r} does not match ^[A-Z]{{3,5}}-\\d{{2}}$"
        )


def test_ids_are_unique(claims):
    ids = [claim["id"] for claim in claims]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    assert not duplicates, f"duplicate claim ids: {duplicates}"


def test_every_source_url_is_https(claims):
    for claim in claims:
        assert claim["source_url"].startswith("https://"), (
            f"{claim['id']} has a non-https source_url: {claim['source_url']!r}"
        )


# ------------------------------------------------------------------------ rule 4: scope

def test_every_scope_is_in_the_allowed_set(claims):
    for claim in claims:
        assert claim["scope"] in ALLOWED_SCOPES, (
            f"{claim['id']} has scope {claim['scope']!r}, "
            f"not one of {sorted(ALLOWED_SCOPES)}"
        )


# --------------------------------------------------------------------- rule 5: staleness

def test_every_data_year_names_a_year(claims):
    """Guards the staleness test itself: a `data_year` no year can be read out of would
    make the check below pass by being unparseable rather than by being fresh."""
    for claim in claims:
        assert latest_year(claim["data_year"]) is not None, (
            f"{claim['id']} has a data_year with no year in it: {claim['data_year']!r}"
        )


def test_a_stale_claim_is_flagged_stale(claims):
    """The build fails on a staleness lie. This is the assertion that makes `stale`
    worth reading."""
    unflagged = [
        f"{c['id']} (data_year {c['data_year']!r})"
        for c in claims
        if (year := latest_year(c["data_year"])) is not None
        and year < STALE_BEFORE
        and c.get("stale") is not True
    ]
    assert not unflagged, (
        f"claims with data older than {STALE_BEFORE} that are not flagged stale: "
        f"{unflagged}"
    )


def test_a_current_claim_is_not_flagged_stale(claims):
    """The other direction. A false [STALE] mark discredits a current figure, and both
    directions have to hold for `stale` to be derivable from `data_year`."""
    over_flagged = [
        f"{c['id']} (data_year {c['data_year']!r})"
        for c in claims
        if (year := latest_year(c["data_year"])) is not None
        and year >= STALE_BEFORE
        and c.get("stale") is True
    ]
    assert not over_flagged, (
        f"claims from {STALE_BEFORE} or later flagged stale: {over_flagged}"
    )


def test_stale_is_a_boolean_everywhere(claims):
    for claim in claims:
        assert isinstance(claim.get("stale"), bool), (
            f"{claim['id']} has a non-boolean stale: {claim.get('stale')!r}"
        )


# ------------------------------------------------------------- rule 6: the GEN POP guard

def test_general_population_claims_carry_a_caveat(claims):
    """Maricopa County's counts are not worker figures and the county does not record
    occupation. Conflating the two is the specific error this project must not make, so
    the caveat travels with the number rather than with whoever remembers to add it."""
    for claim in claims:
        if claim["scope"] != "GENERAL_POPULATION":
            continue
        caveat = claim.get("caveat")
        assert isinstance(caveat, str) and caveat.strip(), (
            f"{claim['id']} is GENERAL_POPULATION with no caveat"
        )
        lowered = caveat.lower()
        assert "not a worker" in lowered or "not worker" in lowered, (
            f"{claim['id']}'s caveat does not say it is not a worker figure"
        )
        assert "occupation" in lowered, (
            f"{claim['id']}'s caveat does not say the county does not record occupation"
        )


# ------------------------------------------------------------ rule 7: citations resolve

def _markers_in(relative_path: str) -> list[tuple[int, str]]:
    """Every [[EV:ID]] in a file, with the line it sits on."""
    path = ROOT / relative_path
    found: list[tuple[int, str]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        found.extend((lineno, claim_id) for claim_id in MARKER.findall(line))
    return found


def test_every_citing_file_exists():
    """Rule 7 scans four named files. If one is renamed the scan silently finds nothing
    and every citation in it stops being checked — so the scan's own inputs are pinned."""
    for relative_path in CITING_FILES:
        assert (ROOT / relative_path).exists(), (
            f"{relative_path} is cited by tests/test_evidence.py and does not exist"
        )


def test_every_ev_marker_resolves_to_a_claim(claims):
    """An unresolvable citation reads exactly like a real one, which is why it fails the
    build rather than warning. Zero markers is a pass: an empty set of references
    trivially resolves."""
    known = {claim["id"] for claim in claims}
    unresolved = [
        f"{relative_path}:{lineno} cites [[EV:{claim_id}]], which is not in the registry"
        for relative_path in CITING_FILES
        for lineno, claim_id in _markers_in(relative_path)
        if claim_id not in known
    ]
    assert not unresolved, "\n".join(unresolved)
