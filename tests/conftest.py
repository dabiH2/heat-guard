"""Shared fixtures. Everything here reads committed files — no network, no credits."""

import csv
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"


@pytest.fixture(scope="session")
def site_rows() -> list[dict]:
    """config/sites.csv as a list of dicts — the built roster."""
    with (CONFIG / "sites.csv").open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="session")
def site_geojson() -> dict:
    return json.loads((CONFIG / "sites.geojson").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def site_source() -> dict:
    """config/sites_source.yaml — the human-authored input the artifacts derive from."""
    return yaml.safe_load((CONFIG / "sites_source.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def thresholds() -> dict:
    return yaml.safe_load((CONFIG / "thresholds.yaml").read_text(encoding="utf-8"))
